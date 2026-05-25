package main

import (
	"database/sql"
	"fmt"
	"log"
	"time"

	"github.com/zelenin/go-tdlib/client"
)

const membersPerPage = 200

// loadAllChats pages through the main chat list until TDLib signals that
// everything is loaded (404 error). Flood waits are handled transparently.
func loadAllChats(c *client.Client) {
	for {
		err := withFloodWait(func() error {
			_, e := c.LoadChats(&client.LoadChatsRequest{
				ChatList: &client.ChatListMain{},
				Limit:    100,
			})
			return e
		})
		if err != nil {
			break // 404 = all chats loaded
		}
	}
}

func enumerateGroups(c *client.Client, db *sql.DB, threshold time.Time) error {
	loadAllChats(c)

	chats, err := c.GetChats(&client.GetChatsRequest{
		ChatList: &client.ChatListMain{},
		Limit:    10000,
	})
	if err != nil {
		return fmt.Errorf("GetChats: %w", err)
	}

	for _, chatID := range chats.ChatIds {
		var chat *client.Chat
		if err := withFloodWait(func() (e error) {
			chat, e = c.GetChat(&client.GetChatRequest{ChatId: chatID})
			return
		}); err != nil {
			log.Printf("GetChat %d: %v", chatID, err)
			continue
		}

		switch t := chat.Type.(type) {
		case *client.ChatTypeBasicGroup:
			if err := listBasicGroup(c, db, chat, t.BasicGroupId, threshold); err != nil {
				log.Printf("basic group %q: %v", chat.Title, err)
			}
		case *client.ChatTypeSupergroup:
			if err := listSupergroup(c, db, chat, t.SupergroupId, threshold); err != nil {
				log.Printf("supergroup %q: %v", chat.Title, err)
			}
		}
	}
	return nil
}

func listBasicGroup(c *client.Client, db *sql.DB, chat *client.Chat, groupID int64, threshold time.Time) error {
	tx, err := db.Begin()
	if err != nil {
		return fmt.Errorf("begin tx: %w", err)
	}
	defer tx.Rollback()

	// member_count for basic groups comes from the full info fetch below;
	// use 0 as a placeholder so the row exists for needsMemberFetch to query.
	if err := upsertGroup(tx, chat.Id, chat.Title, "basic_group", 0); err != nil {
		return fmt.Errorf("upsertGroup: %w", err)
	}

	if !needsMemberFetch(tx, chat.Id, threshold) {
		fmt.Printf("\n[basic group] %s — skipping (fetched recently)\n", chat.Title)
		return tx.Commit()
	}

	var info *client.BasicGroupFullInfo
	if err := withFloodWait(func() (e error) {
		info, e = c.GetBasicGroupFullInfo(&client.GetBasicGroupFullInfoRequest{BasicGroupId: groupID})
		return
	}); err != nil {
		return fmt.Errorf("GetBasicGroupFullInfo: %w", err)
	}

	// Update member_count now that we have the real value.
	if err := upsertGroup(tx, chat.Id, chat.Title, "basic_group", int32(len(info.Members))); err != nil {
		return fmt.Errorf("upsertGroup (count): %w", err)
	}

	now := time.Now().Unix()
	fmt.Printf("\n[basic group] %s (%d members)\n", chat.Title, len(info.Members))
	for _, m := range info.Members {
		if err := persistMember(c, tx, chat.Id, m, now); err != nil {
			log.Printf("  member error: %v", err)
		}
	}

	if err := markGroupFetched(tx, chat.Id); err != nil {
		log.Printf("markGroupFetched %q: %v", chat.Title, err)
	}
	return tx.Commit()
}

