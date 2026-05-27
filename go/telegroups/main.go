package main

import (
	"context"
	"flag"
	"fmt"
	"io"
	"log"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/zelenin/go-tdlib/client"
)

func main() {
	ctx := context.Background()

	if len(os.Args) > 1 {
		switch os.Args[1] {
		case "list":
			runListCmd(os.Args[2:])
			return
		case "intersect":
			runIntersectCmd(os.Args[2:])
			return
		}
	}

	dbPath := flag.String("db", "telegroups.db", "path to SQLite database")
	since := flag.Duration("since", 0, "skip groups whose member list was fetched within this duration (e.g. 24h)")
	selectGroups := flag.Bool("select-groups", false, "interactively choose which groups to fetch")
	quiet := flag.Bool("quiet", false, "suppress info messages; errors still shown")
	silent := flag.Bool("silent", false, "suppress all output except fatal errors")
	verbose := flag.Bool("verbose", false, "enable verbose debug logging")
	useQR := flag.Bool("qr", false, "use QR code for authentication")
	dryRun := flag.Bool("dry-run", false, "dry run; list groups that would be fetched and member counts, then exit")
	yes := flag.Bool("y", false, "bypass confirmation prompt")
	logFilePath := flag.String("log-file", "", "path to write application logs (TDLib logs will be written to <path>.tdlib)")
	matchFlag := flag.String("match", "", "comma-separated list of glob patterns or IDs to match group names")
	flag.Parse()

	isQuiet = *quiet || *silent
	isSilent = *silent
	isVerbose = *verbose

	if *logFilePath != "" {
		f, err := os.OpenFile(*logFilePath, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0644)
		if err != nil {
			log.Fatalf("failed to open log file: %v", err)
		}
		defer f.Close()
		log.SetOutput(io.MultiWriter(os.Stderr, f))
	}

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

	// Configure TDLib logging globally BEFORE creating the client to prevent console spew during auth
	if *logFilePath != "" {
		_, err = client.SetLogVerbosityLevel(&client.SetLogVerbosityLevelRequest{
			NewVerbosityLevel: 1,
		})
		if err != nil {
			logError("SetLogVerbosityLevel error: %v", err)
		}

		tdlibLogPath := *logFilePath + ".tdlib"
		_, err = client.SetLogStream(&client.SetLogStreamRequest{
			LogStream: &client.LogStreamFile{
				Path:           tdlibLogPath,
				MaxFileSize:    10 * 1024 * 1024, // 10MB
				RedirectStderr: false,
			},
		})
		if err != nil {
			logError("SetLogStream (file) error: %v", err)
		}
	} else if isVerbose {
		_, err = client.SetLogVerbosityLevel(&client.SetLogVerbosityLevelRequest{
			NewVerbosityLevel: 1,
		})
		if err != nil {
			logError("SetLogVerbosityLevel error: %v", err)
		}
	} else {
		_, err = client.SetLogStream(&client.SetLogStreamRequest{
			LogStream: &client.LogStreamEmpty{},
		})
		if err != nil {
			logError("SetLogStream (empty) error: %v", err)
		}
	}

	authorizer := NewCustomAuthorizer(params, *useQR)

	tdlibClient, err := client.NewClient(authorizer)
	if err != nil {
		log.Fatalf("NewClient error: %v", err)
	}
	defer tdlibClient.Close(ctx)

	me, err := tdlibClient.GetMe(ctx)
	if err != nil {
		log.Fatalf("GetMe error: %v", err)
	}
	logInfo("authorized as: %s %s (id:%d)", me.FirstName, me.LastName, me.Id)

	chats, err := loadGroupChats(ctx, tdlibClient)
	if err != nil {
		log.Fatalf("loadGroupChats: %v", err)
	}

	var filters []string
	if *matchFlag != "" {
		for _, f := range strings.Split(*matchFlag, ",") {
			f = strings.TrimSpace(f)
			if f != "" {
				filters = append(filters, f)
			}
		}
	}
	if args := flag.Args(); len(args) > 0 {
		filters = append(filters, args...)
	}

	if len(filters) > 0 {
		chats = filterChats(chats, filters)
		if len(chats) == 0 {
			log.Fatalf("no groups matched filters: %v", filters)
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

	if *dryRun {
		runDryRun(ctx, tdlibClient, chats)
		return
	}

	if !*yes {
		runDryRun(ctx, tdlibClient, chats)
		fmt.Print("\nBegin fetching members for these groups? [y/N]: ")
		var response string
		if _, err := fmt.Scanln(&response); err != nil && response != "" {
			log.Fatalf("failed to read confirmation: %v", err)
		}
		response = strings.ToLower(strings.TrimSpace(response))
		if response != "y" && response != "yes" {
			logInfo("Aborted by user.")
			return
		}
	}

	enumerateGroupChats(ctx, tdlibClient, db, chats, threshold)
}
