package docker

import (
	"context"
	"io"
	"log/slog"
	"testing"

	"github.com/docker/docker/api/types/container"
	docker_mock "github.com/matir/hacks/go/handholder/docker/mock"
)

func TestGetLogger(t *testing.T) {
	// Case: default logger
	l1 := getLogger(context.Background())
	if l1 != slog.Default() {
		t.Error("expected default logger")
	}

	// Case: logger in context
	custom := slog.New(slog.NewTextHandler(io.Discard, nil))
	ctx := context.WithValue(context.Background(), loggerKey, custom)
	l2 := getLogger(ctx)
	if l2 != custom {
		t.Error("expected custom logger from context")
	}
}

func TestNewManager(t *testing.T) {
	// Case: default
	mgr, err := NewManager("")
	if err != nil {
		t.Fatalf("NewManager failed: %v", err)
	}
	if mgr == nil {
		t.Fatal("NewManager returned nil")
	}

	// Case: custom socket
	mgr, err = NewManager("unix:///var/run/docker.sock")
	if err != nil {
		t.Fatalf("NewManager failed with socket: %v", err)
	}
	if mgr == nil {
		t.Fatal("NewManager returned nil")
	}
}

func TestEnsureImage(t *testing.T) {
	fake := docker_mock.NewFakeDockerClient()
	mgr := &Manager{cli: fake}
	ctx := context.Background()

	// Test case: Image doesn't exist, should pull it
	imgName := "test-image"
	if err := mgr.EnsureImage(ctx, imgName); err != nil {
		t.Fatalf("EnsureImage failed: %v", err)
	}

	if !fake.Images[imgName] {
		t.Error("Image was not marked as pulled in fake client")
	}

	// Test case: Image already exists, should not fail
	if err := mgr.EnsureImage(ctx, imgName); err != nil {
		t.Fatalf("EnsureImage failed on existing image: %v", err)
	}
}

func TestStartContainer(t *testing.T) {
	fake := docker_mock.NewFakeDockerClient()
	mgr := &Manager{cli: fake}
	ctx := context.Background()

	port := 8080
	workspace := "test-ws"
	hostPath := "/tmp/ws"
	img := "node:latest"
	env := map[string]string{"FOO": "BAR"}

	err := mgr.StartContainer(ctx, workspace, port, hostPath, img, env)
	if err != nil {
		t.Fatalf("StartContainer failed: %v", err)
	}

	// Verify container exists in fake
	name := "handholder-openhands-8080"
	cfg, ok := fake.Containers[name]
	if !ok {
		t.Fatalf("Container %s not found in fake client", name)
	}

	if cfg.Image != img {
		t.Errorf("Expected image %s, got %s", img, cfg.Image)
	}

	// Check labels
	if cfg.Labels["workspace"] != workspace {
		t.Errorf("Expected label workspace=%s, got %s", workspace, cfg.Labels["workspace"])
	}
}

func TestStopContainerByPort(t *testing.T) {
	fake := docker_mock.NewFakeDockerClient()
	mgr := &Manager{cli: fake}
	ctx := context.Background()

	port := 9000
	name := "handholder-openhands-9000"
	
	// Pre-create a container
	fake.Containers[name] = &container.Config{
		Labels: map[string]string{"managed-by": "handholder"},
	}

	if err := mgr.StopContainerByPort(ctx, port); err != nil {
		t.Fatalf("StopContainerByPort failed: %v", err)
	}

	if _, ok := fake.Containers[name]; ok {
		t.Error("Container was not removed from fake client")
	}
}

func TestStopContainerFail(t *testing.T) {
	fake := docker_mock.NewFakeDockerClient()
	mgr := &Manager{cli: fake}
	ctx := context.Background()

	port := 9001
	name := "handholder-openhands-9001"
	
	// Pre-create a container
	fake.Containers[name] = &container.Config{
		Labels: map[string]string{"managed-by": "handholder"},
	}
	// Make stop fail but remove succeed (to test force remove)
	fake.StopFails = true

	if err := mgr.StopContainerByPort(ctx, port); err != nil {
		t.Fatalf("StopContainerByPort should succeed even if Stop fails (due to force remove): %v", err)
	}

	if _, ok := fake.Containers[name]; ok {
		t.Error("Container was not removed via force removal")
	}
}

func TestGetContainerStatus(t *testing.T) {
	fake := docker_mock.NewFakeDockerClient()
	mgr := &Manager{cli: fake}
	ctx := context.Background()

	port := 7000
	name := "handholder-openhands-7000"

	// Case: Not running
	status, ws, err := mgr.GetContainerStatus(ctx, port)
	if err != nil {
		t.Fatalf("GetContainerStatus failed: %v", err)
	}
	if status != "not running" {
		t.Errorf("Expected 'not running', got %s", status)
	}

	// Case: Running
	fake.Containers[name] = &container.Config{
		Labels: map[string]string{"workspace": "alpha"},
	}

	status, ws, err = mgr.GetContainerStatus(ctx, port)
	if err != nil {
		t.Fatalf("GetContainerStatus failed: %v", err)
	}
	if status != "running" {
		t.Errorf("Expected 'running', got %s", status)
	}
	if ws != "alpha" {
		t.Errorf("Expected workspace 'alpha', got %s", ws)
	}
}
