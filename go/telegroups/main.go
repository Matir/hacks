package main

import (
	"flag"
	"log"
	"os"
	"path/filepath"
	"strconv"
	"time"

	"github.com/zelenin/go-tdlib/client"
)

func main() {
	dbPath := flag.String("db", "telegroups.db", "path to SQLite database")
	since := flag.Duration("since", 0, "skip groups whose member list was fetched within this duration (e.g. 24h)")
	selectGroups := flag.Bool("select-groups", false, "interactively choose which groups to fetch")
	quiet := flag.Bool("quiet", false, "suppress info messages; errors still shown")
	silent := flag.Bool("silent", false, "suppress all output except fatal errors")
	flag.Parse()

	isQuiet = *quiet || *silent
	isSilent = *silent

	apiIDStr := os.Getenv("TELEGRAM_API_ID")
	apiHash := os.Getenv("TELEGRAM_API_HASH")

	if apiIDStr == "" || apiHash == "" {
		log.Fatal("TELEGRAM_API_ID and TELEGRAM_API_HASH must be set")
	}

	apiID, err := strconv.ParseInt(apiIDStr, 10, 32)
	if err != nil {
		log.Fatalf("invalid TELEGRAM_API_ID: %v", err)
	}

	db, err := openDB(*dbPath)
	if err != nil {
		log.Fatalf("openDB: %v", err)
	}
	defer db.Close()

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
	logInfo("authorized as: %s %s (id:%d)", me.FirstName, me.LastName, me.Id)

	chats, err := loadGroupChats(tdlibClient)
	if err != nil {
		log.Fatalf("loadGroupChats: %v", err)
	}

	if args := flag.Args(); len(args) > 0 {
		chats = filterChats(chats, args)
		if len(chats) == 0 {
			log.Fatalf("no groups matched: %v", args)
		}
	}

	if *selectGroups {
		chats, err = selectGroupsInteractively(chats)
		if err != nil {
			log.Fatalf("selectGroups: %v", err)
		}
		if len(chats) == 0 {
			logInfo("no groups selected, exiting")
			return
		}
	}

	var threshold time.Time
	if *since > 0 {
		threshold = time.Now().Add(-*since)
	}

	enumerateGroupChats(tdlibClient, db, chats, threshold)
}
