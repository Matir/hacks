package main

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"os"
	"text/tabwriter"
	"time"

	"github.com/zelenin/go-tdlib/client"
)

const membersPerPage = 200

// loadAllChats pages through the main chat list until TDLib signals that
// everything is loaded (404 error). Flood waits are handled transparently.
// Retries up to 3 times on other non-fatal errors.
func loadAllChats(ctx context.Context, c *client.Client) {
	retries := 0
	const maxRetries = 3
	for {
		err := withFloodWait(func() error {
			_, e := c.LoadChats(ctx, &client.LoadChatsRequest{
				ChatList: &client.ChatListMain{},
				Limit:    100,
			})
			return e
		})
		if err != nil {
			var tdResErr client.ResponseError
			if errors.As(err, &tdResErr) && tdResErr.Err.Code == 404 {
				break // normal termination: all chats loaded
			}

			if retries < maxRetries {
				retries++
				backoff := time.Duration(retries*2) * time.Second
				logError("LoadChats error (code %d): %v; retrying in %v (%d/%d)",
					getErrCode(err), err, backoff, retries, maxRetries)
				time.Sleep(backoff)
				continue
			}

			logError("LoadChats failed after %d retries: %v", maxRetries, err)
			break
		}
		retries = 0 // reset retries on success
	}
}

func getErrCode(err error) int32 {
	var tdResErr client.ResponseError
	if errors.As(err, &tdResErr) {
		return tdResErr.Err.Code
	}
	return 0
}

// loadGroupChats loads the full chat list from TDLib and returns only the
// entries that are basic groups, supergroups, or channels.
func loadGroupChats(ctx context.Context, c *client.Client) ([]*client.Chat, error) {
	loadAllChats(ctx, c)

	chats, err := c.GetChats(ctx, &client.GetChatsRequest{
		ChatList: &client.ChatListMain{},
		Limit:    10000,
	})
	if err != nil {
		return nil, fmt.Errorf("GetChats: %w", err)
	}

	var groups []*client.Chat
	for _, chatID := range chats.ChatIds {
		var chat *client.Chat
		if err := withFloodWait(func() (e error) {
			chat, e = c.GetChat(ctx, &client.GetChatRequest{ChatId: chatID})
			return
		}); err != nil {
			logError("GetChat %d: %v", chatID, err)
			continue
		}
		switch chat.Type.(type) {
		case *client.ChatTypeBasicGroup, *client.ChatTypeSupergroup:
			groups = append(groups, chat)
		}
	}
	return groups, nil
}

// enumerateGroupChats fetches and stores members for each chat in the list.
func enumerateGroupChats(ctx context.Context, c *client.Client, db *sql.DB, chats []*client.Chat, threshold time.Time) {
	for _, chat := range chats {
		switch t := chat.Type.(type) {
		case *client.ChatTypeBasicGroup:
			if err := listBasicGroup(ctx, c, db, chat, t.BasicGroupId, threshold); err != nil {
				logError("basic group %q: %v", chat.Title, err)
			}
		case *client.ChatTypeSupergroup:
			if err := listSupergroup(ctx, c, db, chat, t.SupergroupId, threshold); err != nil {
				logError("supergroup %q: %v", chat.Title, err)
			}
		}
	}
}

