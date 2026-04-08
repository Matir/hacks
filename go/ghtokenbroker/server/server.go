package server

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"net"
	"net/http"
	"os"
	"strings"
	"sync"
	"time"

	"github.com/matir/hacks/go/ghtokenbroker/audit"
	githubclient "github.com/matir/hacks/go/ghtokenbroker/github"
	"github.com/matir/hacks/go/ghtokenbroker/policy"
)

// TokenRequest is the JSON body of POST /v1/token.
type TokenRequest struct {
	Repo                 string            `json:"repo"`
	RequestedPermissions map[string]string `json:"requested_permissions"`
	TaskID               string            `json:"task_id"`
	Purpose              string            `json:"purpose"`
}

// TokenResponse is the JSON body returned on success.
type TokenResponse struct {
	Token              string            `json:"token"`
	ExpiresAt          time.Time         `json:"expires_at"`
	Repo               string            `json:"repo"`
	GrantedPermissions map[string]string `json:"granted_permissions"`
}

// errorResponse is the JSON body returned on failure.
type errorResponse struct {
	Error string `json:"error"`
}

// Server handles HTTP requests.
type Server struct {
	policy *policy.Engine
	github *githubclient.Client
	audit  *audit.Logger
	mux    *http.ServeMux
}

// ServeHTTP implements http.Handler by delegating to the internal mux.
func (s *Server) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	s.mux.ServeHTTP(w, r)
}

// New creates a Server wired up with the given components.
func New(pol *policy.Engine, ghc *githubclient.Client, auditor *audit.Logger) *Server {
	s := &Server{
		policy: pol,
		github: ghc,
		audit:  auditor,
		mux:    http.NewServeMux(),
	}
	s.mux.HandleFunc("POST /v1/token", s.handleToken)
	s.mux.HandleFunc("GET /healthz", s.handleHealth)
	return s
}

// ListenAndServe starts listeners on the configured addresses and blocks until
// all listeners have stopped. At least one address must be non-empty.
func (s *Server) ListenAndServe(ctx context.Context, tcpAddr, unixSocket string) error {
	if tcpAddr == "" && unixSocket == "" {
		return errors.New("server: at least one of tcp_addr or unix_socket must be configured")
	}

	srv := &http.Server{
		Handler:      s.mux,
		ReadTimeout:  30 * time.Second,
		WriteTimeout: 30 * time.Second,
		IdleTimeout:  60 * time.Second,
	}

	var listeners []net.Listener

	if tcpAddr != "" {
		ln, err := net.Listen("tcp", tcpAddr)
		if err != nil {
			return fmt.Errorf("server: listen tcp %s: %w", tcpAddr, err)
		}
		listeners = append(listeners, ln)
	}

	if unixSocket != "" {
		// Remove a stale socket file if present.
		_ = os.Remove(unixSocket)
		ln, err := net.Listen("unix", unixSocket)
		if err != nil {
			for _, l := range listeners {
				l.Close()
			}
			return fmt.Errorf("server: listen unix %s: %w", unixSocket, err)
		}
		listeners = append(listeners, ln)
	}

	var wg sync.WaitGroup
	errs := make(chan error, len(listeners))

	for _, ln := range listeners {
		wg.Add(1)
		go func(l net.Listener) {
			defer wg.Done()
			if err := srv.Serve(l); err != nil && !errors.Is(err, http.ErrServerClosed) {
				errs <- err
			}
		}(ln)
	}

	// Wait for context cancellation then shut down gracefully.
	<-ctx.Done()
	shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	if err := srv.Shutdown(shutdownCtx); err != nil {
		log.Printf("server: shutdown error: %v", err)
	}

	wg.Wait()
	close(errs)

	for err := range errs {
		return err
	}
	return nil
}

func (s *Server) handleHealth(w http.ResponseWriter, _ *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	_, _ = w.Write([]byte(`{"status":"ok"}` + "\n"))
}

