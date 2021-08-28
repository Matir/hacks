package main

import (
	"log"
)

const (
	WorkReportInterval uint64 = 100
)

type Worker struct {
	DB               *ScanDB
	WorkChan         <-chan string
	DoneCallback     func()
	WorkDoneCallback func(uint64)
	workCount        uint64
}

func (w *Worker) Run() {
	defer func() {
		w.ReportWorkDone()
		if w.DoneCallback != nil {
			w.DoneCallback()
		}
	}()
	for unit := range w.WorkChan {
		if w.DB.HasResultForHost(unit) {
			// Already scanned, skip
			continue
		}
		hs := NewHostScanner(unit)
		if err := hs.Scan(); err != nil {
			log.Printf("Error scanning: %s", err)
		} else {
			w.workCount++
			if err := w.DB.InsertResult(hs); err != nil {
				log.Printf("Error inserting: %s", err)
			}
		}
		if w.workCount >= WorkReportInterval {
			w.ReportWorkDone()
		}
	}
}

func (w *Worker) ReportWorkDone() {
	if w.WorkDoneCallback != nil {
		w.WorkDoneCallback(w.workCount)
	}
	w.workCount = 0
}