func listSupergroup(c *client.Client, db *sql.DB, chat *client.Chat, sgID int64, threshold time.Time) error {
	groupType := "supergroup"
	if t, ok := chat.Type.(*client.ChatTypeSupergroup); ok && t.IsChannel {
		groupType = "channel"
	}

	// Fetch Telegram's reported member count before opening the transaction
	// so no API calls happen while the DB write lock is held.
	var memberCount int32
	var sg *client.Supergroup
	if err := withFloodWait(func() (e error) {
		sg, e = c.GetSupergroup(&client.GetSupergroupRequest{SupergroupId: sgID})
		return
	}); err == nil {
		memberCount = sg.MemberCount
	}

	tx, err := db.Begin()
	if err != nil {
		return fmt.Errorf("begin tx: %w", err)
	}
	defer tx.Rollback()

	if err := upsertGroup(tx, chat.Id, chat.Title, groupType, memberCount); err != nil {
		return fmt.Errorf("upsertGroup: %w", err)
	}

	if !needsMemberFetch(tx, chat.Id, threshold) {
		fmt.Printf("\n[%s] %s — skipping (fetched recently)\n", groupType, chat.Title)
		return tx.Commit()
	}

	var offset int32
	var total int
	now := time.Now().Unix()

	fmt.Printf("\n[%s] %s\n", groupType, chat.Title)
	for {
		var result *client.ChatMembers
		if err := withFloodWait(func() (e error) {
			result, e = c.GetSupergroupMembers(&client.GetSupergroupMembersRequest{
				SupergroupId: sgID,
				Offset:       offset,
				Limit:        membersPerPage,
			})
			return
		}); err != nil {
			return fmt.Errorf("GetSupergroupMembers offset=%d: %w", offset, err)
		}

		for _, m := range result.Members {
			if err := persistMember(c, tx, chat.Id, m, now); err != nil {
				log.Printf("  member error: %v", err)
			}
		}
		total += len(result.Members)

		if len(result.Members) < membersPerPage {
			break
		}
		offset += int32(len(result.Members))
	}

	if memberCount > 0 && total == 0 {
		log.Printf("[%s] %s: Telegram reports %d members but enumeration returned 0 — likely restricted",
			groupType, chat.Title, memberCount)
	}
	fmt.Printf("  (%d members total)\n", total)

	if err := markGroupFetched(tx, chat.Id); err != nil {
		log.Printf("markGroupFetched %q: %v", chat.Title, err)
	}
	return tx.Commit()
}

func persistMember(c *client.Client, tx *sql.Tx, chatID int64, m *client.ChatMember, lastSeenAt int64) error {
	sender, ok := m.MemberId.(*client.MessageSenderUser)
	if !ok {
		if cs, ok := m.MemberId.(*client.MessageSenderChat); ok {
			fmt.Printf("  [anonymous chat id:%d]\n", cs.ChatId)
		}
		return nil
	}

	var user *client.User
	if err := withFloodWait(func() (e error) {
		user, e = c.GetUser(&client.GetUserRequest{UserId: sender.UserId})
		return
	}); err != nil {
		fmt.Printf("  [user %d] (error: %v)\n", sender.UserId, err)
		return nil
	}

	handle := primaryUsername(user.Usernames)
	isBot := isUserBot(user)
	status := memberStatus(m.Status)

	if handle != "" {
		fmt.Printf("  %s %s @%s (id:%d, status:%s)\n", user.FirstName, user.LastName, handle, user.Id, status)
	} else {
		fmt.Printf("  %s %s (id:%d, status:%s)\n", user.FirstName, user.LastName, user.Id, status)
	}

	if err := upsertUser(tx, user.Id, user.FirstName, user.LastName, handle, isBot); err != nil {
		return fmt.Errorf("upsertUser %d: %w", user.Id, err)
	}
	if err := upsertMember(tx, chatID, user.Id, lastSeenAt, status, m.JoinedChatDate); err != nil {
		return fmt.Errorf("upsertMember: %w", err)
	}
	return nil
}

func memberStatus(s client.ChatMemberStatus) string {
	switch s.(type) {
	case *client.ChatMemberStatusCreator:
		return "owner"
	case *client.ChatMemberStatusAdministrator:
		return "admin"
	case *client.ChatMemberStatusMember:
		return "member"
	case *client.ChatMemberStatusRestricted:
		return "restricted"
	case *client.ChatMemberStatusLeft:
		return "left"
	case *client.ChatMemberStatusBanned:
		return "banned"
	default:
		return "unknown"
	}
}

func isUserBot(u *client.User) bool {
	_, ok := u.Type.(*client.UserTypeBot)
	return ok
}

func primaryUsername(u *client.Usernames) string {
	if u == nil || len(u.ActiveUsernames) == 0 {
		return ""
	}
	return u.ActiveUsernames[0]
}
