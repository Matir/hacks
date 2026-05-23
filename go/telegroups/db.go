package main

import (
	"database/sql"
	"fmt"

	_ "github.com/mattn/go-sqlite3"
)

const schema = `
CREATE TABLE IF NOT EXISTS groups (
    id    INTEGER PRIMARY KEY,
    title TEXT    NOT NULL,
    type  TEXT    NOT NULL   -- 'basic_group', 'supergroup', 'channel'
);
CREATE TABLE IF NOT EXISTS users (
    id         INTEGER PRIMARY KEY,
    first_name TEXT    NOT NULL DEFAULT '',
    last_name  TEXT    NOT NULL DEFAULT '',
    username   TEXT    NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS members (
    group_id INTEGER NOT NULL REFERENCES groups(id),
    user_id  INTEGER NOT NULL REFERENCES users(id),
    PRIMARY KEY (group_id, user_id)
);
`

// execer is satisfied by both *sql.DB and *sql.Tx.
type execer interface {
	Exec(query string, args ...any) (sql.Result, error)
}

func openDB(path string) (*sql.DB, error) {
	db, err := sql.Open("sqlite3", path+"?_foreign_keys=on")
	if err != nil {
		return nil, err
	}
	if _, err := db.Exec(schema); err != nil {
		db.Close()
		return nil, fmt.Errorf("init schema: %w", err)
	}
	return db, nil
}

func upsertGroup(ex execer, id int64, title, groupType string) error {
	_, err := ex.Exec(
		`INSERT INTO groups (id, title, type) VALUES (?, ?, ?)
		 ON CONFLICT(id) DO UPDATE SET title=excluded.title, type=excluded.type`,
		id, title, groupType,
	)
	return err
}

func upsertUser(ex execer, id int64, firstName, lastName, username string) error {
	_, err := ex.Exec(
		`INSERT INTO users (id, first_name, last_name, username) VALUES (?, ?, ?, ?)
		 ON CONFLICT(id) DO UPDATE SET
		     first_name=excluded.first_name,
		     last_name=excluded.last_name,
		     username=excluded.username`,
		id, firstName, lastName, username,
	)
	return err
}

func upsertMember(ex execer, groupID, userID int64) error {
	_, err := ex.Exec(
		`INSERT OR IGNORE INTO members (group_id, user_id) VALUES (?, ?)`,
		groupID, userID,
	)
	return err
}
