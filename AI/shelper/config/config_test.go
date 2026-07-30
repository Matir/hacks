package config

import (
	"fmt"
	"os"
	"path/filepath"
	"testing"
)

func TestResolveSocketPath(t *testing.T) {
	// Save existing env
	origSock := os.Getenv("SHELPER_SOCK")
	origXdg := os.Getenv("XDG_RUNTIME_DIR")
	origTmp := os.Getenv("TMPDIR")
	defer func() {
		os.Setenv("SHELPER_SOCK", origSock)
		os.Setenv("XDG_RUNTIME_DIR", origXdg)
		os.Setenv("TMPDIR", origTmp)
	}()

	t.Run("Explicit SHELPER_SOCK override", func(t *testing.T) {
		os.Setenv("SHELPER_SOCK", "/tmp/custom.sock")
		os.Setenv("XDG_RUNTIME_DIR", "/run/user/1000")
		os.Setenv("TMPDIR", "/var/tmp")

		got := ResolveSocketPath()
		want := "/tmp/custom.sock"
		if got != want {
			t.Errorf("got %q, want %q", got, want)
		}
	})

	t.Run("XDG_RUNTIME_DIR fallback", func(t *testing.T) {
		os.Unsetenv("SHELPER_SOCK")
		os.Setenv("XDG_RUNTIME_DIR", "/run/user/1000")
		os.Setenv("TMPDIR", "/var/tmp")

		got := ResolveSocketPath()
		want := "/run/user/1000/shelper.sock"
		if got != want {
			t.Errorf("got %q, want %q", got, want)
		}
	})

	t.Run("TMPDIR fallback", func(t *testing.T) {
		os.Unsetenv("SHELPER_SOCK")
		os.Unsetenv("XDG_RUNTIME_DIR")
		os.Setenv("TMPDIR", "/var/tmp")

		uid := os.Getuid()
		got := ResolveSocketPath()
		want := filepath.Join("/var/tmp", fmt.Sprintf("shelper.%d.sock", uid))
		if got != want {
			t.Errorf("got %q, want %q", got, want)
		}
	})

	t.Run("Default /tmp fallback", func(t *testing.T) {
		os.Unsetenv("SHELPER_SOCK")
		os.Unsetenv("XDG_RUNTIME_DIR")
		os.Unsetenv("TMPDIR")

		uid := os.Getuid()
		got := ResolveSocketPath()
		want := filepath.Join("/tmp", fmt.Sprintf("shelper.%d.sock", uid))
		if got != want {
			t.Errorf("got %q, want %q", got, want)
		}
	})
}

