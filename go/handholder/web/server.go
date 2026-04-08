// Package web provides a web interface for managing HandHolder workspaces.
package web

import (
	"context"
	"crypto/rand"
	"embed"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"html/template"
	"log/slog"
	"net"
	"net/http"
	"sort"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/matir/hacks/go/handholder/config"
	"github.com/matir/hacks/go/handholder/docker"
)

//go:embed templates/*
var templates embed.FS

type contextKey string

const loggerKey contextKey = "logger"

// Server represents the HandHolder web server.
type Server struct {
	cfg      *config.Config
	docker   docker.DockerManager
	status   map[int]string
	mu       sync.Mutex
	locks    map[int]*sync.Mutex
	locksMu  sync.Mutex
	template *template.Template
}

// NewServer creates a new web server instance with the given configuration and Docker manager.
func NewServer(cfg *config.Config, docker docker.DockerManager) *Server {
	tmpl := template.Must(template.ParseFS(templates, "templates/index.html"))
	return &Server{
		cfg:      cfg,
		docker:   docker,
		status:   make(map[int]string),
		locks:    make(map[int]*sync.Mutex),
		template: tmpl,
	}
}

// Start runs the HTTP server on the configured address and port.
func (s *Server) Start() error {
	mux := http.NewServeMux()
	mux.HandleFunc("/", s.handleIndex)
	mux.HandleFunc("/launch", s.handleLaunch)
	mux.HandleFunc("/stop", s.handleStop)
	mux.HandleFunc("/status", s.handleStatus)

	handler := s.withLogging(mux)

	addr := fmt.Sprintf("%s:%d", s.cfg.HandHolder.BindAddress, s.cfg.HandHolder.Port)
	slog.Info("Starting HandHolder", "addr", addr)
	return http.ListenAndServe(addr, handler)
}

func (s *Server) withLogging(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		logger := slog.Default()
		clientIP := s.getClientIP(r)

		if r.Method == http.MethodPost || r.URL.Path == "/launch" || r.URL.Path == "/stop" {
			id := make([]byte, 4)
			rand.Read(id)
			reqID := hex.EncodeToString(id)
			logger = logger.With("req_id", reqID, "client_ip", clientIP)
		}

		ctx := context.WithValue(r.Context(), loggerKey, logger)
		next.ServeHTTP(w, r.WithContext(ctx))
	})
}

func (s *Server) getClientIP(r *http.Request) string {
	remoteHost, _, err := net.SplitHostPort(r.RemoteAddr)
	if err != nil {
		remoteHost = r.RemoteAddr
	}

	if !s.isTrustedProxy(remoteHost) {
		return remoteHost
	}

	// Try X-Forwarded-For
	if xff := r.Header.Get("X-Forwarded-For"); xff != "" {
		ips := strings.Split(xff, ",")
		// Work backwards from the last IP in the chain
		for i := len(ips) - 1; i >= 0; i-- {
			ip := strings.TrimSpace(ips[i])
			if !s.isTrustedProxy(ip) {
				return ip
			}
		}
		// If all IPs are trusted, return the first one
		return strings.TrimSpace(ips[0])
	}

	// Try Forwarded (very basic support)
	if forwarded := r.Header.Get("Forwarded"); forwarded != "" {
		parts := strings.Split(forwarded, ";")
		for _, part := range parts {
			part = strings.TrimSpace(part)
			if strings.HasPrefix(strings.ToLower(part), "for=") {
				ip := strings.TrimPrefix(part[4:], "\"")
				ip = strings.TrimSuffix(ip, "\"")
				return ip
			}
		}
	}

	return remoteHost
}

func (s *Server) isTrustedProxy(ipStr string) bool {
	ip := net.ParseIP(ipStr)
	if ip == nil {
		return false
	}

	for _, proxy := range s.cfg.HandHolder.TrustedProxies {
		// Try as literal IP
		if proxy == ipStr {
			return true
		}
		// Try as CIDR
		if _, ipnet, err := net.ParseCIDR(proxy); err == nil {
			if ipnet.Contains(ip) {
				return true
			}
		}
	}
	return false
}

func getLogger(ctx context.Context) *slog.Logger {
	if logger, ok := ctx.Value(loggerKey).(*slog.Logger); ok {
		return logger
	}
	return slog.Default()
}

func (s *Server) getLock(port int) *sync.Mutex {
	s.locksMu.Lock()
	defer s.locksMu.Unlock()
	if _, ok := s.locks[port]; !ok {
		s.locks[port] = &sync.Mutex{}
	}
	return s.locks[port]
}

// handleIndex serves the main page listing all workspaces.
func (s *Server) handleIndex(w http.ResponseWriter, r *http.Request) {
	type workspaceView struct {
		ID        string
		Name      string
		Port      int
		Workspace string
		Status    string
		Active    bool
	}

	var workspaces []workspaceView
	for id, ws := range s.cfg.Workspaces {
		port := ws.Port
		if port == 0 {
			port = s.cfg.Defaults.Port
		}

		state, activeWorkspace, err := s.docker.GetContainerStatus(r.Context(), port)
		if err != nil {
			slog.Error("Error getting container status", "error", err, "port", port, "workspace_id", id)
		}

		workspaces = append(workspaces, workspaceView{
			ID:        id,
			Name:      ws.Name,
			Port:      port,
			Workspace: ws.Workspace,
			Status:    state,
			Active:    activeWorkspace == id,
		})
	}

	sort.Slice(workspaces, func(i, j int) bool {
		return workspaces[i].Name < workspaces[j].Name
	})

	s.template.Execute(w, workspaces)
}

