package web

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
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

	// Test case: Launch Alpha
	req := httptest.NewRequest("GET", "/launch?id=alpha", nil)
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

	// Test case: Invalid ID (404)
	req2 := httptest.NewRequest("GET", "/launch?id=nonexistent", nil)
	rr2 := httptest.NewRecorder()
	server.handleLaunch(rr2, req2)
	if rr2.Code != http.StatusNotFound {
		t.Errorf("expected 404 for invalid workspace, got %d", rr2.Code)
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
	fake.StartContainer(nil, "alpha", 3000, "/tmp/alpha", "image", nil)

	req := httptest.NewRequest("GET", "/stop?id=alpha", nil)
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
	req1 := httptest.NewRequest("GET", "/launch?id=alpha", nil)
	rr1 := httptest.NewRecorder()
	server.handleLaunch(rr1, req1)

	// Trigger second launch immediately
	req2 := httptest.NewRequest("GET", "/launch?id=alpha", nil)
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

	// Test GET (no req_id expected in context normally, but logger should be present)
	req := httptest.NewRequest("GET", "/", nil)
	rr := httptest.NewRecorder()
	handler.ServeHTTP(rr, req)
	if rr.Code != http.StatusOK {
		t.Errorf("expected 200, got %d", rr.Code)
	}

	// Test /launch (req_id expected)
	req = httptest.NewRequest("GET", "/launch?id=alpha", nil)
	rr = httptest.NewRecorder()
	handler.ServeHTTP(rr, req)
}
