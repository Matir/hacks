package main

import (
	"fmt"

	"github.com/AlecAivazis/survey/v2"
	"github.com/zelenin/go-tdlib/client"
)

// selectGroupsInteractively presents a multi-select TUI listing all supplied
// group chats and returns only the ones the user picks.
func selectGroupsInteractively(chats []*client.Chat) ([]*client.Chat, error) {
	labels := make([]string, len(chats))
	for i, chat := range chats {
		labels[i] = chatLabel(chat)
	}

	// Deduplicate: if two chats produce the same label, append the chat ID.
	seen := make(map[string]bool, len(labels))
	for i, label := range labels {
		if seen[label] {
			labels[i] = fmt.Sprintf("%s  (id:%d)", label, chats[i].Id)
		}
		seen[labels[i]] = true
	}

	labelToChat := make(map[string]*client.Chat, len(chats))
	for i, chat := range chats {
		labelToChat[labels[i]] = chat
	}

	var chosen []string
	if err := survey.AskOne(
		&survey.MultiSelect{
			Message: "Select groups to fetch  (↑↓ navigate · space select · enter confirm):",
			Options: labels,
		},
		&chosen,
		survey.WithPageSize(20),
	); err != nil {
		return nil, err
	}

	result := make([]*client.Chat, 0, len(chosen))
	for _, label := range chosen {
		result = append(result, labelToChat[label])
	}
	return result, nil
}

func chatLabel(chat *client.Chat) string {
	switch t := chat.Type.(type) {
	case *client.ChatTypeBasicGroup:
		_ = t
		return fmt.Sprintf("%s  [basic group]", chat.Title)
	case *client.ChatTypeSupergroup:
		if t.IsChannel {
			return fmt.Sprintf("%s  [channel]", chat.Title)
		}
		return fmt.Sprintf("%s  [supergroup]", chat.Title)
	default:
		return chat.Title
	}
}
