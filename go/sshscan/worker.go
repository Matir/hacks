package main

import (
	"log"
)

type Worker struct {
	DB           *ScanDB
	WorkChan     <-chan string
	DoneCallback func()
}

func (w *Worker) Run() {
	defer func() {
		if w.DoneCallback != nil {
			w.DoneCallback()
		}
	}()
	for unit := range w.WorkChan {
		hs := NewHostScanner(unit)
		if err := hs.Scan(); err != nil {
			log.Printf("Error scanning: %s", err)
		} else {
			if err := w.DB.InsertResult(hs); err != nil {
				log.Printf("Error inserting: %s", err)
			}
		}
	}
}
