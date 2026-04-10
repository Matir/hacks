package web

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/matir/hacks/go/handholder/config"
	docker_mock "github.com/matir/hacks/go/handholder/docker/mock"
)

func TestHandleIndex(t *testing.T) {
	cfg := &config.Config{
		Workspaces: map[string]config.WorkspaceConfig{
			"alpha": {Name: "Alpha", Workspace: "/tmp/alpha"},
		},
	}
	fake := docker_mock.NewFakeManager()
	server := NewServer(cfg, fake)

	req := httptest.NewRequest("GET", "/", nil)
	rr := httptest.NewRecorder()

	server.handleIndex(rr, req)

	if status := rr.Code; status != http.StatusOK {
		t.Errorf("handler returned wrong status code: got %v want %v", status, http.StatusOK)
	}

	if rr.Body.String() == "" {
		t.Error("handler returned empty body")
	}
}

func TestHandleLaunch(t *testing.T) {
	cfg := &config.Config{
		Defaults: config.WorkspaceConfig{Port: 3000},
		Workspaces: map[string]config.WorkspaceConfig{
			"alpha": {Name: "Alpha", Workspace: "/tmp/alpha"},
		},
	}
	fake := docker_mock.NewFakeManager()
	server := NewServer(cfg, fake)

	// Test case: Launch Alpha (method check only; CSRF is enforced by middleware)
	req := httptest.NewRequest("POST", "/launch?id=alpha", nil)
	rr := httptest.NewRecorder()

	server.handleLaunch(rr, req)

	if status := rr.Code; status != http.StatusAccepted {
		t.Errorf("handler returned wrong status code: got %v want %v", status, http.StatusAccepted)
	}

	// Give the goroutine a moment to run
	time.Sleep(100 * time.Millisecond)

	state, name, _ := fake.GetContainerStatus(nil, 3000)
	if name != "alpha" {
		t.Errorf("expected alpha to be running, got %s (state: %s)", name, state)
	}

	// Test case: Wrong method (405)
	req2 := httptest.NewRequest("GET", "/launch?id=alpha", nil)
	rr2 := httptest.NewRecorder()
	server.handleLaunch(rr2, req2)
	if rr2.Code != http.StatusMethodNotAllowed {
		t.Errorf("expected 405 for GET, got %d", rr2.Code)
	}

	// Test case: Invalid ID (404)
	req3 := httptest.NewRequest("POST", "/launch?id=nonexistent", nil)
	rr3 := httptest.NewRecorder()
	server.handleLaunch(rr3, req3)
	if rr3.Code != http.StatusNotFound {
		t.Errorf("expected 404 for invalid workspace, got %d", rr3.Code)
	}
}

func TestHandleStatus(t *testing.T) {
	cfg := &config.Config{}
	fake := docker_mock.NewFakeManager()
	server := NewServer(cfg, fake)

	// Pre-set status in memory
	func() {
		server.mu.Lock()
		defer server.mu.Unlock()
		server.status[3000] = "Starting..."
	}()

	req := httptest.NewRequest("GET", "/status?port=3000", nil)
	rr := httptest.NewRecorder()

	server.handleStatus(rr, req)

	if status := rr.Code; status != http.StatusOK {
		t.Errorf("handler returned wrong status code: got %v want %v", status, http.StatusOK)
	}

	var data map[string]string
	if err := json.NewDecoder(rr.Body).Decode(&data); err != nil {
		t.Fatalf("failed to decode response: %v", err)
	}

	if data["status"] != "Starting..." {
		t.Errorf("expected status 'Starting...', got %s", data["status"])
	}

	// Case: Invalid port
	req2 := httptest.NewRequest("GET", "/status?port=abc", nil)
	rr2 := httptest.NewRecorder()
	server.handleStatus(rr2, req2)
	if rr2.Code != http.StatusBadRequest {
		t.Errorf("expected 400 for invalid port, got %d", rr2.Code)
	}
}

