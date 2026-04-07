package config

import (
	"os"
	"path/filepath"
	"reflect"
	"testing"
)

func TestLoadConfig(t *testing.T) {
	tmpDir := t.TempDir()
	configPath := filepath.Join(tmpDir, "handholder.toml")
	
	content := `
[handholder]
port = 3001
logging = "stderr"

[defaults]
port = 3000
image = "custom-image"

[workspace.test]
name = "Test Workspace"
workspace = "/tmp/test"
`
	if err := os.WriteFile(configPath, []byte(content), 0644); err != nil {
		t.Fatalf("failed to write test config: %v", err)
	}

	cfg, err := LoadConfig(configPath)
	if err != nil {
		t.Fatalf("LoadConfig failed: %v", err)
	}

	if cfg.HandHolder.Port != 3001 {
		t.Errorf("expected handholder port 3001, got %d", cfg.HandHolder.Port)
	}

	if cfg.Defaults.Image != "custom-image" {
		t.Errorf("expected default image custom-image, got %s", cfg.Defaults.Image)
	}

	ws, ok := cfg.Workspaces["test"]
	if !ok {
		t.Fatal("workspace 'test' not found in config")
	}
	if ws.Name != "Test Workspace" {
		t.Errorf("expected workspace name 'Test Workspace', got %s", ws.Name)
	}
}

func TestResolveEnv(t *testing.T) {
	tmpDir := t.TempDir()
	
	// Create global env file
	globalEnvPath := filepath.Join(tmpDir, "global.env")
	os.WriteFile(globalEnvPath, []byte("GLOBAL_KEY=global_val\nOVERRIDE_KEY=global_override"), 0644)

	// Create workspace env file
	wsEnvPath := filepath.Join(tmpDir, "ws.env")
	os.WriteFile(wsEnvPath, []byte("WS_KEY=ws_val\nOVERRIDE_KEY=ws_override"), 0644)

	defaults := WorkspaceConfig{
		EnvFile: globalEnvPath,
		Env: map[string]string{
			"MAP_KEY":      "global_map",
			"OVERRIDE_KEY": "global_map_override",
		},
	}

	ws := WorkspaceConfig{
		EnvFile: wsEnvPath,
		Env: map[string]string{
			"WS_MAP_KEY":   "ws_map",
			"OVERRIDE_KEY": "final_override",
		},
	}

	resolved, err := ws.ResolveEnv(defaults)
	if err != nil {
		t.Fatalf("ResolveEnv failed: %v", err)
	}

	expected := map[string]string{
		"GLOBAL_KEY":   "global_val",
		"WS_KEY":       "ws_val",
		"MAP_KEY":      "global_map",
		"WS_MAP_KEY":   "ws_map",
		"OVERRIDE_KEY": "final_override", // Last override wins
	}

	if !reflect.DeepEqual(resolved, expected) {
		t.Errorf("ResolveEnv mismatch.\nExpected: %v\nGot:      %v", expected, resolved)
	}
}

func TestGetLogWriter(t *testing.T) {
	// Case: stdout
	w, _ := GetLogWriter("stdout")
	if w != os.Stdout {
		t.Errorf("expected os.Stdout, got %v", w)
	}

	// Case: stderr
	w, _ = GetLogWriter("stderr")
	if w != os.Stderr {
		t.Errorf("expected os.Stderr, got %v", w)
	}

	// Case: default/empty
	w, _ = GetLogWriter("")
	if w != os.Stderr {
		t.Errorf("expected os.Stderr, got %v", w)
	}

	// Case: file path
	tmpFile := filepath.Join(t.TempDir(), "test.log")
	w, err := GetLogWriter(tmpFile)
	if err != nil {
		t.Fatalf("GetLogWriter failed: %v", err)
	}
	f, ok := w.(*os.File)
	if !ok || f.Name() != tmpFile {
		t.Errorf("expected file %s, got %v", tmpFile, w)
	}
	f.Close()
}
