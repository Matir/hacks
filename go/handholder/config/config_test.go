package config

import (
	"log/slog"
	"os"
	"os/user"
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
sandbox_base_image = "debian"

[workspace.test]
name = "Test Workspace"
workspace = "/tmp/test"
sandbox_base_image = "ubuntu:22.04"
`
	if err := os.WriteFile(configPath, []byte(content), 0644); err != nil {
		t.Fatalf("failed to write test config: %v", err)
	}

	cfg, err := LoadConfig(configPath)
	if err != nil {
		t.Fatalf("LoadConfig failed: %v", err)
	}

	if cfg.Defaults.SandboxBaseImage != "debian" {
		t.Errorf("expected default sandbox_base_image debian, got %s", cfg.Defaults.SandboxBaseImage)
	}

	u, _ := user.Current()
	if cfg.Defaults.SandboxUserID != u.Uid {
		t.Errorf("expected default sandbox_user_id %s, got %s", u.Uid, cfg.Defaults.SandboxUserID)
	}

	if cfg.HandHolder.PreloadImages != true {
		t.Errorf("expected default preload_images true, got %v", cfg.HandHolder.PreloadImages)
	}

	// Test override in TOML
	content2 := `
[handholder]
preload_images = false
`
	configPath2 := filepath.Join(tmpDir, "handholder2.toml")
	os.WriteFile(configPath2, []byte(content2), 0644)
	cfg2, _ := LoadConfig(configPath2)
	if cfg2.HandHolder.PreloadImages != false {
		t.Errorf("expected preload_images false from TOML, got %v", cfg2.HandHolder.PreloadImages)
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
		SandboxBaseImage: "debian", // becomes debian:latest
		SandboxUserID:    "1234",
		EnvFile:          globalEnvPath,
		Env: map[string]string{
			"MAP_KEY":      "global_map",
			"OVERRIDE_KEY": "global_map_override",
		},
	}

	ws := WorkspaceConfig{
		SandboxBaseImage: "ubuntu:22.04",
		SandboxUserID:    "5678",
		EnvFile:          wsEnvPath,
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
		"RUNTIME":                      "docker",
		"SANDBOX_BASE_CONTAINER_IMAGE": "ubuntu:22.04", // Workspace override wins
		"SANDBOX_USER_ID":              "5678",         // Workspace override wins
		"GLOBAL_KEY":                   "global_val",
		"WS_KEY":                       "ws_val",
		"MAP_KEY":                      "global_map",
		"WS_MAP_KEY":                   "ws_map",
		"OVERRIDE_KEY":                 "final_override",
	}

	if !reflect.DeepEqual(resolved, expected) {
		t.Errorf("ResolveEnv mismatch.\nExpected: %v\nGot:      %v", expected, resolved)
	}

	// Test default only
	wsEmpty := WorkspaceConfig{}
	resolved2, _ := wsEmpty.ResolveEnv(defaults)
	if resolved2["SANDBOX_BASE_CONTAINER_IMAGE"] != "debian:latest" {
		t.Errorf("expected debian:latest, got %s", resolved2["SANDBOX_BASE_CONTAINER_IMAGE"])
	}
	if resolved2["SANDBOX_USER_ID"] != "1234" {
		t.Errorf("expected sandbox user id 1234, got %s", resolved2["SANDBOX_USER_ID"])
	}
}

func TestDefaultEnv(t *testing.T) {
	tests := []struct {
		name     string
		defaults WorkspaceConfig
		expected map[string]string
	}{
		{
			"Only RUNTIME",
			WorkspaceConfig{},
			map[string]string{"RUNTIME": "docker"},
		},
		{
			"All settings",
			WorkspaceConfig{
				SandboxBaseImage: "debian",
				SandboxUserID:    "1000",
				LLMModel:         "gpt-4",
				LLMProvider:      "openai",
				LLMAPIKey:        "sk-123",
			},
			map[string]string{
				"RUNTIME":                      "docker",
				"SANDBOX_BASE_CONTAINER_IMAGE": "debian:latest",
				"SANDBOX_USER_ID":              "1000",
				"LLM_MODEL":                    "openai/gpt-4",
				"LLM_API_KEY":                  "sk-123",
			},
		},
		{
			"Model with slash (no prefixing)",
			WorkspaceConfig{
				LLMModel:    "custom/model",
				LLMProvider: "provider",
			},
			map[string]string{
				"RUNTIME":   "docker",
				"LLM_MODEL": "custom/model",
			},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := DefaultEnv(tt.defaults)
			if !reflect.DeepEqual(got, tt.expected) {
				t.Errorf("DefaultEnv() = %v, want %v", got, tt.expected)
			}
		})
	}
}

func TestResolveEnvLLM(t *testing.T) {
	defaults := WorkspaceConfig{
		LLMModel:    "default-model",
		LLMProvider: "default-provider",
	}

	tests := []struct {
		name     string
		ws       WorkspaceConfig
		expected string
	}{
		{
			"Inherit all",
			WorkspaceConfig{},
			"default-provider/default-model",
		},
		{
			"Override model only",
			WorkspaceConfig{LLMModel: "ws-model"},
			"default-provider/ws-model",
		},
		{
			"Override provider only",
			WorkspaceConfig{LLMProvider: "ws-provider"},
			"ws-provider/default-model",
		},
		{
			"Override both",
			WorkspaceConfig{LLMModel: "ws-model", LLMProvider: "ws-provider"},
			"ws-provider/ws-model",
		},
		{
			"Override model with slash",
			WorkspaceConfig{LLMModel: "manual/model"},
			"manual/model",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			resolved, _ := tt.ws.ResolveEnv(defaults)
			if resolved["LLM_MODEL"] != tt.expected {
				t.Errorf("LLM_MODEL = %q, want %q", resolved["LLM_MODEL"], tt.expected)
			}
		})
	}
}

func TestResolveEnvErrors(t *testing.T) {
	defaults := WorkspaceConfig{EnvFile: "/non/existent/file"}
	ws := WorkspaceConfig{}
	if _, err := ws.ResolveEnv(defaults); err == nil {
		t.Error("expected error for non-existent global env file")
	}

	defaults = WorkspaceConfig{}
	ws = WorkspaceConfig{EnvFile: "/non/existent/file"}
	if _, err := ws.ResolveEnv(defaults); err == nil {
		t.Error("expected error for non-existent workspace env file")
	}
}

func TestApplyOverrides(t *testing.T) {
	cfg := &Config{
		HandHolder: HandHolderConfig{
			BindAddress:    "127.0.0.1",
			Port:           3000,
			PreloadImages:  true,
			TrustedProxies: []string{"1.2.3.4"},
		},
	}

	f := false
	cfg.ApplyOverrides(Overrides{
		BindAddress:    "0.0.0.0",
		Port:           3001,
		TrustedProxies: "10.0.0.1, 192.168.1.1",
		PreloadImages:  &f,
	})

	if cfg.HandHolder.BindAddress != "0.0.0.0" {
		t.Errorf("expected 0.0.0.0, got %s", cfg.HandHolder.BindAddress)
	}
	if cfg.HandHolder.Port != 3001 {
		t.Errorf("expected 3001, got %d", cfg.HandHolder.Port)
	}
	if cfg.HandHolder.PreloadImages != false {
		t.Errorf("expected preload_images false, got %v", cfg.HandHolder.PreloadImages)
	}
	expectedProxies := []string{"10.0.0.1", "192.168.1.1"}
	if !reflect.DeepEqual(cfg.HandHolder.TrustedProxies, expectedProxies) {
		t.Errorf("expected proxies %v, got %v", expectedProxies, cfg.HandHolder.TrustedProxies)
	}
}

func TestLoadConfigDefaults(t *testing.T) {
	tmpDir := t.TempDir()
	configPath := filepath.Join(tmpDir, "config.toml")

	content := `
[workspace.alpha]
name = "Alpha"
`
	os.WriteFile(configPath, []byte(content), 0644)

	cfg, err := LoadConfig(configPath)
	if err != nil {
		t.Fatalf("LoadConfig failed: %v", err)
	}

	if cfg.HandHolder.BindAddress != "127.0.0.1" {
		t.Errorf("expected default bind address 127.0.0.1, got %s", cfg.HandHolder.BindAddress)
	}

	// Should include localhost in trusted proxies by default
	found := false
	for _, tp := range cfg.HandHolder.TrustedProxies {
		if tp == "127.0.0.1" {
			found = true
			break
		}
	}
	if !found {
		t.Error("expected 127.0.0.1 to be in trusted proxies by default")
	}

	// Test malformed config
	malformedPath := filepath.Join(tmpDir, "malformed.toml")
	os.WriteFile(malformedPath, []byte("this is not toml"), 0644)
	if _, err := LoadConfig(malformedPath); err == nil {
		t.Error("expected error for malformed TOML")
	}

	// Test validation error
	invalidPath := filepath.Join(tmpDir, "invalid.toml")
	invalidContent := `
[workspace.ws1]
name = "WS1"
port = 3000
[workspace.ws2]
name = "WS2"
port = 3000
`
	os.WriteFile(invalidPath, []byte(invalidContent), 0644)
	if _, err := LoadConfig(invalidPath); err == nil {
		t.Error("expected error for duplicate port in config")
	}
}

func TestConfigValidate(t *testing.T) {
	tests := []struct {
		name    string
		cfg     Config
		wantErr bool
	}{
		{
			"Valid config",
			Config{
				Defaults: WorkspaceConfig{Port: 3000},
				Workspaces: map[string]WorkspaceConfig{
					"ws1": {Name: "WS1", Port: 3001},
					"ws2": {Name: "WS2", Port: 3002},
				},
			},
			false,
		},
		{
			"Duplicate port",
			Config{
				Defaults: WorkspaceConfig{Port: 3000},
				Workspaces: map[string]WorkspaceConfig{
					"ws1": {Name: "WS1", Port: 3001},
					"ws2": {Name: "WS2", Port: 3001},
				},
			},
			true,
		},
		{
			"Duplicate name",
			Config{
				Defaults: WorkspaceConfig{Port: 3000},
				Workspaces: map[string]WorkspaceConfig{
					"ws1": {Name: "WS1", Port: 3001},
					"ws2": {Name: "WS1", Port: 3002},
				},
			},
			true,
		},
		{
			"Invalid port",
			Config{
				Defaults: WorkspaceConfig{Port: 3000},
				Workspaces: map[string]WorkspaceConfig{
					"ws1": {Name: "WS1", Port: 80},
				},
			},
			true,
		},
		{
			"Missing name",
			Config{
				Defaults: WorkspaceConfig{Port: 3000},
				Workspaces: map[string]WorkspaceConfig{
					"ws1": {Port: 3001},
				},
			},
			true,
		},
		{
			"HandHolder port conflict",
			Config{
				HandHolder: HandHolderConfig{Port: 3001},
				Workspaces: map[string]WorkspaceConfig{
					"ws1": {Name: "WS1", Port: 3001},
				},
			},
			true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := tt.cfg.Validate()
			if (err != nil) != tt.wantErr {
				t.Errorf("Validate() error = %v, wantErr %v", err, tt.wantErr)
			}
		})
	}
}

func TestResolveEnvPriority(t *testing.T) {
	// Scenario: Global sandbox_base_image is overridden by global env map
	defaults := WorkspaceConfig{
		SandboxBaseImage: "global-base",
		Env: map[string]string{
			"SANDBOX_BASE_CONTAINER_IMAGE": "global-env-override",
		},
	}
	ws := WorkspaceConfig{}
	resolved, _ := ws.ResolveEnv(defaults)
	if resolved["SANDBOX_BASE_CONTAINER_IMAGE"] != "global-env-override" {
		t.Errorf("Global env map should override global sandbox_base_image. Got: %s", resolved["SANDBOX_BASE_CONTAINER_IMAGE"])
	}

	// Scenario: Workspace sandbox_base_image overrides global settings
	ws.SandboxBaseImage = "workspace-base"
	resolved, _ = ws.ResolveEnv(defaults)
	if resolved["SANDBOX_BASE_CONTAINER_IMAGE"] != "workspace-base:latest" {
		t.Errorf("Workspace sandbox_base_image should override global settings. Got: %s", resolved["SANDBOX_BASE_CONTAINER_IMAGE"])
	}

	// Scenario: Workspace env map overrides workspace sandbox_base_image
	ws.Env = map[string]string{
		"SANDBOX_BASE_CONTAINER_IMAGE": "workspace-env-override",
	}
	resolved, _ = ws.ResolveEnv(defaults)
	if resolved["SANDBOX_BASE_CONTAINER_IMAGE"] != "workspace-env-override" {
		t.Errorf("Workspace env map should override workspace sandbox_base_image. Got: %s", resolved["SANDBOX_BASE_CONTAINER_IMAGE"])
	}
}

func TestGetLogHandler(t *testing.T) {
	// Case: stdout
	h, err := GetLogHandler("stdout", "text")
	if err != nil {
		t.Fatalf("GetLogHandler failed: %v", err)
	}
	if h == nil {
		t.Fatal("GetLogHandler returned nil handler")
	}

	// Case: json
	h, err = GetLogHandler("stderr", "json")
	if err != nil {
		t.Fatalf("GetLogHandler failed: %v", err)
	}
	if _, ok := h.(*slog.JSONHandler); !ok {
		t.Errorf("expected JSONHandler, got %T", h)
	}

	// Case: file path
	tmpFile := filepath.Join(t.TempDir(), "test.log")
	h, err = GetLogHandler(tmpFile, "text")
	if err != nil {
		t.Fatalf("GetLogHandler failed: %v", err)
	}
	if h == nil {
		t.Fatal("GetLogHandler returned nil handler")
	}
}