func TestHandleStop(t *testing.T) {
	cfg := &config.Config{
		Defaults: config.WorkspaceConfig{Port: 3000},
		Workspaces: map[string]config.WorkspaceConfig{
			"alpha": {Name: "Alpha", Workspace: "/tmp/alpha"},
		},
	}
	fake := docker_mock.NewFakeManager()
	server := NewServer(cfg, fake)

	// Pre-start the container
	fake.StartContainer(nil, "alpha", 3000, "/tmp/alpha", "image", nil, false)

	req := httptest.NewRequest("POST", "/stop?id=alpha", nil)
	rr := httptest.NewRecorder()

	server.handleStop(rr, req)

	if status := rr.Code; status != http.StatusAccepted {
		t.Errorf("handler returned wrong status code: got %v want %v", status, http.StatusAccepted)
	}

	// Give the goroutine a moment to run
	time.Sleep(100 * time.Millisecond)

	state, _, _ := fake.GetContainerStatus(nil, 3000)
	if state != "not running" {
		t.Errorf("expected alpha to be stopped, got state %s", state)
	}

	// Test case: Wrong method (405)
	req2 := httptest.NewRequest("GET", "/stop?id=alpha", nil)
	rr2 := httptest.NewRecorder()
	server.handleStop(rr2, req2)
	if rr2.Code != http.StatusMethodNotAllowed {
		t.Errorf("expected 405 for GET, got %d", rr2.Code)
	}
}

func TestCSRFMiddleware(t *testing.T) {
	server := NewServer(&config.Config{}, nil)
	token := server.csrfToken

	sentinel := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	})
	handler := server.withCSRF(sentinel)

	tests := []struct {
		name       string
		method     string
		csrfHeader string
		wantStatus int
	}{
		{"GET passes without token", http.MethodGet, "", http.StatusOK},
		{"HEAD passes without token", http.MethodHead, "", http.StatusOK},
		{"POST with valid token passes", http.MethodPost, token, http.StatusOK},
		{"POST without token rejected", http.MethodPost, "", http.StatusForbidden},
		{"POST with wrong token rejected", http.MethodPost, "wrong-token", http.StatusForbidden},
		{"PUT with valid token passes", http.MethodPut, token, http.StatusOK},
		{"PUT without token rejected", http.MethodPut, "", http.StatusForbidden},
		{"DELETE with valid token passes", http.MethodDelete, token, http.StatusOK},
		{"DELETE without token rejected", http.MethodDelete, "", http.StatusForbidden},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			req := httptest.NewRequest(tt.method, "/", nil)
			if tt.csrfHeader != "" {
				req.Header.Set("X-CSRF-Token", tt.csrfHeader)
			}
			rr := httptest.NewRecorder()
			handler.ServeHTTP(rr, req)
			if rr.Code != tt.wantStatus {
				t.Errorf("got %d, want %d", rr.Code, tt.wantStatus)
			}
		})
	}
}

