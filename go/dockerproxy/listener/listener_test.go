package listener

import (
	"errors"
	"os"
	"path/filepath"
	"testing"

	"github.com/Matir/hacks/go/dockerproxy/config"
)

func TestNewListener_TCP(t *testing.T) {
	ln, err := New("tcp://127.0.0.1:0")
	if err != nil {
		t.Fatalf("unexpected error creating TCP listener: %v", err)
	}
	defer ln.Close()

	if ln.Addr().Network() != "tcp" {
		t.Errorf("expected network tcp, got %s", ln.Addr().Network())
	}
}

func TestNewListener_Unix(t *testing.T) {
	tmpDir := t.TempDir()
	sockPath := filepath.Join(tmpDir, "test.sock")

	ln, err := New("unix://" + sockPath)
	if err != nil {
		t.Fatalf("unexpected error creating Unix listener: %v", err)
	}

	if ln.Addr().Network() != "unix" {
		t.Errorf("expected network unix, got %s", ln.Addr().Network())
	}

	// Verify file exists
	if _, err := os.Stat(sockPath); err != nil {
		t.Errorf("expected socket file to exist at %s: %v", sockPath, err)
	}

	if err := ln.Close(); err != nil {
		t.Errorf("unexpected error closing unix listener: %v", err)
	}
}

func TestNewListener_UnsupportedScheme(t *testing.T) {
	_, err := New("http://localhost:8080")
	if !errors.Is(err, config.ErrUnsupportedSocket) {
		t.Errorf("expected ErrUnsupportedSocket, got %v", err)
	}
}

func TestParseAddr(t *testing.T) {
	tests := []struct {
		rawInput string
		network  string
		address  string
		wantErr  bool
	}{
		{"tcp://127.0.0.1:8080", "tcp", "127.0.0.1:8080", false},
		{"unix:///var/run/docker.sock", "unix", "/var/run/docker.sock", false},
		{"http://localhost", "", "", true},
		{"invalid", "", "", true},
	}

	for _, tt := range tests {
		netw, addr, err := ParseAddr(tt.rawInput)
		if (err != nil) != tt.wantErr {
			t.Errorf("ParseAddr(%q) error = %v, wantErr %v", tt.rawInput, err, tt.wantErr)
			continue
		}
		if netw != tt.network || addr != tt.address {
			t.Errorf("ParseAddr(%q) = (%q, %q), want (%q, %q)", tt.rawInput, netw, addr, tt.network, tt.address)
		}
	}
}