func listBasicGroup(ctx context.Context, c *client.Client, db *sql.DB, chat *client.Chat, groupID int64, threshold time.Time) error {
	if !needsMemberFetch(db, chat.Id, threshold) {
		logInfo("[basic group] %s — skipping (fetched recently)", chat.Title)
		return nil
	}

	logDebug("[basic group] %s: fetching full info (id: %d)", chat.Title, chat.Id)
	var info *client.BasicGroupFullInfo
	if err := withFloodWait(func() (e error) {
		info, e = c.GetBasicGroupFullInfo(ctx, &client.GetBasicGroupFullInfoRequest{BasicGroupId: groupID})
		return
	}); err != nil {
		return fmt.Errorf("GetBasicGroupFullInfo: %w", err)
	}

	type memberData struct {
		user   *client.User
		member *client.ChatMember
	}
	var membersData []memberData
	for _, m := range info.Members {
		sender, ok := m.MemberId.(*client.MessageSenderUser)
		if !ok {
			continue
		}
		var user *client.User
		if err := withFloodWait(func() (e error) {
			user, e = c.GetUser(ctx, &client.GetUserRequest{UserId: sender.UserId})
			return
		}); err != nil {
			logError("  GetUser %d: %v", sender.UserId, err)
			continue
		}
		membersData = append(membersData, memberData{user: user, member: m})
	}

	logDebug("[basic group] %s: writing %d members to database", chat.Title, len(membersData))
	tx, err := db.Begin()
	if err != nil {
		return fmt.Errorf("begin tx: %w", err)
	}
	defer tx.Rollback()

	if err := upsertGroup(tx, chat.Id, chat.Title, "basic_group", int32(len(info.Members))); err != nil {
		return fmt.Errorf("upsertGroup: %w", err)
	}

	now := time.Now().Unix()
	logInfo("[basic group] %s (%d members)", chat.Title, len(info.Members))
	for _, md := range membersData {
		if err := writeMember(tx, chat.Id, md.user, md.member, now); err != nil {
			logError("  member error: %v", err)
		}
	}

	// Log anonymous chats
	for _, m := range info.Members {
		if _, ok := m.MemberId.(*client.MessageSenderUser); !ok {
			if cs, ok := m.MemberId.(*client.MessageSenderChat); ok {
				logDebug("  anonymous chat id:%d", cs.ChatId)
			}
		}
	}

	if err := markGroupFetched(tx, chat.Id); err != nil {
		logError("markGroupFetched %q: %v", chat.Title, err)
	}
	return tx.Commit()
}

func listSupergroup(ctx context.Context, c *client.Client, db *sql.DB, chat *client.Chat, sgID int64, threshold time.Time) error {
	groupType := "supergroup"
	if t, ok := chat.Type.(*client.ChatTypeSupergroup); ok && t.IsChannel {
		groupType = "channel"
	}

	if !needsMemberFetch(db, chat.Id, threshold) {
		logInfo("[%s] %s — skipping (fetched recently)", groupType, chat.Title)
		return nil
	}

	logDebug("[%s] %s: starting member enumeration (id: %d)", groupType, chat.Title, chat.Id)

	var memberCount int32
	var sg *client.Supergroup
	if err := withFloodWait(func() (e error) {
		sg, e = c.GetSupergroup(ctx, &client.GetSupergroupRequest{SupergroupId: sgID})
		return
	}); err == nil {
		memberCount = sg.MemberCount
	}

	if err := upsertGroup(db, chat.Id, chat.Title, groupType, memberCount); err != nil {
		return fmt.Errorf("upsertGroup: %w", err)
	}

	var offset int32
	var total int
	now := time.Now().Unix()

	logInfo("[%s] %s", groupType, chat.Title)
	for {
		var result *client.ChatMembers
		if err := withFloodWait(func() (e error) {
			result, e = c.GetSupergroupMembers(ctx, &client.GetSupergroupMembersRequest{
				SupergroupId: sgID,
				Offset:       offset,
				Limit:        membersPerPage,
			})
			return
		}); err != nil {
			return fmt.Errorf("GetSupergroupMembers offset=%d: %w", offset, err)
		}

		if len(result.Members) == 0 {
			break
		}

		type memberData struct {
			user   *client.User
			member *client.ChatMember
		}
		var pageData []memberData
		for _, m := range result.Members {
			sender, ok := m.MemberId.(*client.MessageSenderUser)
			if !ok {
				continue
			}
			var user *client.User
			if err := withFloodWait(func() (e error) {
				user, e = c.GetUser(ctx, &client.GetUserRequest{UserId: sender.UserId})
				return
			}); err != nil {
				logError("  GetUser %d: %v", sender.UserId, err)
				continue
			}
			pageData = append(pageData, memberData{user: user, member: m})
		}

		logDebug("[%s] %s: writing page of %d members to database (offset %d)", groupType, chat.Title, len(pageData), offset)
		tx, err := db.Begin()
		if err != nil {
			return fmt.Errorf("begin tx: %w", err)
		}

		err = func() error {
			defer tx.Rollback()
			for _, md := range pageData {
				if err := writeMember(tx, chat.Id, md.user, md.member, now); err != nil {
					return err
				}
			}
			// Log anonymous chats
			for _, m := range result.Members {
				if _, ok := m.MemberId.(*client.MessageSenderUser); !ok {
					if cs, ok := m.MemberId.(*client.MessageSenderChat); ok {
						logDebug("  anonymous chat id:%d", cs.ChatId)
					}
				}
			}
			return tx.Commit()
		}()

		if err != nil {
			return fmt.Errorf("write page transaction: %w", err)
		}

		total += len(result.Members)
		if memberCount > 0 {
			logInfo("[%s] %s: processed %d/%d members", groupType, chat.Title, total, memberCount)
		} else {
			logInfo("[%s] %s: processed %d members", groupType, chat.Title, total)
		}

		if len(result.Members) < membersPerPage {
			break
		}
		offset += int32(len(result.Members))
	}

	if memberCount > 0 && total == 0 {
		logError("[%s] %s: Telegram reports %d members but enumeration returned 0 — likely restricted",
			groupType, chat.Title, memberCount)
	}
	logInfo("[%s] %s: %d members", groupType, chat.Title, total)

	if err := markGroupFetched(db, chat.Id); err != nil {
		logError("markGroupFetched %q: %v", chat.Title, err)
	}
	return nil
}