func TestCSRFMiddlewareIntegration(t *testing.T) {
	cfg := &config.Config{
		Defaults: config.WorkspaceConfig{Port: 3000},
		Workspaces: map[string]config.WorkspaceConfig{
			"alpha": {Name: "Alpha", Workspace: "/tmp/alpha"},
		},
	}
	fake := docker_mock.NewFakeManager()
	server := NewServer(cfg, fake)
	token := server.csrfToken

	// Build the same mux that Start() would use
	mux := http.NewServeMux()
	mux.HandleFunc("/", server.handleIndex)
	mux.HandleFunc("/launch", server.handleLaunch)
	mux.HandleFunc("/stop", server.handleStop)
	mux.HandleFunc("/status", server.handleStatus)
	handler := server.withCSRF(mux)

	tests := []struct {
		name       string
		method     string
		path       string
		csrfHeader string
		wantStatus int
	}{
		{"GET index allowed", http.MethodGet, "/", "", http.StatusOK},
		{"GET status allowed", http.MethodGet, "/status?port=3000", "", http.StatusOK},
		{"POST launch with token allowed", http.MethodPost, "/launch?id=alpha", token, http.StatusAccepted},
		{"POST launch without token rejected", http.MethodPost, "/launch?id=alpha", "", http.StatusForbidden},
		{"POST launch with wrong token rejected", http.MethodPost, "/launch?id=alpha", "bad", http.StatusForbidden},
		{"POST stop with token allowed", http.MethodPost, "/stop?id=alpha", token, http.StatusAccepted},
		{"POST stop without token rejected", http.MethodPost, "/stop?id=alpha", "", http.StatusForbidden},
		{"GET launch rejected by handler (405)", http.MethodGet, "/launch?id=alpha", "", http.StatusMethodNotAllowed},
		{"GET stop rejected by handler (405)", http.MethodGet, "/stop?id=alpha", "", http.StatusMethodNotAllowed},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			req := httptest.NewRequest(tt.method, tt.path, nil)
			if tt.csrfHeader != "" {
				req.Header.Set("X-CSRF-Token", tt.csrfHeader)
			}
			rr := httptest.NewRecorder()
			handler.ServeHTTP(rr, req)
			if rr.Code != tt.wantStatus {
				t.Errorf("got %d, want %d", rr.Code, tt.wantStatus)
			}
		})
	}
}

func TestGetClientIP(t *testing.T) {
	cfg := &config.Config{
		HandHolder: config.HandHolderConfig{
			TrustedProxies: []string{"10.0.0.1", "192.168.1.0/24"},
		},
	}
	server := NewServer(cfg, nil)

	tests := []struct {
		name       string
		remoteAddr string
		headers    map[string]string
		expected   string
	}{
		{
			"Direct, untrusted",
			"1.2.3.4:1234",
			nil,
			"1.2.3.4",
		},
		{
			"Trusted proxy, single XFF",
			"10.0.0.1:1234",
			map[string]string{"X-Forwarded-For": "5.6.7.8"},
			"5.6.7.8",
		},
		{
			"Trusted proxy, chained XFF",
			"10.0.0.1:1234",
			map[string]string{"X-Forwarded-For": "5.6.7.8, 10.0.0.5"}, // 10.0.0.5 is not trusted by default except by CIDR if added
			"10.0.0.5",
		},
		{
			"Trusted proxy chain",
			"10.0.0.1:1234",
			map[string]string{"X-Forwarded-For": "5.6.7.8, 192.168.1.50, 10.0.0.1"},
			"5.6.7.8",
		},
		{
			"Untrusted proxy, ignored XFF",
			"1.1.1.1:1234",
			map[string]string{"X-Forwarded-For": "5.6.7.8"},
			"1.1.1.1",
		},
		{
			"All proxies trusted in XFF",
			"10.0.0.1:1234",
			map[string]string{"X-Forwarded-For": "10.0.0.5, 10.0.0.1"},
			"10.0.0.5",
		},
		{
			"Forwarded header support",
			"10.0.0.1:1234",
			map[string]string{"Forwarded": "for=9.9.9.9;proto=https"},
			"9.9.9.9",
		},
		{
			"Forwarded header with quotes",
			"10.0.0.1:1234",
			map[string]string{"Forwarded": "for=\"[2001:db8:cafe::17]:4711\""},
			"[2001:db8:cafe::17]:4711",
		},
		{
			"Forwarded header case insensitive",
			"10.0.0.1:1234",
			map[string]string{"Forwarded": "FOR=8.8.8.8"},
			"8.8.8.8",
		},
		{
			"SplitHostPort failure handles raw IP",
			"1.2.3.4",
			nil,
			"1.2.3.4",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			req := httptest.NewRequest("GET", "/", nil)
			req.RemoteAddr = tt.remoteAddr
			for k, v := range tt.headers {
				req.Header.Set(k, v)
			}
			if ip := server.getClientIP(req); ip != tt.expected {
				t.Errorf("expected %s, got %s", tt.expected, ip)
			}
		})
	}
}

