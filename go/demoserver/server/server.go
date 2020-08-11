package server

import (
	"errors"
	"log"
	"net/http"
	"time"

	"github.com/matir/hacks/go/demoserver/modules"
	"github.com/matir/hacks/go/demoserver/words"
)

type DemoServer struct {
	modules map[string]modules.ServerModule
	server  *http.Server
	mux     *http.ServeMux
}

var (
	ErrorBadModulePrefix       = errors.New("Bad module prefix")
	ErrorDuplicateModulePrefix = errors.New("Duplicate module prefix")
)

func NewDemoServer(listenAddr string) *DemoServer {
	s := &DemoServer{
		server: &http.Server{
			Addr:         listenAddr,
			ReadTimeout:  30 * time.Second,
			WriteTimeout: 30 * time.Second,
		},
		mux:     http.NewServeMux(),
		modules: make(map[string]modules.ServerModule),
	}
	s.server.Handler = s
	return s
}

// Handle HTTP Requests
func (ds *DemoServer) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	log.Printf("Request: %s", r.URL)
	ds.mux.ServeHTTP(w, r)
}

// Register a module under a path
func (ds *DemoServer) RegisterModule(sm modules.ServerModule) error {
	prefix := sm.Prefix()
	if sm.RandomPrefix() {
		prefix = words.DirectoryRandomChooser()
		prefix += "/"
	}
	prefix = "/" + prefix
	if _, exists := ds.modules[prefix]; exists {
		log.Printf("Duplicate module for prefix %s: %s", prefix, sm)
		return ErrorDuplicateModulePrefix
	}
	log.Printf("Registering module %s with prefix %s", sm, prefix)
	ds.modules[prefix] = sm
	ds.mux.Handle(prefix, sm)
	return nil
}

// Close to shutdown
func (ds *DemoServer) Close() error {
	return ds.server.Close()
}

// Listen and serve same as HTTP
func (ds *DemoServer) ListenAndServe() error {
	log.Printf("Starting DemoServer on %s", ds.server.Addr)
	return ds.server.ListenAndServe()
}
