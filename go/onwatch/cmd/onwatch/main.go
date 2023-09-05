package main

import (
	"fmt"
	"log"

	"github.com/Matir/hacks/go/onwatch"
)

func main() {
	logger := log.Default()
	watcher, err := onwatch.NewRecursiveWatcher()
	if err != nil {
		panic(err)
	}
	watcher.SetLogger(logger)

	go func() {
		for {
			select {
			case err, ok := <-watcher.Errors:
				if !ok {
					return
				}
				fmt.Printf("Error: %v", err)
			case e, ok := <-watcher.Events:
				if !ok {
					return
				}
				fmt.Printf("Event: %s", e)
			}
		}
	}()

	watcher.Add(...)

	c := make(chan bool)
	// block forever
	<-c
}
