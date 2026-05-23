package main

import (
	"fmt"
	"log"

	"github.com/zelenin/go-tdlib/client"
)

const membersPerPage = 200

func enumerateGroups(c *client.Client) error {
	chats, err := c.GetChats(&client.GetChatsRequest{
		ChatList: &client.ChatListMain{},
		Limit:    1000,
	})
	if err != nil {
		return fmt.Errorf("GetChats: %w", err)
	}

	for _, chatID := range chats.ChatIds {
		chat, err := c.GetChat(&client.GetChatRequest{ChatId: chatID})
		if err != nil {
			log.Printf("GetChat %d: %v", chatID, err)
			continue
		}

		switch t := chat.Type.(type) {
		case *client.ChatTypeBasicGroup:
			if err := listBasicGroup(c, chat, t.BasicGroupId); err != nil {
				log.Printf("basic group %q: %v", chat.Title, err)
			}
		case *client.ChatTypeSupergroup:
			if err := listSupergroup(c, chat, t.SupergroupId); err != nil {
				log.Printf("supergroup %q: %v", chat.Title, err)
			}
		}
	}
	return nil
}

func listBasicGroup(c *client.Client, chat *client.Chat, groupID int64) error {
	info, err := c.GetBasicGroupFullInfo(&client.GetBasicGroupFullInfoRequest{
		BasicGroupId: groupID,
	})
	if err != nil {
		return fmt.Errorf("GetBasicGroupFullInfo: %w", err)
	}

	fmt.Printf("\n[basic group] %s (%d members)\n", chat.Title, len(info.Members))
	for _, m := range info.Members {
		printMember(c, m)
	}
	return nil
}

func listSupergroup(c *client.Client, chat *client.Chat, sgID int64) error {
	var offset int32
	var total int

	fmt.Printf("\n[supergroup] %s\n", chat.Title)
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
			printMember(c, m)
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

func printMember(c *client.Client, m *client.ChatMember) {
	switch sender := m.MemberId.(type) {
	case *client.MessageSenderUser:
		user, err := c.GetUser(&client.GetUserRequest{UserId: sender.UserId})
		if err != nil {
			fmt.Printf("  [user %d] (error: %v)\n", sender.UserId, err)
			return
		}
		handle := primaryUsername(user.Usernames)
		if handle != "" {
			fmt.Printf("  %s %s @%s (id:%d)\n", user.FirstName, user.LastName, handle, user.Id)
		} else {
			fmt.Printf("  %s %s (id:%d)\n", user.FirstName, user.LastName, user.Id)
		}
	case *client.MessageSenderChat:
		fmt.Printf("  [anonymous chat id:%d]\n", sender.ChatId)
	}
}

func primaryUsername(u *client.Usernames) string {
	if u == nil || len(u.ActiveUsernames) == 0 {
		return ""
	}
	return u.ActiveUsernames[0]
}