func TestPerPortLocking(t *testing.T) {
	cfg := &config.Config{
		Defaults: config.WorkspaceConfig{Port: 3000},
		Workspaces: map[string]config.WorkspaceConfig{
			"alpha": {Name: "Alpha", Workspace: "/tmp/alpha"},
		},
	}

	// Create a manager that takes time to stop a container
	fake := docker_mock.NewFakeManager()
	fake.StopDelay = 200 * time.Millisecond

	server := NewServer(cfg, fake)

	// Trigger first launch
	req1 := httptest.NewRequest("POST", "/launch?id=alpha", nil)
	rr1 := httptest.NewRecorder()
	server.handleLaunch(rr1, req1)

	// Trigger second launch immediately
	req2 := httptest.NewRequest("POST", "/launch?id=alpha", nil)
	rr2 := httptest.NewRecorder()
	server.handleLaunch(rr2, req2)

	// At this point, both requests are accepted, but one should be waiting for the other.
	// Since we can't easily peek into the internal state of the goroutines,
	// we'll check if the StopContainerByPort was called sequentially.
	// We'll give it some time to finish both.
	time.Sleep(600 * time.Millisecond)

	if fake.StopCount != 2 {
		t.Errorf("expected 2 stop calls, got %d", fake.StopCount)
	}
}

func TestGetRequestScheme(t *testing.T) {
	cfg := &config.Config{
		HandHolder: config.HandHolderConfig{
			TrustedProxies: []string{"10.0.0.1"},
		},
	}
	server := NewServer(cfg, nil)

	tests := []struct {
		name       string
		remoteAddr string
		proto      string
		want       string
	}{
		{"direct, no header", "1.2.3.4:1234", "", "http"},
		{"direct, header ignored", "1.2.3.4:1234", "https", "http"},
		{"trusted proxy, https", "10.0.0.1:1234", "https", "https"},
		{"trusted proxy, http", "10.0.0.1:1234", "http", "http"},
		{"trusted proxy, no header", "10.0.0.1:1234", "", "http"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			req := httptest.NewRequest("GET", "/", nil)
			req.RemoteAddr = tt.remoteAddr
			if tt.proto != "" {
				req.Header.Set("X-Forwarded-Proto", tt.proto)
			}
			if got := server.getRequestScheme(req); got != tt.want {
				t.Errorf("got %q, want %q", got, tt.want)
			}
		})
	}
}

