package config_test

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/matir/hacks/go/ghtokenbroker/config"
)

func writeConfig(t *testing.T, content string) string {
	t.Helper()
	f, err := os.CreateTemp(t.TempDir(), "config-*.toml")
	if err != nil {
		t.Fatalf("create temp file: %v", err)
	}
	if _, err := f.WriteString(content); err != nil {
		t.Fatalf("write temp file: %v", err)
	}
	f.Close()
	return f.Name()
}

func TestLoad_Valid(t *testing.T) {
	path := writeConfig(t, `
[server]
tcp_addr = ":8080"

[github_app]
app_id = 1
private_key_file = "/tmp/key.pem"

[cache]
installation_ttl = "5m"

[[agents]]
id = "agent1"
api_key = "key1"
allowed_repos = ["org/repo1"]

[agents.max_permissions]
contents = "read"
metadata = "read"
`)
	cfg, err := config.Load(path)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if cfg.Server.TCPAddr != ":8080" {
		t.Errorf("tcp_addr = %q, want :8080", cfg.Server.TCPAddr)
	}
	if cfg.GitHubApp.AppID != 1 {
		t.Errorf("app_id = %d, want 1", cfg.GitHubApp.AppID)
	}
	if len(cfg.Agents) != 1 || cfg.Agents[0].ID != "agent1" {
		t.Errorf("agents = %v", cfg.Agents)
	}
}

func TestLoad_MissingFile(t *testing.T) {
	_, err := config.Load(filepath.Join(t.TempDir(), "nope.toml"))
	if err == nil {
		t.Fatal("expected error for missing file")
	}
}

func TestLoad_NoListeners(t *testing.T) {
	path := writeConfig(t, `
[server]

[github_app]
app_id = 1
private_key_file = "/tmp/key.pem"

[[agents]]
id = "a"
api_key = "k"
allowed_repos = ["org/repo"]

[agents.max_permissions]
contents = "read"
`)
	_, err := config.Load(path)
	if err == nil {
		t.Fatal("expected error: no listeners configured")
	}
}

func TestLoad_BothKeySourcesSet(t *testing.T) {
	path := writeConfig(t, `
[server]
tcp_addr = ":8080"

[github_app]
app_id = 1
private_key_file = "/tmp/key.pem"
gcp_secret_name = "projects/p/secrets/s/versions/latest"

[[agents]]
id = "a"
api_key = "k"
allowed_repos = ["org/repo"]

[agents.max_permissions]
contents = "read"
`)
	_, err := config.Load(path)
	if err == nil {
		t.Fatal("expected error: both key sources set")
	}
}

func TestLoad_NoKeySource(t *testing.T) {
	path := writeConfig(t, `
[server]
tcp_addr = ":8080"

[github_app]
app_id = 1

[[agents]]
id = "a"
api_key = "k"
allowed_repos = ["org/repo"]

[agents.max_permissions]
contents = "read"
`)
	_, err := config.Load(path)
	if err == nil {
		t.Fatal("expected error: no key source")
	}
}

func TestLoad_NoAgents(t *testing.T) {
	path := writeConfig(t, `
[server]
tcp_addr = ":8080"

[github_app]
app_id = 1
private_key_file = "/tmp/key.pem"
`)
	_, err := config.Load(path)
	if err == nil {
		t.Fatal("expected error: no agents")
	}
}

func TestLoad_DuplicateAgentID(t *testing.T) {
	path := writeConfig(t, `
[server]
tcp_addr = ":8080"

[github_app]
app_id = 1
private_key_file = "/tmp/key.pem"

[[agents]]
id = "same"
api_key = "k1"
allowed_repos = ["org/repo"]

[agents.max_permissions]
contents = "read"

[[agents]]
id = "same"
api_key = "k2"
allowed_repos = ["org/repo"]

[agents.max_permissions]
contents = "read"
`)
	_, err := config.Load(path)
	if err == nil {
		t.Fatal("expected error: duplicate agent id")
	}
}

func TestPermissionSet_Allows(t *testing.T) {
	ps := config.PermissionSet{
		"contents": "write",
		"metadata": "read",
	}

	tests := []struct {
		name, level string
		want        bool
	}{
		{"contents", "read", true},
		{"contents", "write", true},
		{"metadata", "read", true},
		{"metadata", "write", false},     // exceeds max
		{"pull_requests", "read", false}, // not in set
		{"contents", "admin", false},     // invalid level
	}
	for _, tt := range tests {
		got := ps.Allows(tt.name, tt.level)
		if got != tt.want {
			t.Errorf("Allows(%q, %q) = %v, want %v", tt.name, tt.level, got, tt.want)
		}
	}
}
