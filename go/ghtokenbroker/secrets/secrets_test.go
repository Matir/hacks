package secrets_test

import (
	"context"
	"os"
	"path/filepath"
	"testing"

	"github.com/matir/hacks/go/ghtokenbroker/config"
	"github.com/matir/hacks/go/ghtokenbroker/secrets"
)

func TestLoadPrivateKey_FromFile(t *testing.T) {
	content := []byte("fake-pem-content")
	dir := t.TempDir()
	path := filepath.Join(dir, "key.pem")
	if err := os.WriteFile(path, content, 0600); err != nil {
		t.Fatalf("write key file: %v", err)
	}

	cfg := config.GitHubAppConfig{PrivateKeyFile: path}
	got, err := secrets.LoadPrivateKey(context.Background(), cfg)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if string(got) != string(content) {
		t.Errorf("got %q, want %q", got, content)
	}
}

func TestLoadPrivateKey_FileNotFound(t *testing.T) {
	cfg := config.GitHubAppConfig{PrivateKeyFile: filepath.Join(t.TempDir(), "nope.pem")}
	_, err := secrets.LoadPrivateKey(context.Background(), cfg)
	if err == nil {
		t.Fatal("expected error for missing file")
	}
}

func TestLoadPrivateKey_NoSource(t *testing.T) {
	cfg := config.GitHubAppConfig{}
	_, err := secrets.LoadPrivateKey(context.Background(), cfg)
	if err == nil {
		t.Fatal("expected error when no source is configured")
	}
}