func TestHandleIndexOpenURL(t *testing.T) {
	tests := []struct {
		name        string
		defaults    config.WorkspaceConfig
		workspace   config.WorkspaceConfig
		remoteAddr  string
		host        string
		proto       string
		trustedProxy string
		wantURL     string
	}{
		{
			name:      "direct request uses http and request host",
			workspace: config.WorkspaceConfig{Name: "Alpha", Workspace: "/tmp/alpha"},
			defaults:  config.WorkspaceConfig{Port: 3000},
			remoteAddr: "1.2.3.4:5000",
			host:      "myhost.example.com",
			wantURL:   "http://myhost.example.com:3000",
		},
		{
			name:      "host with port strips port",
			workspace: config.WorkspaceConfig{Name: "Alpha", Workspace: "/tmp/alpha"},
			defaults:  config.WorkspaceConfig{Port: 3000},
			remoteAddr: "1.2.3.4:5000",
			host:      "myhost.example.com:8080",
			wantURL:   "http://myhost.example.com:3000",
		},
		{
			name:         "trusted proxy https uses https scheme",
			workspace:    config.WorkspaceConfig{Name: "Alpha", Workspace: "/tmp/alpha"},
			defaults:     config.WorkspaceConfig{Port: 3000},
			remoteAddr:   "10.0.0.1:5000",
			host:         "myhost.example.com",
			proto:        "https",
			trustedProxy: "10.0.0.1",
			wantURL:      "https://myhost.example.com:3000",
		},
		{
			name:         "untrusted proxy header ignored",
			workspace:    config.WorkspaceConfig{Name: "Alpha", Workspace: "/tmp/alpha"},
			defaults:     config.WorkspaceConfig{Port: 3000},
			remoteAddr:   "1.2.3.4:5000",
			host:         "myhost.example.com",
			proto:        "https",
			wantURL:      "http://myhost.example.com:3000",
		},
		{
			name:      "workspace proxy_url overrides",
			workspace: config.WorkspaceConfig{Name: "Alpha", Workspace: "/tmp/alpha", ProxyURL: "https://proxy.example.com/alpha"},
			defaults:  config.WorkspaceConfig{Port: 3000},
			remoteAddr: "1.2.3.4:5000",
			host:      "myhost.example.com",
			wantURL:   "https://proxy.example.com/alpha",
		},
		{
			name:      "default proxy_url used when workspace has none",
			workspace: config.WorkspaceConfig{Name: "Alpha", Workspace: "/tmp/alpha"},
			defaults:  config.WorkspaceConfig{Port: 3000, ProxyURL: "https://default-proxy.example.com"},
			remoteAddr: "1.2.3.4:5000",
			host:      "myhost.example.com",
			wantURL:   "https://default-proxy.example.com",
		},
		{
			name:      "workspace proxy_url overrides default proxy_url",
			workspace: config.WorkspaceConfig{Name: "Alpha", Workspace: "/tmp/alpha", ProxyURL: "https://ws-proxy.example.com"},
			defaults:  config.WorkspaceConfig{Port: 3000, ProxyURL: "https://default-proxy.example.com"},
			remoteAddr: "1.2.3.4:5000",
			host:      "myhost.example.com",
			wantURL:   "https://ws-proxy.example.com",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			trusted := []string{}
			if tt.trustedProxy != "" {
				trusted = []string{tt.trustedProxy}
			}
			cfg := &config.Config{
				HandHolder: config.HandHolderConfig{TrustedProxies: trusted},
				Defaults:   tt.defaults,
				Workspaces: map[string]config.WorkspaceConfig{"alpha": tt.workspace},
			}
			server := NewServer(cfg, docker_mock.NewFakeManager())

			req := httptest.NewRequest("GET", "/", nil)
			req.RemoteAddr = tt.remoteAddr
			req.Host = tt.host
			if tt.proto != "" {
				req.Header.Set("X-Forwarded-Proto", tt.proto)
			}
			rr := httptest.NewRecorder()
			server.handleIndex(rr, req)

			if rr.Code != http.StatusOK {
				t.Fatalf("unexpected status %d", rr.Code)
			}
			if !strings.Contains(rr.Body.String(), `href="`+tt.wantURL+`"`) {
				t.Errorf("body does not contain href=%q\nbody: %s", tt.wantURL, rr.Body.String())
			}
		})
	}
}

func TestWithLogging(t *testing.T) {
	server := NewServer(&config.Config{}, nil)

	nextHandler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		logger := getLogger(r.Context())
		if logger == nil {
			t.Error("logger not found in context")
		}
		w.WriteHeader(http.StatusOK)
	})

	handler := server.withLogging(nextHandler)

	// Test GET (logger present but no req_id)
	req := httptest.NewRequest("GET", "/", nil)
	rr := httptest.NewRecorder()
	handler.ServeHTTP(rr, req)
	if rr.Code != http.StatusOK {
		t.Errorf("expected 200, got %d", rr.Code)
	}

	// Test POST (req_id injected into logger)
	req = httptest.NewRequest("POST", "/launch?id=alpha", nil)
	rr = httptest.NewRecorder()
	handler.ServeHTTP(rr, req)
	if rr.Code != http.StatusOK {
		t.Errorf("expected 200, got %d", rr.Code)
	}
}
