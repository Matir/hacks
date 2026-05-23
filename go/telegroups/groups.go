package main

import (
	"database/sql"
	"fmt"
	"log"

	"github.com/zelenin/go-tdlib/client"
)

const membersPerPage = 200

func enumerateGroups(c *client.Client, db *sql.DB) error {
	chats, err := c.GetChats(&client.GetChatsRequest{
		ChatList: &client.ChatListMain{},
		Limit:    1000,
	})
	if err != nil {
		return fmt.Errorf("GetChats: %w", err)
	}

	tx, err := db.Begin()
	if err != nil {
		return fmt.Errorf("begin tx: %w", err)
	}
	defer tx.Rollback()

	for _, chatID := range chats.ChatIds {
		chat, err := c.GetChat(&client.GetChatRequest{ChatId: chatID})
		if err != nil {
			log.Printf("GetChat %d: %v", chatID, err)
			continue
		}

		switch t := chat.Type.(type) {
		case *client.ChatTypeBasicGroup:
			if err := listBasicGroup(c, tx, chat, t.BasicGroupId); err != nil {
				log.Printf("basic group %q: %v", chat.Title, err)
			}
		case *client.ChatTypeSupergroup:
			if err := listSupergroup(c, tx, chat, t.SupergroupId); err != nil {
				log.Printf("supergroup %q: %v", chat.Title, err)
			}
		}
	}

	return tx.Commit()
}

func listBasicGroup(c *client.Client, tx *sql.Tx, chat *client.Chat, groupID int64) error {
	info, err := c.GetBasicGroupFullInfo(&client.GetBasicGroupFullInfoRequest{
		BasicGroupId: groupID,
	})
	if err != nil {
		return fmt.Errorf("GetBasicGroupFullInfo: %w", err)
	}

	if err := upsertGroup(tx, chat.Id, chat.Title, "basic_group"); err != nil {
		return fmt.Errorf("upsertGroup: %w", err)
	}

	fmt.Printf("\n[basic group] %s (%d members)\n", chat.Title, len(info.Members))
	for _, m := range info.Members {
		if err := persistMember(c, tx, chat.Id, m); err != nil {
			log.Printf("  member error: %v", err)
		}
	}
	return nil
}

func listSupergroup(c *client.Client, tx *sql.Tx, chat *client.Chat, sgID int64) error {
	groupType := "supergroup"
	if t, ok := chat.Type.(*client.ChatTypeSupergroup); ok && t.IsChannel {
		groupType = "channel"
	}
	if err := upsertGroup(tx, chat.Id, chat.Title, groupType); err != nil {
		return fmt.Errorf("upsertGroup: %w", err)
	}

	var offset int32
	var total int

	fmt.Printf("\n[%s] %s\n", groupType, chat.Title)
	for {
		result, err := c.GetSupergroupMembers(&client.GetSupergroupMembersRequest{
			SupergroupId: sgID,
			Offset:       offset,
			Limit:        membersPerPage,
		})
		if err != nil {
			return fmt.Errorf("GetSupergroupMembers offset=%d: %w", offset, err)
		}

		for _, m := range result.Members {
			if err := persistMember(c, tx, chat.Id, m); err != nil {
				log.Printf("  member error: %v", err)
			}
		}
		total += len(result.Members)

		if len(result.Members) < membersPerPage {
			break
		}
		offset += int32(len(result.Members))
	}
	fmt.Printf("  (%d members total)\n", total)
	return nil
}

func persistMember(c *client.Client, tx *sql.Tx, chatID int64, m *client.ChatMember) error {
	sender, ok := m.MemberId.(*client.MessageSenderUser)
	if !ok {
		// anonymous chat-sender: no user row to store
		if cs, ok := m.MemberId.(*client.MessageSenderChat); ok {
			fmt.Printf("  [anonymous chat id:%d]\n", cs.ChatId)
		}
		return nil
	}

	user, err := c.GetUser(&client.GetUserRequest{UserId: sender.UserId})
	if err != nil {
		fmt.Printf("  [user %d] (error: %v)\n", sender.UserId, err)
		return nil
	}

	handle := primaryUsername(user.Usernames)
	if handle != "" {
		fmt.Printf("  %s %s @%s (id:%d)\n", user.FirstName, user.LastName, handle, user.Id)
	} else {
		fmt.Printf("  %s %s (id:%d)\n", user.FirstName, user.LastName, user.Id)
	}

	if err := upsertUser(tx, user.Id, user.FirstName, user.LastName, handle); err != nil {
		return fmt.Errorf("upsertUser %d: %w", user.Id, err)
	}
	if err := upsertMember(tx, chatID, user.Id); err != nil {
		return fmt.Errorf("upsertMember: %w", err)
	}
	return nil
}

func primaryUsername(u *client.Usernames) string {
	if u == nil || len(u.ActiveUsernames) == 0 {
		return ""
	}
	return u.ActiveUsernames[0]
}
