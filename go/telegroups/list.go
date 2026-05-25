package main

import (
	"database/sql"
	"flag"
	"fmt"
	"log"
	"os"
	"text/tabwriter"
	"time"
)

func runListCmd(args []string) {
	fs := flag.NewFlagSet("list", flag.ExitOnError)
	dbPath := fs.String("db", "telegroups.db", "path to SQLite database")
	fs.Usage = func() {
		fmt.Fprintf(os.Stderr, "usage: telegroups list [-db path]\n\n")
		fmt.Fprintf(os.Stderr, "Lists groups stored in the database. IDs can be passed as positional\n")
		fmt.Fprintf(os.Stderr, "arguments to the main command to target specific groups.\n\n")
		fs.PrintDefaults()
	}
	fs.Parse(args)

	db, err := openDB(*dbPath)
	if err != nil {
		log.Fatalf("openDB: %v", err)
	}
	defer db.Close()

	if err := listGroups(db); err != nil {
		log.Fatalf("list: %v", err)
	}
}

func listGroups(db *sql.DB) error {
	rows, err := db.Query(`
		SELECT
			g.id,
			g.type,
			g.member_count,
			COUNT(m.user_id)      AS db_count,
			g.members_fetched_at,
			g.title
		FROM groups g
		LEFT JOIN members m ON m.group_id = g.id
		GROUP BY g.id
		ORDER BY g.title COLLATE NOCASE
	`)
	if err != nil {
		return fmt.Errorf("query: %w", err)
	}
	defer rows.Close()

	w := tabwriter.NewWriter(os.Stdout, 0, 0, 2, ' ', 0)
	fmt.Fprintln(w, "ID\tTYPE\tTG\tDB\tFETCHED\tTITLE")

	for rows.Next() {
		var (
			id          int64
			groupType   string
			memberCount int32
			dbCount     int32
			fetchedAt   sql.NullInt64
			title       string
		)
		if err := rows.Scan(&id, &groupType, &memberCount, &dbCount, &fetchedAt, &title); err != nil {
			return fmt.Errorf("scan: %w", err)
		}

		fetched := "never"
		if fetchedAt.Valid {
			fetched = time.Unix(fetchedAt.Int64, 0).Format("2006-01-02 15:04")
		}

		fmt.Fprintf(w, "%d\t%s\t%d\t%d\t%s\t%s\n",
			id, groupType, memberCount, dbCount, fetched, title)
	}
	w.Flush()
	return rows.Err()
}
