package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"os"
	"os/signal"
	"strings"
	"sync"
	"sync/atomic"
)

const (
	WORKERS                  = 16
	PrintWorkInterval uint64 = 1000
)

type WorkCounter struct {
	count    uint64
	reported uint64
	mu       sync.Mutex
}

func main() {
	ctr := &WorkCounter{}
	if len(os.Args) != 3 {
		fmt.Fprintf(os.Stderr, "Usage: %s <iplist> <db>\n", os.Args[0])
		os.Exit(1)
		return
	}

	dsn := fmt.Sprintf("file:%s?_journal_mode=WAL", os.Args[2])
	db, err := OpenDB(dsn)
	if err != nil {
		panic("Error opening DB: " + err.Error())
	}
	defer db.Close()

	// Handle ctrl+c
	stopChan := make(chan bool, 1)
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, os.Interrupt)
	go func() {
		<-sigChan
		log.Printf("Received SIGINT, shutting down.  Press CTRL+C again to exit immediately.")
		stopChan <- true
		<-sigChan
		os.Exit(0)
	}()

	ch, err := LoadFromFile(os.Args[1], stopChan)
	if err != nil {
		panic(err)
	}
	wg := &sync.WaitGroup{}
	wg.Add(WORKERS)
	for i := 0; i < WORKERS; i++ {
		w := Worker{
			DB:               db,
			WorkChan:         ch,
			DoneCallback:     wg.Done,
			WorkDoneCallback: ctr.Add,
		}
		go w.Run()
	}
	wg.Wait()
	log.Printf("Scanned %d hosts total...", ctr.count)
}

func LoadFromFile(filename string, stop <-chan bool) (<-chan string, error) {
	ch := make(chan string)
	fp, err := os.Open(filename)
	if err != nil {
		return nil, err
	}
	go func() {
		defer fp.Close()
		defer close(ch)
		if strings.Contains(filename, ".json") {
			JSONFileReader(fp, ch, stop)
		} else {
			PlainFileReader(fp, ch, stop)
		}
	}()
	return ch, nil
}

func PlainFileReader(r io.Reader, ch chan<- string, stop <-chan bool) {
	sc := bufio.NewScanner(r)
	for sc.Scan() {
		select {
		case <-stop:
			return
		case ch <- strings.TrimSpace(sc.Text()):
			continue
		}
	}
}

type JSONEntry struct {
	IP string `json:"ip"`
}

// Read an array of JSON objects with an "ip" field in each object.
func JSONFileReader(r io.Reader, ch chan<- string, stop <-chan bool) {
	dec := json.NewDecoder(r)
	// Progressive read for large files
	t, err := dec.Token()
	if err != nil {
		log.Printf("Error getting first token: %s", err)
		return
	}
	if _, ok := t.(json.Delim); !ok {
		log.Printf("Expected json bracket, got %T: %v", t, t)
		return
	}

	// Start reading the elements
	for dec.More() {
		var e JSONEntry
		if err := dec.Decode(&e); err != nil {
			log.Printf("Error getting object: %s", err)
			return
		}
		select {
		case ch <- e.IP:
			continue
		case <-stop:
			return
		}
	}
}

func (w *WorkCounter) Add(inc uint64) {
	if atomic.AddUint64(&w.count, inc) >= (atomic.LoadUint64(&w.reported) + PrintWorkInterval) {
		w.mu.Lock()
		defer w.mu.Unlock()
		// Verify it's still greater
		target := atomic.LoadUint64(&w.reported) + PrintWorkInterval
		if atomic.LoadUint64(&w.count) >= target {
			atomic.AddUint64(&w.reported, PrintWorkInterval)
			log.Printf("Scanned %d hosts...", target)
		}
	}
}
