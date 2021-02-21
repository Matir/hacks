package main

import (
	"bufio"
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/gorilla/websocket"
	_ "github.com/mattn/go-sqlite3"
)

const (
	tblName       = "samples"
	cachedSamples = 128
	webAddr       = ":9333"
	pongWait      = 60 * time.Second
)

type PowerLogger struct {
	srcFilename string
	nowFunc     func() time.Time
	debug       bool
	handlers    []*PLHandlerChan
	wg          sync.WaitGroup
	blocking    bool
}

type PowerLogRecord struct {
	Timestamp  time.Time
	SampleID   uint32
	ChannelID  uint8
	Millivolts int32
	Milliamps  int32
}

type PowerLogHandler interface {
	Name() string
	HandleRecords(...PowerLogRecord) error
}

type PLHandlerChan struct {
	handler PowerLogHandler
	ch      chan []PowerLogRecord
}

type PowerDBLogger struct {
	dbName string
	db     *sql.DB
}

type PowerWebServer struct {
	sampleCache []PowerLogRecord
	httpMux     *http.ServeMux
	wsChans     map[chan []PowerLogRecord]bool
}

var upgrader = websocket.Upgrader{}

func (pl *PowerLogger) Run() error {
	if fp, err := os.Open(pl.srcFilename); err != nil {
		return err
	} else {
		defer fp.Close()
		err := pl.ProcessFile(fp)
		pl.Finish()
		return err
	}
}

func (pl *PowerLogger) ProcessFile(fp *os.File) error {
	sc := bufio.NewScanner(fp)
	for sc.Scan() {
		if records, err := pl.ParseRecords(sc.Text()); err != nil {
			return err
		} else {
			if err := pl.HandleRecords(records...); err != nil {
				return err
			}
		}
	}
	return sc.Err()
}

func (pl *PowerLogger) Finish() {
	for _, h := range pl.handlers {
		close(h.ch)
	}
	pl.wg.Wait()
}

func (pl *PowerLogger) HandleRecords(records ...PowerLogRecord) error {
	for _, h := range pl.handlers {
		if pl.blocking {
			h.ch <- records
		} else {
			select {
			case h.ch <- records:
				continue
			default:
				log.Printf("Queue for handler %s is blocking.", h.handler.Name())
			}
		}
	}
	return nil
}

func (pl *PowerLogger) RegisterHandler(handler PowerLogHandler) {
	ch := make(chan []PowerLogRecord, 32)
	h := &PLHandlerChan{
		ch:      ch,
		handler: handler,
	}
	pl.handlers = append(pl.handlers, h)
	pl.wg.Add(1)
	go func() {
		for e := range ch {
			if err := handler.HandleRecords(e...); err != nil {
				log.Printf("Handler %s failed: %s", handler.Name(), err)
			}
		}
		pl.wg.Done()
	}()
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

func NewPowerDBLogger(dbName string) (*PowerDBLogger, error) {
	dbl := &PowerDBLogger{
		dbName: dbName,
	}
	if db, err := sql.Open("sqlite3", dbName); err != nil {
		return nil, err
	} else {
		dbl.db = db
		dbl.CreateDB()
	}
	return dbl, nil
}

func (dbl *PowerDBLogger) Name() string {
	return "PowerDBLogger"
}

func (pl *PowerDBLogger) HandleRecords(records ...PowerLogRecord) error {
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

func (pl *PowerDBLogger) CreateDB() error {
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

func NewPowerWebServer() *PowerWebServer {
	pws := &PowerWebServer{
		sampleCache: make([]PowerLogRecord, 0, cachedSamples*2),
		wsChans:     make(map[chan []PowerLogRecord]bool),
	}
	// TODO: serve static
	mux := http.NewServeMux()
	mux.HandleFunc("/readings", pws.GetReadings)
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		http.ServeFile(w, r, "index.html")
	})
	mux.HandleFunc("/app.js", func(w http.ResponseWriter, r *http.Request) {
		http.ServeFile(w, r, "app.js")
	})
	mux.HandleFunc("/ws", pws.HandleSocket)
	pws.httpMux = mux
	go http.ListenAndServe(webAddr, mux)
	return pws
}

func (pws *PowerWebServer) Name() string {
	return "PowerWebServer"
}

func (pws *PowerWebServer) HandleRecords(rec ...PowerLogRecord) error {
	pws.sampleCache = append(pws.sampleCache, rec...)
	if len(pws.sampleCache) > cachedSamples {
		pws.sampleCache = pws.sampleCache[len(pws.sampleCache)-cachedSamples:]
	}
	for ch, _ := range pws.wsChans {
		select {
		case ch <- rec:
			continue
		default:
			continue
		}
	}
	return nil
}

func (pws *PowerWebServer) GetReadings(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-type", "application/json")
	enc := json.NewEncoder(w)
	enc.Encode(pws.sampleCache)
}

func (pws *PowerWebServer) HandleSocket(w http.ResponseWriter, r *http.Request) {
	ws, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		log.Println(err)
		return
	}
	ch := make(chan []PowerLogRecord, 10)
	pws.wsChans[ch] = true
	defer func() {
		ws.Close()
		delete(pws.wsChans, ch)
		close(ch)
	}()
	ws.SetReadDeadline(time.Now().Add(pongWait))
	ws.SetPongHandler(func(string) error { ws.SetReadDeadline(time.Now().Add(pongWait)); return nil })
	// Send data from the channel
	go func() {
		pingTicker := time.NewTicker(pongWait / 2)
		defer pingTicker.Stop()
		for {
			select {
			case e, ok := <-ch:
				if !ok {
					return
				}
				if err := ws.WriteJSON(e); err != nil {
					return
				}
			case <-pingTicker.C:
				if err := ws.WriteMessage(websocket.PingMessage, []byte{}); err != nil {
					return
				}
			}
		}
	}()
	// Read until socket close
	for {
		_, _, err := ws.ReadMessage()
		if err != nil {
			break
		}
	}
}

func main() {
	if len(os.Args) != 3 {
		fmt.Printf("Usage: %s <src> <db>\n", os.Args[0])
		os.Exit(1)
	}
	logger := &PowerLogger{
		srcFilename: os.Args[1],
		nowFunc:     time.Now,
		blocking:    true,
	}
	dbHandler, err := NewPowerDBLogger(os.Args[2])
	if err != nil {
		fmt.Printf("Error: %s\n", err)
		os.Exit(1)
	}
	logger.RegisterHandler(dbHandler)
	pws := NewPowerWebServer()
	logger.RegisterHandler(pws)
	if err := logger.Run(); err != nil {
		fmt.Printf("Error: %s\n", err)
		os.Exit(1)
	}
}
