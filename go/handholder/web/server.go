// Package web provides a web interface for managing HandHolder workspaces.
package web

import (
	"context"
	"embed"
	"encoding/json"
	"fmt"
	"html/template"
	"log"
	"net/http"
	"sort"
	"strconv"
	"sync"

	"github.com/matir/hacks/go/handholder/config"
	"github.com/matir/hacks/go/handholder/docker"
)

//go:embed templates/*
var templates embed.FS

// Server represents the HandHolder web server.
type Server struct {
	cfg     *config.Config
	docker  docker.DockerManager
	status  map[int]string
	mu      sync.Mutex
}

// NewServer creates a new web server instance with the given configuration and Docker manager.
func NewServer(cfg *config.Config, docker docker.DockerManager) *Server {
	return &Server{
		cfg:    cfg,
		docker: docker,
		status: make(map[int]string),
	}
}

// Start runs the HTTP server on the configured port.
func (s *Server) Start() error {
	mux := http.NewServeMux()
	mux.HandleFunc("/", s.handleIndex)
	mux.HandleFunc("/launch", s.handleLaunch)
	mux.HandleFunc("/status", s.handleStatus)

	addr := fmt.Sprintf(":%d", s.cfg.HandHolder.Port)
	log.Printf("Starting HandHolder on %s", addr)
	return http.ListenAndServe(addr, mux)
}

// handleIndex serves the main page listing all workspaces.
func (s *Server) handleIndex(w http.ResponseWriter, r *http.Request) {
	tmpl, err := template.ParseFS(templates, "templates/index.html")
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	type workspaceView struct {
		ID      string
		Name    string
		Port    int
		Status  string
		Active  bool
	}

	var workspaces []workspaceView
	for id, ws := range s.cfg.Workspaces {
		port := ws.Port
		if port == 0 {
			port = s.cfg.Defaults.Port
		}
		
		state, activeWorkspace, _ := s.docker.GetContainerStatus(r.Context(), port)
		
		workspaces = append(workspaces, workspaceView{
			ID:     id,
			Name:   ws.Name,
			Port:   port,
			Status: state,
			Active: activeWorkspace == id,
		})
	}

	sort.Slice(workspaces, func(i, j int) bool {
		return workspaces[i].Name < workspaces[j].Name
	})

	tmpl.Execute(w, workspaces)
}

// handleLaunch initiates the launch of a specific workspace.
// It returns immediately with StatusAccepted (202), while the launch process continues in a goroutine.
func (s *Server) handleLaunch(w http.ResponseWriter, r *http.Request) {
	id := r.URL.Query().Get("id")
	ws, ok := s.cfg.Workspaces[id]
	if !ok {
		http.Error(w, "workspace not found", http.StatusNotFound)
		return
	}

	port := ws.Port
	if port == 0 {
		port = s.cfg.Defaults.Port
	}

	s.mu.Lock()
	s.status[port] = "Starting..."
	s.mu.Unlock()

	go func() {
		ctx := context.Background()
		
		s.updateStatus(port, "Stopping existing container...")
		if err := s.docker.StopContainerByPort(ctx, port); err != nil {
			s.updateStatus(port, fmt.Sprintf("Error stopping: %v", err))
			return
		}

		image := ws.Image
		if image == "" {
			image = s.cfg.Defaults.Image
		}

		s.updateStatus(port, fmt.Sprintf("Ensuring image %s...", image))
		if err := s.docker.EnsureImage(ctx, image); err != nil {
			s.updateStatus(port, fmt.Sprintf("Error pulling image: %v", err))
			return
		}

		env, err := ws.ResolveEnv(s.cfg.Defaults)
		if err != nil {
			s.updateStatus(port, fmt.Sprintf("Error resolving env: %v", err))
			return
		}

		s.updateStatus(port, "Launching container...")
		if err := s.docker.StartContainer(ctx, id, port, ws.Workspace, image, env); err != nil {
			s.updateStatus(port, fmt.Sprintf("Error starting: %v", err))
			return
		}

		s.updateStatus(port, "Running")
	}()

	w.WriteHeader(http.StatusAccepted)
}

// handleStatus returns the current startup or operational status of a workspace as JSON.
func (s *Server) handleStatus(w http.ResponseWriter, r *http.Request) {
	portStr := r.URL.Query().Get("port")
	port, _ := strconv.Atoi(portStr)

	s.mu.Lock()
	status, ok := s.status[port]
	s.mu.Unlock()

	if !ok {
		state, _, _ := s.docker.GetContainerStatus(r.Context(), port)
		status = state
	}

	json.NewEncoder(w).Encode(map[string]string{"status": status})
}

// updateStatus updates the internal status map and logs the change.
func (s *Server) updateStatus(port int, msg string) {
	s.mu.Lock()
	s.status[port] = msg
	s.mu.Unlock()
	log.Printf("Port %d: %s", port, msg)
}
