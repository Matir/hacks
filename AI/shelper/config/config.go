package config

import (
	"flag"
	"fmt"
	"os"
	"path/filepath"

	"github.com/BurntSushi/toml"
)

// DefaultConfigPath defines the default user-level location for the toml config.
// We make it a variable so tests can override it.
var DefaultConfigPath = func() string {
	home, err := os.UserHomeDir()
	if err == nil && home != "" {
		return filepath.Join(home, ".config", "shelper", "shelper.toml")
	}
	return ""
}()

// Config represents the application configuration resolved from CLI, TOML, Env, and defaults.
type Config struct {
	SocketPath       string
	CustomPromptPath string
	DefaultProvider  string
	DefaultModel     string
	GeminiAPIKey     string
	OpenAIAPIKey     string
	LogFile          string
	LogLevel         string
	MaxWorkers       int
}

// tomlConfig struct reflects the exact keys configured in helper.toml
type tomlConfig struct {
	LLMProvider  *string `toml:"llm_provider"`
	LLMModel     *string `toml:"llm_model"`
	GeminiAPIKey *string `toml:"gemini_api_key"`
	OpenAIAPIKey *string `toml:"openai_api_key"`
	LogFile      *string `toml:"logfile"`
	LogLevel     *string `toml:"loglevel"`
}

// ResolveSocketPath determines the Unix domain socket path according to the resolution order:
// 1. $SHELPER_SOCK
// 2. ${XDG_RUNTIME_DIR}/shelper.sock
// 3. ${TMPDIR}/shelper.${UID}.sock (or /tmp/shelper.${UID}.sock if TMPDIR is unset)
func ResolveSocketPath() string {
	if sock := os.Getenv("SHELPER_SOCK"); sock != "" {
		return sock
	}

	if xdg := os.Getenv("XDG_RUNTIME_DIR"); xdg != "" {
		return filepath.Join(xdg, "shelper.sock")
	}

	tmpDir := os.Getenv("TMPDIR")
	if tmpDir == "" {
		tmpDir = "/tmp"
	}
	uid := os.Getuid()
	return filepath.Join(tmpDir, fmt.Sprintf("shelper.%d.sock", uid))
}

// LoadConfig loads and merges configurations.
// Precedence: CLI Flags > TOML Config > Environment Variables > Defaults.
func LoadConfig(args []string) (*Config, error) {
	// 1. Set fallback defaults
	cfg := &Config{
		SocketPath:      ResolveSocketPath(),
		DefaultProvider: "gemini",
		DefaultModel:    "gemini-2.5-flash",
		LogLevel:        "info",
		MaxWorkers:      20,
	}

	home, err := os.UserHomeDir()
	if err == nil && home != "" {
		cfg.CustomPromptPath = filepath.Join(home, ".config", "shelper", "prompt.md")
	}

	// 2. Load from Environment Variables
	if envProvider := os.Getenv("SHELPER_DEFAULT_PROVIDER"); envProvider != "" {
		cfg.DefaultProvider = envProvider
	}
	if envGeminiKey := os.Getenv("GEMINI_API_KEY"); envGeminiKey != "" {
		cfg.GeminiAPIKey = envGeminiKey
	}
	if envOpenaiKey := os.Getenv("OPENAI_API_KEY"); envOpenaiKey != "" {
		cfg.OpenAIAPIKey = envOpenaiKey
	}

	// 3. Load from TOML file (if exists)
	if DefaultConfigPath != "" {
		if _, err := os.Stat(DefaultConfigPath); err == nil {
			var tc tomlConfig
			if _, err := toml.DecodeFile(DefaultConfigPath, &tc); err == nil {
				if tc.LLMProvider != nil {
					cfg.DefaultProvider = *tc.LLMProvider
				}
				if tc.LLMModel != nil {
					cfg.DefaultModel = *tc.LLMModel
				}
				if tc.GeminiAPIKey != nil {
					cfg.GeminiAPIKey = *tc.GeminiAPIKey
				}
				if tc.OpenAIAPIKey != nil {
					cfg.OpenAIAPIKey = *tc.OpenAIAPIKey
				}
				if tc.LogFile != nil {
					cfg.LogFile = *tc.LogFile
				}
				if tc.LogLevel != nil {
					cfg.LogLevel = *tc.LogLevel
				}
			}
		}
	}

	// 4. Bind CLI Flags (using resolved values from Defaults/Env/TOML as defaults for flags)
	fs := flag.NewFlagSet("shelperd", flag.ContinueOnError)

	cliProvider := fs.String("llm-provider", cfg.DefaultProvider, "Active LLM backend provider (gemini or openai)")
	cliModel := fs.String("llm-model", cfg.DefaultModel, "Specific LLM model ID")
	cliGeminiKey := fs.String("gemini-api-key", cfg.GeminiAPIKey, "API Credential for Google Gemini")
	cliOpenaiKey := fs.String("openai-api-key", cfg.OpenAIAPIKey, "API Credential for OpenAI")
	cliLogFile := fs.String("logfile", cfg.LogFile, "Path to output logs")
	cliLogLevel := fs.String("loglevel", cfg.LogLevel, "Filtering log level (info, warning, error)")
	cliSocket := fs.String("socket", cfg.SocketPath, "Path for Unix socket")

	if err := fs.Parse(args); err != nil {
		return nil, fmt.Errorf("failed to parse CLI flags: %w", err)
	}

	// Apply parsed flag values back
	cfg.DefaultProvider = *cliProvider
	cfg.DefaultModel = *cliModel
	cfg.GeminiAPIKey = *cliGeminiKey
	cfg.OpenAIAPIKey = *cliOpenaiKey
	cfg.LogFile = *cliLogFile
	cfg.LogLevel = *cliLogLevel
	cfg.SocketPath = *cliSocket

	return cfg, nil
}
