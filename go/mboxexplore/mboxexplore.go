package main

import (
	"crypto/sha256"
	"database/sql"
	"encoding/hex"
	"flag"
	"fmt"
	"io"
	"log"
	"mime"
	"mime/multipart"
	"net/mail"
	"os"
	"path/filepath"
	"strings"
	"time"

	mbox "github.com/emersion/go-mbox"
	"github.com/google/uuid"
	_ "github.com/mattn/go-sqlite3"
)

var (
	mboxNameFlag = flag.String("mbox", "", "MBOX Filename")
	dbNameFlag   = flag.String("db", "", "Sqlite3 DB Filename")
	dataDirFlag  = flag.String("datadir", "", "Data Directory")
)

func usage() {
	flag.PrintDefaults()
	os.Exit(1)
}

func checkFlags() {
	if *mboxNameFlag == "" {
		usage()
	}
	if *dbNameFlag == "" {
		usage()
	}
	if *dataDirFlag == "" {
		usage()
	}
}

type MBoxExplorer struct {
	reader      *MBoxReader
	dataDirPath string
	db          *sql.DB
}

func main() {
	flag.Parse()
	checkFlags()
	mrdr := MustOpenMBox(*mboxNameFlag)
	defer mrdr.Close()
	if err := os.MkdirAll(*dataDirFlag, 0700); err != nil {
		panic(err)
	}
	db := mustOpenDB(*dbNameFlag)
	defer db.Close()
	exp := &MBoxExplorer{
		reader:      mrdr,
		dataDirPath: *dataDirFlag,
		db:          db,
	}
	if err := exp.Explore(); err != nil {
		panic(err)
	}
}

func (e *MBoxExplorer) Explore() error {
	for {
		msgrdr, err := e.reader.NextMessage()
		if err != nil {
			if err == io.EOF {
				return nil
			}
			return err
		}
		if err := e.ProcessMessageReader(msgrdr); err != nil {
			if strings.Contains(err.Error(), "malformed MIME header line") {
				log.Printf("error processing message: %s", err)
			} else {
				return err
			}
		}
	}
}

