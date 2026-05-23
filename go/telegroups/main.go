package main

import (
	"log"
	"os"
	"path/filepath"
	"strconv"

	"github.com/zelenin/go-tdlib/client"
)

func main() {
	apiIDStr := os.Getenv("TELEGRAM_API_ID")
	apiHash := os.Getenv("TELEGRAM_API_HASH")

	if apiIDStr == "" || apiHash == "" {
		log.Fatal("TELEGRAM_API_ID and TELEGRAM_API_HASH must be set")
	}

	apiID, err := strconv.ParseInt(apiIDStr, 10, 32)
	if err != nil {
		log.Fatalf("invalid TELEGRAM_API_ID: %v", err)
	}

	params := &client.SetTdlibParametersRequest{
		UseTestDc:           false,
		DatabaseDirectory:   filepath.Join(".tdlib", "database"),
		FilesDirectory:      filepath.Join(".tdlib", "files"),
		UseFileDatabase:     true,
		UseChatInfoDatabase: true,
		UseMessageDatabase:  true,
		UseSecretChats:      false,
		ApiId:               int32(apiID),
		ApiHash:             apiHash,
		SystemLanguageCode:  "en",
		DeviceModel:         "Server",
		SystemVersion:       "1.0.0",
		ApplicationVersion:  "1.0.0",
	}

	authorizer := client.ClientAuthorizer(params)
	go client.CliInteractor(authorizer)

	tdlibClient, err := client.NewClient(authorizer, client.WithLogVerbosity(&client.SetLogVerbosityLevelRequest{
		NewVerbosityLevel: 1,
	}))
	if err != nil {
		log.Fatalf("NewClient error: %v", err)
	}
	defer tdlibClient.Stop()

	me, err := tdlibClient.GetMe()
	if err != nil {
		log.Fatalf("GetMe error: %v", err)
	}
	log.Printf("authorized as: %s %s [@%s]", me.FirstName, me.LastName, me.Username)
}
