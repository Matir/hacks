package server

import (
	"fmt"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"sync"

	"github.com/fsnotify/fsnotify"
	"github.com/matir/hacks/go/mdtool/converter"
)

// Server holds the configuration for the web server.
type Server struct {
	Dir       string
	Listen    string
	OnlyMD    bool
	Converter *converter.Converter
	Watch     bool

	mu      sync.Mutex
	clients []chan struct{}
}

// New returns a new Server with the specified options.
func New(dir, listen string, onlyMD bool, c *converter.Converter) *Server {
	if dir == "" {
		dir = "."
	}
	if listen == "" {
		listen = "127.0.0.1:7768"
	}
	return &Server{
		Dir:       dir,
		Listen:    listen,
		OnlyMD:    onlyMD,
		Converter: c,
	}
}

// Serve starts the web server.
func (s *Server) Serve() error {
	if s.Watch {
		go s.watchFiles()
	}

	http.HandleFunc("/events", s.handleEvents)
	http.HandleFunc("/", s.handle)
	fmt.Printf("Starting server on %s serving %s\n", s.Listen, s.Dir)
	return http.ListenAndServe(s.Listen, nil)
}

func (s *Server) handleEvents(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("Connection", "keep-alive")

	client := make(chan struct{})
	s.mu.Lock()
	s.clients = append(s.clients, client)
	s.mu.Unlock()

	defer func() {
		s.mu.Lock()
		for i, c := range s.clients {
			if c == client {
				s.clients = append(s.clients[:i], s.clients[i+1:]...)
				break
			}
		}
		s.mu.Unlock()
	}()

	notify := r.Context().Done()
	for {
		select {
		case <-client:
			fmt.Fprintf(w, "data: reload\n\n")
			if f, ok := w.(http.Flusher); ok {
				f.Flush()
			}
		case <-notify:
			return
		}
	}
}

func (s *Server) notifyClients() {
	s.mu.Lock()
	defer s.mu.Unlock()
	for _, client := range s.clients {
		select {
		case client <- struct{}{}:
		default:
		}
	}
}

func (s *Server) watchFiles() {
	watcher, err := fsnotify.NewWatcher()
	if err != nil {
		log.Printf("Watcher error: %v", err)
		return
	}
	defer watcher.Close()

	filepath.Walk(s.Dir, func(path string, info os.FileInfo, err error) error {
		if err == nil && info.IsDir() {
			watcher.Add(path)
		}
		return nil
	})

	for {
		select {
		case event, ok := <-watcher.Events:
			if !ok {
				return
			}
			if event.Op&fsnotify.Write == fsnotify.Write {
				if strings.HasSuffix(event.Name, ".md") {
					s.notifyClients()
				}
			}
		case err, ok := <-watcher.Errors:
			if !ok {
				return
			}
			log.Printf("Watcher error: %v", err)
		}
	}
}

func (s *Server) handle(w http.ResponseWriter, r *http.Request) {
	relPath := strings.TrimPrefix(r.URL.Path, "/")
	fullPath := filepath.Join(s.Dir, relPath)

	info, err := os.Stat(fullPath)
	if err != nil {
		if os.IsNotExist(err) {
			http.NotFound(w, r)
			return
		}
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	if info.IsDir() {
		// Look for index.md or README.md
		for _, name := range []string{"index.md", "README.md"} {
			indexPath := filepath.Join(fullPath, name)
			if _, err := os.Stat(indexPath); err == nil {
				s.serveMarkdown(w, indexPath)
				return
			}
		}
		// Fallback to directory listing
		s.serveDirectoryListing(w, fullPath, r.URL.Path)
		return
	}

	if strings.HasSuffix(strings.ToLower(fullPath), ".md") {
		s.serveMarkdown(w, fullPath)
		return
	}

	if s.OnlyMD {
		http.NotFound(w, r)
		return
	}

	// Serve other files directly
	http.ServeFile(w, r, fullPath)
}

func (s *Server) serveMarkdown(w http.ResponseWriter, path string) {
	f, err := os.Open(path)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	defer f.Close()

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	if err := s.Converter.Convert(f, w); err != nil {
		// If we already started writing, this might not work perfectly, 
		// but Convert writes its own headers/start tags anyway.
		fmt.Fprintf(os.Stderr, "Conversion error: %v\n", err)
	}
}

func (s *Server) serveDirectoryListing(w http.ResponseWriter, fullPath, urlPath string) {
	entries, err := os.ReadDir(fullPath)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	fmt.Fprintf(w, `<html>
<head>
    <style>
        body { font-family: sans-serif; padding: 2em; line-height: 1.5; max-width: 800px; margin: auto; }
        ul { list-style: none; padding: 0; }
        li { border-bottom: 1px solid #eee; padding: 0.5em 0; }
        a { text-decoration: none; color: #0366d6; }
        a:hover { text-decoration: underline; }
        .dir { font-weight: bold; }
    </style>
</head>
<body>
<h1>Index of %s</h1>
<ul>`, urlPath)

	if urlPath != "/" {
		fmt.Fprintf(w, "<li><a href=\"..\">..</a></li>")
	}

	for _, entry := range entries {
		name := entry.Name()
		class := ""
		if entry.IsDir() {
			name += "/"
			class = "class=\"dir\""
		} else if s.OnlyMD && !strings.HasSuffix(strings.ToLower(name), ".md") {
			continue
		}
		fmt.Fprintf(w, "<li><a href=\"%s\" %s>%s</a></li>", name, class, name)
	}
	fmt.Fprintf(w, "</ul></body></html>")
}
