package main

import (
	"bufio"
	"database/sql"
	"fmt"
	_ "github.com/mattn/go-sqlite3"
	"log"
	"os"
	"strconv"
	"strings"
	"time"
)

const (
	tblName = "samples"
)

type PowerLogger struct {
	srcFilename string
	dbName      string
	db          *sql.DB
	nowFunc     func() time.Time
	debug       bool
}

type PowerLogRecord struct {
	Timestamp  time.Time
	SampleID   uint32
	ChannelID  uint8
	Millivolts int32
	Milliamps  int32
}

func (pl *PowerLogger) Run() error {
	if db, err := sql.Open("sqlite3", pl.dbName); err != nil {
		return err
	} else {
		defer db.Close()
		pl.db = db
		pl.CreateDB()
		if fp, err := os.Open(pl.srcFilename); err != nil {
			return err
		} else {
			defer fp.Close()
			return pl.ProcessFile(fp)
		}
	}
}

func (pl *PowerLogger) ProcessFile(fp *os.File) error {
	sc := bufio.NewScanner(fp)
	for sc.Scan() {
		if records, err := pl.ParseRecords(sc.Text()); err != nil {
			return err
		} else {
			if err := pl.SaveRecords(records...); err != nil {
				return err
			}
		}
	}
	return sc.Err()
}

func (pl *PowerLogger) ParseRecords(line string) ([]PowerLogRecord, error) {
	now := pl.nowFunc()
	line = strings.TrimRight(line, "| \n")
	pieces := strings.Split(line, "|")
	chId := uint8(1)
	counter, err := strconv.ParseInt(pieces[0], 10, 32)
	if err != nil {
		return nil, err
	}
	res := make([]PowerLogRecord, len(pieces)/2)
	for i := 1; i < len(pieces); i += 2 {
		mv, err := strconv.ParseInt(pieces[i], 10, 32)
		if err != nil {
			return nil, err
		}
		ma, err := strconv.ParseInt(pieces[i+1], 10, 32)
		if err != nil {
			return nil, err
		}
		res[i/2] = PowerLogRecord{
			Timestamp:  now,
			SampleID:   uint32(counter),
			ChannelID:  chId,
			Millivolts: int32(mv),
			Milliamps:  int32(ma),
		}
		chId++
	}
	return res, nil
}

func (pl *PowerLogger) SaveRecords(records ...PowerLogRecord) error {
	tx, err := pl.db.Begin()
	if err != nil {
		return err
	}
	qry := `insert into %s (timestamp, sample_id, channel_id, millivolts, milliamps) VALUES(?, ?, ?, ?, ?);`
	qry = fmt.Sprintf(qry, tblName)
	for _, r := range records {
		if _, err := tx.Exec(qry, r.Timestamp, r.SampleID, r.ChannelID, r.Millivolts, r.Milliamps); err != nil {
			tx.Rollback()
			return err
		}
	}
	return tx.Commit()
}

func (pl *PowerLogger) CreateDB() error {
	stmt := `CREATE TABLE %s (
		timestamp TEXT,
		sample_id INT,
		channel_id TINYINT,
		millivolts INT,
		milliamps INT
	);
	`
	stmt = fmt.Sprintf(stmt, tblName)
	if _, err := pl.db.Exec(stmt); err != nil {
		return err
	}
	return nil
}

func main() {
	if len(os.Args) != 3 {
		fmt.Printf("Usage: %s <src> <db>\n", os.Args[0])
		os.Exit(1)
	}
	logger := &PowerLogger{
		srcFilename: os.Args[1],
		dbName:      os.Args[2],
		nowFunc:     time.Now,
	}
	if err := logger.Run(); err != nil {
		fmt.Printf("Error: %s\n", err)
		os.Exit(1)
	}
}