// handleLaunch initiates the launch of a specific workspace.
func (s *Server) handleLaunch(w http.ResponseWriter, r *http.Request) {
	id := r.URL.Query().Get("id")
	logger := getLogger(r.Context()).With("workspace_id", id)

	ws, ok := s.cfg.Workspaces[id]
	if !ok {
		logger.Warn("Workspace not found")
		http.Error(w, "workspace not found", http.StatusNotFound)
		return
	}

	port := ws.Port
	if port == 0 {
		port = s.cfg.Defaults.Port
	}
	logger = logger.With("port", port)

	s.mu.Lock()
	defer s.mu.Unlock()
	s.status[port] = "Starting..."

	logger.Info("Attempting to launch workspace")

	go func() {
		// Create a new context for the background goroutine, but keep the logger
		ctx := context.WithValue(context.Background(), loggerKey, logger)

		// Acquire per-port lock
		lock := s.getLock(port)
		lock.Lock()
		defer lock.Unlock()

		s.updateStatus(ctx, port, "Stopping existing container...")
		if err := s.docker.StopContainerByPort(ctx, port); err != nil {
			s.updateStatus(ctx, port, fmt.Sprintf("Error stopping: %v", err))
			return
		}

		image := ws.Image
		if image == "" {
			image = s.cfg.Defaults.Image
		}

		s.updateStatus(ctx, port, fmt.Sprintf("Ensuring image %s...", image))
		if err := s.docker.EnsureImage(ctx, image); err != nil {
			s.updateStatus(ctx, port, fmt.Sprintf("Error pulling image: %v", err))
			return
		}

		env, err := ws.ResolveEnv(s.cfg.Defaults)
		if err != nil {
			s.updateStatus(ctx, port, fmt.Sprintf("Error resolving env: %v", err))
			return
		}

		s.updateStatus(ctx, port, "Launching container...")
		if err := s.docker.StartContainer(ctx, id, port, ws.Workspace, image, env, s.cfg.HandHolder.DisableSocketMount); err != nil {
			s.updateStatus(ctx, port, fmt.Sprintf("Error starting: %v", err))
			return
		}

		s.updateStatus(ctx, port, "Running")
	}()

	w.WriteHeader(http.StatusAccepted)
}

// handleStop initiates the stop of a specific workspace container.
func (s *Server) handleStop(w http.ResponseWriter, r *http.Request) {
	id := r.URL.Query().Get("id")
	logger := getLogger(r.Context()).With("workspace_id", id)

	ws, ok := s.cfg.Workspaces[id]
	if !ok {
		logger.Warn("Workspace not found")
		http.Error(w, "workspace not found", http.StatusNotFound)
		return
	}

	port := ws.Port
	if port == 0 {
		port = s.cfg.Defaults.Port
	}
	logger = logger.With("port", port)

	s.updateStatus(r.Context(), port, "Stopping...")

	go func() {
		ctx := context.WithValue(context.Background(), loggerKey, logger)

		lock := s.getLock(port)
		lock.Lock()
		defer lock.Unlock()

		if err := s.docker.StopContainerByPort(ctx, port); err != nil {
			s.updateStatus(ctx, port, fmt.Sprintf("Error stopping: %v", err))
			return
		}

		s.updateStatus(ctx, port, "not running")
	}()

	w.WriteHeader(http.StatusAccepted)
}

// handleStatus returns the current startup or operational status of a workspace as JSON.
func (s *Server) handleStatus(w http.ResponseWriter, r *http.Request) {
	portStr := r.URL.Query().Get("port")
	port, err := strconv.Atoi(portStr)
	if err != nil {
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(map[string]string{"error": "invalid port"})
		return
	}

	var status string
	var ok bool
	func() {
		s.mu.Lock()
		defer s.mu.Unlock()
		status, ok = s.status[port]
	}()

	if !ok {
		state, _, _ := s.docker.GetContainerStatus(r.Context(), port)
		status = state
	}

	json.NewEncoder(w).Encode(map[string]string{"status": status})
}

// updateStatus updates the internal status map and logs the change.
// Stable statuses (Running, not running, or Error*) are cleared after 5 minutes to prevent memory growth.
func (s *Server) updateStatus(ctx context.Context, port int, msg string) {
	func() {
		s.mu.Lock()
		defer s.mu.Unlock()
		s.status[port] = msg
	}()
	getLogger(ctx).Info(msg, "port", port)

	// Clean up stable statuses after 5 minutes
	if msg == "Running" || msg == "not running" || strings.HasPrefix(msg, "Error") {
		time.AfterFunc(5*time.Minute, func() {
			s.mu.Lock()
			defer s.mu.Unlock()
			if s.status[port] == msg {
				delete(s.status, port)
			}
		})
	}
}
