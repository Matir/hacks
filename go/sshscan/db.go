package main

import (
	"database/sql"
	"log"
	"time"

	_ "github.com/mattn/go-sqlite3"
)

type ScanDB struct {
	DB *sql.DB
}

func OpenDB(dsn string) (*ScanDB, error) {
	db, err := sql.Open("sqlite3", dsn)
	if err != nil {
		return nil, err
	}
	res := &ScanDB{
		DB: db,
	}
	if err := res.MaybeCreateDB(); err != nil {
		return nil, err
	}
	return res, nil
}

func (d *ScanDB) MaybeCreateDB() error {
	stmt := `CREATE TABLE IF NOT EXISTS hosts (
		ip TEXT PRIMARY KEY,
		server_version TEXT,
		scan_timestamp TEXT
	)`
	if _, err := d.DB.Exec(stmt); err != nil {
		return err
	}
	stmt = `CREATE TABLE IF NOT EXISTS host_keys (
		ip TEXT,
		key_type TEXT,
		fingerprint TEXT,
		key_data TEXT
	)`
	if _, err := d.DB.Exec(stmt); err != nil {
		return err
	}
	return nil
}

func (d *ScanDB) InsertResult(hs *HostScanner) error {
	tx, err := d.DB.Begin()
	if err != nil {
		return err
	}
	defer tx.Rollback()

	// Insert primary metadata
	stmt := `INSERT INTO hosts (ip, server_version, scan_timestamp) VALUES (?, ?, ?)`
	if _, err := tx.Exec(stmt, hs.Host, hs.ServerVersion, hs.ScanStart.Format(time.RFC3339)); err != nil {
		return err
	}

	// Insert public keys
	prep, err := tx.Prepare(`INSERT INTO host_keys (ip, key_type, fingerprint, key_data) VALUES (?, ?, ?, ?)`)
	if err != nil {
		return err
	}
	for ktype, fp := range hs.KeyFP {
		data, ok := hs.KeyData[ktype]
		if !ok {
			data = ""
		}
		if _, err := prep.Exec(hs.Host, ktype, fp, data); err != nil {
			return err
		}
	}
	return tx.Commit()
}

func (d *ScanDB) HasResultForHost(host string) bool {
	rows, err := d.DB.Query(`SELECT ip FROM hosts WHERE ip=? LIMIT 1`, host)
	if err != nil {
		log.Printf("Error querying for host: %s", err)
		return false
	}
	defer rows.Close()
	return rows.Next()
}

func (d *ScanDB) Close() error {
	return d.DB.Close()
}
