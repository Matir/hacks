package main

import (
	"database/sql"
	"fmt"
	"strings"
	"time"

	_ "github.com/mattn/go-sqlite3"
)

const createSchema = `
CREATE TABLE IF NOT EXISTS groups (
    id                 INTEGER PRIMARY KEY,
    title              TEXT    NOT NULL,
    type               TEXT    NOT NULL,    -- 'basic_group', 'supergroup', 'channel'
    member_count       INTEGER NOT NULL DEFAULT 0,
    members_fetched_at INTEGER             -- unix timestamp; NULL = never fetched
);
CREATE TABLE IF NOT EXISTS users (
    id         INTEGER PRIMARY KEY,
    first_name TEXT    NOT NULL DEFAULT '',
    last_name  TEXT    NOT NULL DEFAULT '',
    username   TEXT    NOT NULL DEFAULT '',
    is_bot     INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS members (
    group_id     INTEGER NOT NULL REFERENCES groups(id),
    user_id      INTEGER NOT NULL REFERENCES users(id),
    status       TEXT    NOT NULL DEFAULT 'member', -- owner|admin|member|restricted|left|banned
    joined_at    INTEGER NOT NULL DEFAULT 0,        -- unix timestamp from Telegram; 0 = unknown
    last_seen_at INTEGER NOT NULL DEFAULT 0,        -- unix timestamp of last successful fetch
    PRIMARY KEY (group_id, user_id)
);
CREATE INDEX IF NOT EXISTS idx_members_user_id ON members(user_id);
`

// migrations add columns absent from databases created before the current
// schema. "duplicate column name" is silently ignored so the list is safe to
// run against an already up-to-date database.
var migrations = []string{
	`ALTER TABLE groups ADD COLUMN member_count INTEGER NOT NULL DEFAULT 0`,
	`ALTER TABLE groups ADD COLUMN members_fetched_at INTEGER`,
	`ALTER TABLE users ADD COLUMN is_bot INTEGER NOT NULL DEFAULT 0`,
	`ALTER TABLE members ADD COLUMN status TEXT NOT NULL DEFAULT 'member'`,
	`ALTER TABLE members ADD COLUMN joined_at INTEGER NOT NULL DEFAULT 0`,
	`ALTER TABLE members ADD COLUMN last_seen_at INTEGER NOT NULL DEFAULT 0`,
}

// execer is satisfied by both *sql.DB and *sql.Tx.
type execer interface {
	Exec(query string, args ...any) (sql.Result, error)
}

func openDB(path string) (*sql.DB, error) {
	db, err := sql.Open("sqlite3", path+"?_foreign_keys=on")
	if err != nil {
		return nil, err
	}
	if _, err := db.Exec(createSchema); err != nil {
		db.Close()
		return nil, fmt.Errorf("init schema: %w", err)
	}
	for _, m := range migrations {
		if _, err := db.Exec(m); err != nil && !strings.Contains(err.Error(), "duplicate column name") {
			db.Close()
			return nil, fmt.Errorf("migration: %w", err)
		}
	}
	return db, nil
}

func upsertGroup(ex execer, id int64, title, groupType string, memberCount int32) error {
	_, err := ex.Exec(
		`INSERT INTO groups (id, title, type, member_count) VALUES (?, ?, ?, ?)
		 ON CONFLICT(id) DO UPDATE SET
		     title=excluded.title,
		     type=excluded.type,
		     member_count=excluded.member_count`,
		id, title, groupType, memberCount,
	)
	return err
}

// needsMemberFetch reports whether the group's member list should be fetched.
// Returns true when threshold is zero (no -since flag), when the group has
// never been fetched, or when the last fetch predates threshold.
func needsMemberFetch(tx *sql.Tx, chatID int64, threshold time.Time) bool {
	if threshold.IsZero() {
		return true
	}
	var fetchedAt sql.NullInt64
	if err := tx.QueryRow(`SELECT members_fetched_at FROM groups WHERE id = ?`, chatID).Scan(&fetchedAt); err != nil {
		return true
	}
	if !fetchedAt.Valid {
		return true
	}
	return time.Unix(fetchedAt.Int64, 0).Before(threshold)
}

func markGroupFetched(ex execer, chatID int64) error {
	_, err := ex.Exec(
		`UPDATE groups SET members_fetched_at = ? WHERE id = ?`,
		time.Now().Unix(), chatID,
	)
	return err
}

func upsertUser(ex execer, id int64, firstName, lastName, username string, isBot bool) error {
	isBot01 := 0
	if isBot {
		isBot01 = 1
	}
	_, err := ex.Exec(
		`INSERT INTO users (id, first_name, last_name, username, is_bot) VALUES (?, ?, ?, ?, ?)
		 ON CONFLICT(id) DO UPDATE SET
		     first_name=excluded.first_name,
		     last_name=excluded.last_name,
		     username=excluded.username,
		     is_bot=excluded.is_bot`,
		id, firstName, lastName, username, isBot01,
	)
	return err
}

func upsertMember(ex execer, groupID, userID, lastSeenAt int64, status string, joinedAt int32) error {
	_, err := ex.Exec(
		`INSERT INTO members (group_id, user_id, last_seen_at, status, joined_at) VALUES (?, ?, ?, ?, ?)
		 ON CONFLICT(group_id, user_id) DO UPDATE SET
		     last_seen_at=excluded.last_seen_at,
		     status=excluded.status`,
		// joined_at is intentionally not updated: it records when the user first joined.
		groupID, userID, lastSeenAt, status, joinedAt,
	)
	return err
}