func writeMember(ex execer, chatID int64, user *client.User, m *client.ChatMember, lastSeenAt int64) error {
	handle := primaryUsername(user.Usernames)
	isBot := isUserBot(user)
	status := memberStatus(m.Status)

	if handle != "" {
		logDebug("  %s %s @%s (id:%d, status:%s)", user.FirstName, user.LastName, handle, user.Id, status)
	} else {
		logDebug("  %s %s (id:%d, status:%s)", user.FirstName, user.LastName, user.Id, status)
	}

	if err := upsertUser(ex, user.Id, user.FirstName, user.LastName, handle, isBot); err != nil {
		return fmt.Errorf("upsertUser %d: %w", user.Id, err)
	}
	if err := upsertMember(ex, chatID, user.Id, lastSeenAt, status, m.JoinedChatDate); err != nil {
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

func getChatMemberCount(ctx context.Context, c *client.Client, chat *client.Chat) (int32, error) {
	switch t := chat.Type.(type) {
	case *client.ChatTypeBasicGroup:
		var bg *client.BasicGroup
		err := withFloodWait(func() (e error) {
			bg, e = c.GetBasicGroup(ctx, &client.GetBasicGroupRequest{BasicGroupId: t.BasicGroupId})
			return
		})
		if err != nil {
			return 0, fmt.Errorf("GetBasicGroup: %w", err)
		}
		return bg.MemberCount, nil

	case *client.ChatTypeSupergroup:
		var sg *client.Supergroup
		err := withFloodWait(func() (e error) {
			sg, e = c.GetSupergroup(ctx, &client.GetSupergroupRequest{SupergroupId: t.SupergroupId})
			return
		})
		if err != nil {
			return 0, fmt.Errorf("GetSupergroup: %w", err)
		}
		return sg.MemberCount, nil
	}
	return 0, fmt.Errorf("unsupported chat type")
}

func runDryRun(ctx context.Context, c *client.Client, chats []*client.Chat) {
	logInfo("The following groups would be fetched:")
	w := tabwriter.NewWriter(os.Stdout, 0, 0, 2, ' ', 0)
	fmt.Fprintln(w, "ID\tTYPE\tMEMBERS\tTITLE")
	for _, chat := range chats {
		count, err := getChatMemberCount(ctx, c, chat)
		if err != nil {
			logError("failed to get member count for %q: %v", chat.Title, err)
			count = 0
		}
		groupType := "basic group"
		if t, ok := chat.Type.(*client.ChatTypeSupergroup); ok {
			if t.IsChannel {
				groupType = "channel"
			} else {
				groupType = "supergroup"
			}
		}
		fmt.Fprintf(w, "%d\t%s\t%d\t%s\n", chat.Id, groupType, count, chat.Title)
	}
	w.Flush()
}
