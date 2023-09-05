package onwatch

import (
	"errors"
	"io/fs"
	"log"
	"os"
	"path/filepath"

	"github.com/fsnotify/fsnotify"
)

type Logger interface {
	Print(...any)
	Printf(string, ...any)
}

var (
	ErrNotDirectory = errors.New("not a directory")
)

type RecursiveWatcher struct {
	Events chan fsnotify.Event
	Errors chan error

	logger      Logger
	stopChan    chan bool
	stoppedChan chan bool

	// Underlying watcher
	fsnWatcher *fsnotify.Watcher
}

func NewRecursiveWatcher() (*RecursiveWatcher, error) {
	w, err := fsnotify.NewWatcher()
	if err != nil {
		return nil, err
	}
	rw := &RecursiveWatcher{
		Events:      make(chan fsnotify.Event),
		Errors:      make(chan error),
		stopChan:    make(chan bool),
		stoppedChan: make(chan bool),
		fsnWatcher:  w,
	}
	go rw.runLoop()
	return rw, nil
}

func (rw *RecursiveWatcher) SetLogger(logger Logger) {
	rw.logger = logger
}

func (rw *RecursiveWatcher) Add(p string) error {
	newp, err := filepath.Abs(p)
	if err != nil {
		return err
	}
	p = newp
	if dir, err := isDir(p); err != nil {
		return err
	} else if !dir {
		return ErrNotDirectory
	}
	// handle recursion
	if err := filepath.WalkDir(p, func(p string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		// TODO: filter/ignored paths
		if !d.IsDir() {
			return nil
		}
		// TODO: add to watcher
		rw.logf("Saw dir: %s", p)
		return nil
	}); err != nil {
		return err
	}
	return nil
}

func (rw *RecursiveWatcher) logf(format string, v ...any) {
	if rw.logger == nil {
		return
	}
	rw.logger.Printf(format, v...)
}

func (rw *RecursiveWatcher) runLoop() {
	defer func() {
		close(rw.stoppedChan)
	}()
	for {
		select {
		case <-rw.stopChan:
			return
		case err, ok := <-rw.fsnWatcher.Errors:
			if !ok {
				return
			}
			rw.logf("Saw error: %v", err)
			if !rw.sendError(err) {
				rw.logf("Unable to send error!")
				return
			}
		case e, ok := <-rw.fsnWatcher.Events:
			if !ok {
				return
			}
			rw.logf("Saw event: %s", e)
			// TODO: add watch on mkdir
			if !rw.sendEvent(e) {
				rw.logf("Unable to send event!")
				return
			}
		}
	}
}

func (rw *RecursiveWatcher) sendError(err error) bool {
	select {
	case rw.Errors <- err:
		return true
	case <-rw.stopChan:
		return false
	}
}

func (rw *RecursiveWatcher) sendEvent(e fsnotify.Event) bool {
	select {
	case rw.Events <- e:
		return true
	case <-rw.stopChan:
		return false
	}
}

func (rw *RecursiveWatcher) Close() error {
	rw.fsnWatcher.Close()
	close(rw.stopChan)
	<-rw.stoppedChan
	return nil
}

func isDir(p string) (bool, error) {
	fi, err := os.Stat(p)
	if err != nil {
		return false, err
	}
	return fi.IsDir(), nil
}

// guarantee certain types meet the interfaces
var (
	_ Logger = (*log.Logger)(nil)
)
