package main

import (
	"database/sql"
	"flag"
	"fmt"
	"log"
	"os"
	"strconv"
	"strings"
	"text/tabwriter"
)

func runIntersectCmd(args []string) {
	fs := flag.NewFlagSet("intersect", flag.ExitOnError)
	dbPath := fs.String("db", "telegroups.db", "path to SQLite database")
	fs.Usage = func() {
		fmt.Fprintf(os.Stderr, "usage: telegroups intersect [-db path] <group> <group> [...]\n\n")
		fmt.Fprintf(os.Stderr, "Each <group> is a group ID or a unique title substring.\n")
		fmt.Fprintf(os.Stderr, "Prints users who are members of all specified groups.\n\n")
		fs.PrintDefaults()
	}
	fs.Parse(args)

	if fs.NArg() < 2 {
		fs.Usage()
		os.Exit(1)
	}

	db, err := openDB(*dbPath)
	if err != nil {
		log.Fatalf("openDB: %v", err)
	}
	defer db.Close()

	groupIDs, err := resolveGroupIDs(db, fs.Args())
	if err != nil {
		log.Fatalf("%v", err)
	}

	if err := printIntersection(db, groupIDs); err != nil {
		log.Fatalf("intersect: %v", err)
	}
}

// resolveGroupIDs maps each filter string to exactly one group ID.
func resolveGroupIDs(db *sql.DB, filters []string) ([]int64, error) {
	ids := make([]int64, 0, len(filters))
	for _, f := range filters {
		id, err := resolveGroupID(db, f)
		if err != nil {
			return nil, err
		}
		ids = append(ids, id)
	}
	return ids, nil
}

func resolveGroupID(db *sql.DB, filter string) (int64, error) {
	if id, err := strconv.ParseInt(filter, 10, 64); err == nil {
		var dummy int
		if err := db.QueryRow(`SELECT 1 FROM groups WHERE id = ?`, id).Scan(&dummy); err != nil {
			return 0, fmt.Errorf("group %d not found in database", id)
		}
		return id, nil
	}

	rows, err := db.Query(
		`SELECT id, title FROM groups WHERE title LIKE ? COLLATE NOCASE`,
		"%"+filter+"%",
	)
	if err != nil {
		return 0, err
	}
	defer rows.Close()

	type match struct {
		id    int64
		title string
	}
	var matches []match
	for rows.Next() {
		var m match
		if err := rows.Scan(&m.id, &m.title); err != nil {
			return 0, err
		}
		matches = append(matches, m)
	}
	if err := rows.Err(); err != nil {
		return 0, err
	}

	switch len(matches) {
	case 0:
		return 0, fmt.Errorf("%q matched no groups", filter)
	case 1:
		return matches[0].id, nil
	default:
		var b strings.Builder
		fmt.Fprintf(&b, "%q matched %d groups — use an ID to disambiguate:\n", filter, len(matches))
		for _, m := range matches {
			fmt.Fprintf(&b, "  %d  %s\n", m.id, m.title)
		}
		return 0, fmt.Errorf("%s", strings.TrimRight(b.String(), "\n"))
	}
}

func printIntersection(db *sql.DB, groupIDs []int64) error {
	placeholders := make([]string, len(groupIDs))
	args := make([]any, len(groupIDs)+1)
	for i, id := range groupIDs {
		placeholders[i] = "?"
		args[i] = id
	}
	args[len(groupIDs)] = len(groupIDs)

	query := fmt.Sprintf(`
		SELECT u.id, u.first_name, u.last_name, u.username, u.is_bot
		FROM users u
		JOIN members m ON m.user_id = u.id
		WHERE m.group_id IN (%s)
		GROUP BY u.id
		HAVING COUNT(DISTINCT m.group_id) = ?
		ORDER BY u.first_name COLLATE NOCASE, u.last_name COLLATE NOCASE
	`, strings.Join(placeholders, ", "))

	rows, err := db.Query(query, args...)
	if err != nil {
		return fmt.Errorf("query: %w", err)
	}
	defer rows.Close()

	w := tabwriter.NewWriter(os.Stdout, 0, 0, 2, ' ', 0)
	fmt.Fprintln(w, "ID\tNAME\tUSERNAME")

	var count int
	for rows.Next() {
		var (
			id        int64
			firstName string
			lastName  string
			username  string
			isBot     int
		)
		if err := rows.Scan(&id, &firstName, &lastName, &username, &isBot); err != nil {
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

		fmt.Fprintf(w, "%d\t%s\t%s\n", id, name, handle)
		count++
	}
	w.Flush()

	if err := rows.Err(); err != nil {
		return err
	}

	fmt.Fprintf(os.Stderr, "%d users in intersection\n", count)
	return nil
}
