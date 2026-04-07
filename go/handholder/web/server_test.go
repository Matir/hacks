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
}

func TestHandleStatus(t *testing.T) {
	cfg := &config.Config{}
	fake := docker_mock.NewFakeManager()
	server := NewServer(cfg, fake)

	// Pre-set status in memory
	server.mu.Lock()
	server.status[3000] = "Starting..."
	server.mu.Unlock()

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