func (s *Server) handleToken(w http.ResponseWriter, r *http.Request) {
	corrID := r.Header.Get("X-Request-ID")
	if corrID == "" {
		corrID = newCorrelationID()
	}
	w.Header().Set("X-Request-ID", corrID)
	w.Header().Set("Content-Type", "application/json")

	// --- Authentication ---
	apiKey, err := bearerToken(r)
	if err != nil {
		s.deny(w, r, corrID, "", "", nil, http.StatusUnauthorized, err.Error())
		return
	}

	agent, err := s.policy.Authenticate(apiKey)
	if err != nil {
		s.deny(w, r, corrID, "", "", nil, http.StatusUnauthorized, "invalid credentials")
		return
	}

	// --- Parse request body ---
	var req TokenRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		s.deny(w, r, corrID, agent.ID, "", nil, http.StatusBadRequest, "invalid request body")
		return
	}

	if req.Repo == "" {
		s.deny(w, r, corrID, agent.ID, "", req.RequestedPermissions, http.StatusBadRequest, "repo is required")
		return
	}

	if len(req.RequestedPermissions) == 0 {
		s.deny(w, r, corrID, agent.ID, req.Repo, nil, http.StatusBadRequest, "requested_permissions is required")
		return
	}

	// --- Authorisation ---
	granted, err := s.policy.Authorize(agent, req.Repo, req.RequestedPermissions)
	if err != nil {
		s.deny(w, r, corrID, agent.ID, req.Repo, req.RequestedPermissions, http.StatusForbidden, err.Error())
		return
	}

	// --- Resolve repository ---
	owner, repoName, err := githubclient.SplitRepo(req.Repo)
	if err != nil {
		s.deny(w, r, corrID, agent.ID, req.Repo, req.RequestedPermissions, http.StatusBadRequest, "invalid repo format")
		return
	}

	installID, err := s.github.GetInstallationID(r.Context(), owner, repoName)
	if err != nil {
		s.deny(w, r, corrID, agent.ID, req.Repo, req.RequestedPermissions, http.StatusServiceUnavailable, "could not resolve repository installation")
		return
	}

	// --- Mint token ---
	token, err := s.github.MintToken(r.Context(), installID, owner, repoName, granted)
	if err != nil {
		s.deny(w, r, corrID, agent.ID, req.Repo, req.RequestedPermissions, http.StatusServiceUnavailable, "could not mint installation token")
		return
	}

	// --- Audit allow ---
	_ = s.audit.Log(audit.Event{
		CorrelationID:        corrID,
		CallerID:             agent.ID,
		Repo:                 req.Repo,
		TaskID:               req.TaskID,
		Purpose:              req.Purpose,
		RequestedPermissions: req.RequestedPermissions,
		GrantedPermissions:   granted,
		Decision:             audit.DecisionAllow,
	})

	resp := TokenResponse{
		Token:              token.GetToken(),
		ExpiresAt:          token.GetExpiresAt().Time,
		Repo:               req.Repo,
		GrantedPermissions: granted,
	}
	w.WriteHeader(http.StatusOK)
	_ = json.NewEncoder(w).Encode(resp)
}

func (s *Server) deny(w http.ResponseWriter, _ *http.Request, corrID, callerID, repo string, requested map[string]string, status int, reason string) {
	_ = s.audit.Log(audit.Event{
		CorrelationID:        corrID,
		CallerID:             callerID,
		Repo:                 repo,
		RequestedPermissions: requested,
		Decision:             audit.DecisionDeny,
		Reason:               reason,
	})
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(errorResponse{Error: reason})
}

// bearerToken extracts the token from an "Authorization: Bearer <token>" header.
func bearerToken(r *http.Request) (string, error) {
	header := r.Header.Get("Authorization")
	if header == "" {
		return "", errors.New("missing Authorization header")
	}
	const prefix = "Bearer "
	if !strings.HasPrefix(header, prefix) {
		return "", errors.New("Authorization header must use Bearer scheme")
	}
	token := strings.TrimPrefix(header, prefix)
	if token == "" {
		return "", errors.New("bearer token must not be empty")
	}
	return token, nil
}

func newCorrelationID() string {
	b := make([]byte, 16)
	if _, err := rand.Read(b); err != nil {
		return fmt.Sprintf("ts-%d", time.Now().UnixNano())
	}
	return hex.EncodeToString(b)
}