func (e *MBoxExplorer) ProcessMessageReader(rdr io.Reader) error {
	msg, err := mail.ReadMessage(rdr)
	if err != nil {
		return fmt.Errorf("error reading message: %w", err)
	}
	meta := ExtractMeta(msg)
	if meta == nil {
		return nil
	}
	fmt.Printf("Message-Id: %s From: %s\n", meta.MessageId, meta.From)
	attachMeta, err := e.ProcessAttachments(msg, meta)
	if err != nil {
		if strings.Contains(err.Error(), "duplicate parameter name") {
			log.Printf("error processing attachments: %v", err)
		} else {
			return fmt.Errorf("error processing attachments: %w", err)
		}
	}
	// Insert into db
	tx, err := e.db.Begin()
	if err != nil {
		return fmt.Errorf("error starting transaction: %w", err)
	}
	defer tx.Rollback()
	if _, err := tx.Exec(
		`INSERT OR IGNORE INTO messages(message_id, "from", from_email, "to", to_email, subject, date, content_type, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
		meta.MessageId,
		meta.From,
		meta.FromEmail,
		meta.To,
		meta.ToEmail,
		meta.Subject,
		meta.Date,
		meta.ContentType,
		meta.Timestamp.String(),
	); err != nil {
		return fmt.Errorf("error inserting message: %w", err)
	}
	for _, a := range meta.AllTo {
		if _, err := tx.Exec(
			`INSERT OR IGNORE INTO messages_to(message_id, to_email) VALUES(?, ?)`,
			meta.MessageId,
			a,
		); err != nil {
			return fmt.Errorf("error inserting into messages_to: %w", err)
		}
	}
	for _, a := range attachMeta {
		if _, err := tx.Exec(
			`INSERT OR IGNORE INTO attachments(message_id, hash, content_type, filename, length) VALUES(?, ?, ?, ?, ?)`,
			meta.MessageId,
			a.Hash,
			a.ContentType,
			a.Filename,
			a.Length,
		); err != nil {
			return fmt.Errorf("error inserting attachment data: %w", err)
		}
	}
	if err := tx.Commit(); err != nil {
		return fmt.Errorf("error committing transaction: %w", err)
	}
	return nil
}

func (e *MBoxExplorer) ProcessAttachments(msg *mail.Message, meta *MessageMeta) ([]*AttachmentMeta, error) {
	if meta.ContentType == "" {
		return nil, nil
	}
	rv := make([]*AttachmentMeta, 0)
	mediaType, params, err := mime.ParseMediaType(meta.ContentType)
	if err != nil {
		return nil, fmt.Errorf("error parsing media type: %w", err)
	}
	if !strings.HasPrefix(mediaType, "multipart/") {
		return nil, nil
	}
	mrdr := multipart.NewReader(msg.Body, params["boundary"])
	for {
		p, err := mrdr.NextPart()
		if err == io.EOF {
			return rv, nil
		} else if err != nil {
			return rv, fmt.Errorf("error getting next multpart: %w", err)
		}
		fname := p.FileName()
		ctype := p.Header.Get("Content-Type")
		hasher := sha256.New()
		// write to temporary file
		tmpf := filepath.Join(e.dataDirPath, fmt.Sprintf(".tmp.%s", uuid.NewString()))
		fp, err := os.Create(tmpf)
		if err != nil {
			return rv, fmt.Errorf("error opening attachment file %s: %w", tmpf, err)
		}
		tee := io.TeeReader(p, hasher)
		nbytes, err := io.Copy(fp, tee)
		fp.Close()
		if err != nil {
			if err == io.ErrUnexpectedEOF {
				log.Printf("Unexpected EOF reading attachments in %s", meta.MessageId)
				return rv, nil
			} else {
				return rv, fmt.Errorf("error writing attachment %d (%s): %w", len(rv), params["boundary"], err)
			}
		}
		// now rename
		hash := hex.EncodeToString(hasher.Sum(nil))
		destf := filepath.Join(e.dataDirPath, hash)
		if err := os.Rename(tmpf, destf); err != nil {
			return rv, fmt.Errorf("error renaming temp file: %w", err)
		}
		meta := &AttachmentMeta{
			MessageId:   meta.MessageId,
			Hash:        hash,
			ContentType: ctype,
			Filename:    fname,
			Length:      nbytes,
		}
		rv = append(rv, meta)
	}
}

type MessageMeta struct {
	MessageId   string
	From        string
	FromEmail   string
	To          string
	ToEmail     string
	Subject     string
	Date        string
	ContentType string
	Timestamp   time.Time
	AllTo       []string
}

type AttachmentMeta struct {
	MessageId   string
	Hash        string
	ContentType string
	Filename    string
	Length      int64
}

func ExtractMeta(msg *mail.Message) *MessageMeta {
	if strings.Contains(msg.Header.Get("X-Gmail-Labels"), "Chat") {
		// not interested in chat
		return nil
	}
	rv := &MessageMeta{
		MessageId:   strings.TrimSuffix(strings.TrimPrefix(msg.Header.Get("Message-Id"), "<"), ">"),
		From:        msg.Header.Get("From"),
		To:          msg.Header.Get("To"),
		Subject:     msg.Header.Get("Subject"),
		Date:        msg.Header.Get("Date"),
		ContentType: msg.Header.Get("Content-type"),
	}
	if rv.MessageId == "" {
		rv.MessageId = uuid.NewString()
	}
	if alist, err := msg.Header.AddressList("From"); err == nil {
		if len(alist) > 0 {
			rv.FromEmail = alist[0].Address
		}
	} else {
		log.Printf("Error parsing from: %s", err)
	}
	if alist, err := msg.Header.AddressList("To"); err == nil {
		if len(alist) > 0 {
			rv.ToEmail = alist[0].Address
		}
		for _, a := range alist {
			rv.AllTo = append(rv.AllTo, a.Address)
		}
	} else {
		log.Printf("Error parsing to: %s", err)
	}
	if when, err := msg.Header.Date(); err != nil {
		log.Printf("Error getting date: %s", err)
	} else {
		rv.Timestamp = when
	}
	return rv
}

type MBoxReader struct {
	*mbox.Reader
	fp *os.File
}

func (r *MBoxReader) Close() error {
	if r.fp == nil {
		return nil
	}
	e := r.fp.Close()
	r.fp = nil
	return e
}

func MustOpenMBox(filename string) *MBoxReader {
	fp, err := os.Open(filename)
	if err != nil {
		panic(err)
	}
	mrdr := mbox.NewReader(fp)
	return &MBoxReader{Reader: mrdr, fp: fp}
}

func mustOpenDB(filename string) *sql.DB {
	db, err := sql.Open("sqlite3", filename)
	if err != nil {
		panic(err)
	}
	query := `
		CREATE TABLE IF NOT EXISTS messages (
			message_id TEXT UNIQUE NOT NULL,
			"from" TEXT NOT NULL,
			from_email TEXT NOT NULL,
			"to" TEXT NOT NULL,
			to_email TEXT NOT NULL,
			subject TEXT NOT NULL,
			date TEXT NOT NULL,
			content_type TEXT NOT NULL,
			timestamp TEXT,
			PRIMARY KEY (message_id)
		);
		CREATE TABLE IF NOT EXISTS messages_to (
			message_id TEXT NOT NULL,
			to_email TEXT NOT NULL,
			PRIMARY KEY (message_id, to_email)
		);
		CREATE TABLE IF NOT EXISTS attachments (
			message_id TEXT NOT NULL,
			hash TEXT NOT NULL,
			content_type TEXT NOT NULL,
			filename TEXT NOT NULL,
			length INT NOT NULL,
			PRIMARY KEY (message_id, hash)
		);`
	if _, err := db.Exec(query); err != nil {
		panic(err)
	}
	return db
}
