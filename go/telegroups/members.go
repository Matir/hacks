package main

import (
	"database/sql"
	"flag"
	"fmt"
	"log"
	"os"
	"strings"
	"text/tabwriter"
)

func runMembersCmd(args []string) {
	fs := flag.NewFlagSet("members", flag.ExitOnError)
	dbPath := fs.String("db", "telegroups.db", "path to SQLite database")
	fs.Usage = func() {
		fmt.Fprintf(os.Stderr, "usage: telegroups members [-db path] <group>\n\n")
		fmt.Fprintf(os.Stderr, "<group> is a group ID or a unique title substring.\n\n")
		fs.PrintDefaults()
	}
	fs.Parse(args)

	if fs.NArg() != 1 {
		fs.Usage()
		os.Exit(1)
	}

	db, err := openDB(*dbPath)
	if err != nil {
		log.Fatalf("openDB: %v", err)
	}
	defer db.Close()

	groupID, err := resolveGroupID(db, fs.Arg(0))
	if err != nil {
		log.Fatalf("%v", err)
	}

	if err := printMembers(db, groupID); err != nil {
		log.Fatalf("members: %v", err)
	}
}

func printMembers(db *sql.DB, groupID int64) error {
	rows, err := db.Query(`
		SELECT u.id, u.first_name, u.last_name, u.username, u.is_bot, m.status
		FROM users u
		JOIN members m ON m.user_id = u.id
		WHERE m.group_id = ?
		ORDER BY u.first_name COLLATE NOCASE, u.last_name COLLATE NOCASE
	`, groupID)
	if err != nil {
		return fmt.Errorf("query: %w", err)
	}
	defer rows.Close()

	w := tabwriter.NewWriter(os.Stdout, 0, 0, 2, ' ', 0)
	fmt.Fprintln(w, "ID\tNAME\tUSERNAME\tSTATUS")

	var count int
	for rows.Next() {
		var (
			id        int64
			firstName string
			lastName  string
			username  string
			isBot     int
			status    string
		)
		if err := rows.Scan(&id, &firstName, &lastName, &username, &isBot, &status); err != nil {
			return fmt.Errorf("scan: %w", err)
		}

		name := strings.TrimSpace(firstName + " " + lastName)
		if isBot != 0 {
			name += " (bot)"
		}
		handle := ""
		if username != "" {
			handle = "@" + username
		}

		fmt.Fprintf(w, "%d\t%s\t%s\t%s\n", id, name, handle, status)
		count++
	}
	w.Flush()

	if err := rows.Err(); err != nil {
		return err
	}

	fmt.Fprintf(os.Stderr, "%d members\n", count)
	return nil
}