func TestLoadConfigPrecedence(t *testing.T) {
	// Set up temporary configuration directory and file
	tmpDir := t.TempDir()
	tempTomlPath := filepath.Join(tmpDir, "shelper.toml")

	// Mock the default config file path
	origConfigPath := DefaultConfigPath
	DefaultConfigPath = tempTomlPath
	defer func() {
		DefaultConfigPath = origConfigPath
	}()

	// Save existing env
	origProvider := os.Getenv("SHELPER_DEFAULT_PROVIDER")
	origGeminiKey := os.Getenv("GEMINI_API_KEY")
	origOpenaiKey := os.Getenv("OPENAI_API_KEY")
	defer func() {
		os.Setenv("SHELPER_DEFAULT_PROVIDER", origProvider)
		os.Setenv("GEMINI_API_KEY", origGeminiKey)
		os.Setenv("OPENAI_API_KEY", origOpenaiKey)
	}()

	// 1. Test Fallback Defaults
	t.Run("Precedence: Defaults", func(t *testing.T) {
		os.Unsetenv("SHELPER_DEFAULT_PROVIDER")
		os.Unsetenv("GEMINI_API_KEY")
		os.Unsetenv("OPENAI_API_KEY")
		// Remove TOML file if exists
		os.Remove(tempTomlPath)

		cfg, err := LoadConfig([]string{})
		if err != nil {
			t.Fatalf("load failed: %v", err)
		}

		if cfg.DefaultProvider != "gemini" {
			t.Errorf("expected default provider 'gemini', got %q", cfg.DefaultProvider)
		}
		if cfg.DefaultModel != "gemini-3.5-flash" {
			t.Errorf("expected default model 'gemini-3.5-flash', got %q", cfg.DefaultModel)
		}
	})

	// 2. Test Environment Variables Override Defaults
	t.Run("Precedence: Env Overrides Defaults", func(t *testing.T) {
		os.Setenv("SHELPER_DEFAULT_PROVIDER", "openai")
		os.Setenv("GEMINI_API_KEY", "env-gemini-key")
		os.Setenv("OPENAI_API_KEY", "env-openai-key")
		os.Remove(tempTomlPath)

		cfg, err := LoadConfig([]string{})
		if err != nil {
			t.Fatalf("load failed: %v", err)
		}

		if cfg.DefaultProvider != "openai" {
			t.Errorf("expected env provider 'openai', got %q", cfg.DefaultProvider)
		}
		if cfg.GeminiAPIKey != "env-gemini-key" {
			t.Errorf("expected env key, got %q", cfg.GeminiAPIKey)
		}
	})

	// 3. Test TOML Overrides Env & Defaults
	t.Run("Precedence: TOML Overrides Env", func(t *testing.T) {
		os.Setenv("SHELPER_DEFAULT_PROVIDER", "openai")
		os.Setenv("GEMINI_API_KEY", "env-gemini-key")

		// Write TOML
		tomlContent := `
llm_provider = "gemini"
llm_model = "gpt-4o"
gemini_api_key = "toml-gemini-key"
`
		if err := os.WriteFile(tempTomlPath, []byte(tomlContent), 0600); err != nil {
			t.Fatalf("write file failed: %v", err)
		}

		cfg, err := LoadConfig([]string{})
		if err != nil {
			t.Fatalf("load failed: %v", err)
		}

		// Provider should be gemini (from TOML) overriding openai (from Env)
		if cfg.DefaultProvider != "gemini" {
			t.Errorf("expected TOML provider 'gemini', got %q", cfg.DefaultProvider)
		}
		// Model should be gpt-4o (from TOML)
		if cfg.DefaultModel != "gpt-4o" {
			t.Errorf("expected TOML model 'gpt-4o', got %q", cfg.DefaultModel)
		}
		// Gemini API Key should be from TOML
		if cfg.GeminiAPIKey != "toml-gemini-key" {
			t.Errorf("expected TOML key, got %q", cfg.GeminiAPIKey)
		}
	})

	// 4. Test CLI Flags Override TOML
	t.Run("Precedence: CLI Overrides TOML", func(t *testing.T) {
		tomlContent := `
llm_provider = "gemini"
llm_model = "gpt-4o"
`
		if err := os.WriteFile(tempTomlPath, []byte(tomlContent), 0600); err != nil {
			t.Fatalf("write file failed: %v", err)
		}

		// Pass flags overriding provider and model
		args := []string{
			"--llm-provider=openai",
			"--llm-model=gpt-4o-mini",
			"--gemini-api-key=cli-gemini-key",
		}

		cfg, err := LoadConfig(args)
		if err != nil {
			t.Fatalf("load failed: %v", err)
		}

		// CLI flags override TOML
		if cfg.DefaultProvider != "openai" {
			t.Errorf("expected CLI provider 'openai', got %q", cfg.DefaultProvider)
		}
		if cfg.DefaultModel != "gpt-4o-mini" {
			t.Errorf("expected CLI model 'gpt-4o-mini', got %q", cfg.DefaultModel)
		}
		if cfg.GeminiAPIKey != "cli-gemini-key" {
			t.Errorf("expected CLI key, got %q", cfg.GeminiAPIKey)
		}
	})
}

