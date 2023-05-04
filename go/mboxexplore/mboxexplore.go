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
			return err
		}
	}
}

func (e *MBoxExplorer) ProcessMessageReader(rdr io.Reader) error {
	msg, err := mail.ReadMessage(rdr)
	if err != nil {
		return err
	}
	meta := ExtractMeta(msg)
	fmt.Printf("From: %s\n", meta.From)
	if attachMeta, err := e.ProcessAttachments(msg, meta); err != nil {
		return err
	}
	// Insert into db
	tx, err := e.db.Begin()
	if err != nil {
		return err
	}
	defer tx.Rollback()
	// TODO: do the real insert
	return nil
}

func (e *MBoxExplorer) ProcessAttachments(msg *mail.Message, meta *MessageMeta) ([]*AttachmentMeta, error) {
	rv := make([]*AttachmentMeta, 0)
	mediaType, params, err := mime.ParseMediaType(meta.ContentType)
	if err != nil {
		return err
	}
	if !strings.HasPrefix(mediaType, "multipart/") {
		return nil
	}
	mrdr := multipart.NewReader(msg.Body, params["boundary"])
	for {
		p, err := mrdr.NextPart()
		if err == io.EOF {
			return nil
		} else if err != nil {
			return err
		}
		fname := p.FileName()
		ctype := p.Header.Get("Content-Type")
		hasher := sha256.New()
		// write to temporary file
		tmpf := filepath.Join(e.dataDirPath, fmt.Sprintf(".tmp.%s", uuid.NewString()))
		fp, err := os.Create(tmpf)
		if err != nil {
			return err
		}
		tee := io.TeeReader(p, hasher)
		nbytes, err := io.Copy(fp, tee)
		fp.Close()
		if err != nil {
			return err
		}
		// now rename
		hash := hex.EncodeToString(hasher.Sum(nil))
		destf := filepath.Join(e.dataDirPath, hash)
		if err := os.Rename(tmpf, destf); err != nil {
			return err
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
}

type AttachmentMeta struct {
	MessageId   string
	Hash        string
	ContentType string
	Filename    string
	Length      int64
}

func ExtractMeta(msg *mail.Message) *MessageMeta {
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
			from TEXT NOT NULL,
			from_email TEXT NOT NULL,
			to TEXT NOT NULL,
			to_email TEXT NOT NULL,
			subject TEXT NOT NULL,
			date TEXT NOT NULL,
			content_type TEXT NOT NULL,
			timestamp TEXT
		);
		CREATE TABLE IF NOT EXISTS attachments (
			message_id TEXT NOT NULL,
			hash TEXT NOT NULL,
			content_type TEXT NOT NULL,
			filename TEXT NOT NULL,
			length INT NOT NULL
		);`
	if err := db.Exec(query); err != nil {
		panic(err)
	}
}
