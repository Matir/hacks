package main

import (
	"bufio"
	"fmt"
	"io"
	"os"
	"strings"
	"sync"
)

const (
	WORKERS = 4
)

func main() {
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
	ch, err := LoadFromFile(os.Args[1])
	if err != nil {
		panic(err)
	}
	wg := &sync.WaitGroup{}
	wg.Add(WORKERS)
	for i := 0; i < WORKERS; i++ {
		w := Worker{
			DB:           db,
			WorkChan:     ch,
			DoneCallback: wg.Done,
		}
		go w.Run()
	}
	wg.Wait()
}

func LoadFromFile(filename string) (<-chan string, error) {
	ch := make(chan string)
	fp, err := os.Open(filename)
	if err != nil {
		return nil, err
	}
	go func() {
		defer fp.Close()
		defer close(ch)
		if strings.Contains(filename, ".json") {
			JSONFileReader(fp, ch)
		} else {
			PlainFileReader(fp, ch)
		}
	}()
	return ch, nil
}

func PlainFileReader(r io.Reader, ch chan<- string) {
	sc := bufio.NewScanner(r)
	for sc.Scan() {
		ch <- strings.TrimSpace(sc.Text())
	}
}

func JSONFileReader(r io.Reader, ch chan<- string) {
}
