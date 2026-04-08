// Package config handles the parsing and management of HandHolder configuration.
package config

import (
	"fmt"
	"io"
	"log/slog"
	"os"
	"os/user"
	"strings"

	"github.com/BurntSushi/toml"
	"github.com/joho/godotenv"
)

// Config represents the top-level configuration structure for HandHolder.
type Config struct {
	HandHolder HandHolderConfig           `toml:"handholder"`
	Defaults   WorkspaceConfig            `toml:"defaults"`
	Workspaces map[string]WorkspaceConfig `toml:"workspace"`
}

// HandHolderConfig contains global settings for the HandHolder service itself.
type HandHolderConfig struct {
	BindAddress        string   `toml:"bind_address"`
	Port               int      `toml:"port"`
	Logging            string   `toml:"logging"`
	LogFormat          string   `toml:"logformat"`
	DockerSocket       string   `toml:"docker_socket"`
	TrustedProxies     []string `toml:"trusted_proxies"`
	DisableSocketMount bool     `toml:"disable_socket_mount"`
	PreloadImages      bool     `toml:"preload_images"`
}

// WorkspaceConfig contains settings for a specific OpenHands workspace or global defaults.
type WorkspaceConfig struct {
	Workspace        string            `toml:"workspace"`
	Name             string            `toml:"name"`
	Port             int               `toml:"port"`
	Image            string            `toml:"image"`
	SandboxBaseImage string            `toml:"sandbox_base_image"`
	SandboxUserID    string            `toml:"sandbox_user_id"`
	LLMModel         string            `toml:"llm_model"`
	LLMProvider      string            `toml:"llm_provider"`
	LLMAPIKey        string            `toml:"llm_api_key"`
	EnvFile          string            `toml:"env_file"`
	Env              map[string]string `toml:"env"`
}

// LoadConfig reads and parses a TOML configuration file from the given path.
func LoadConfig(path string) (*Config, error) {
	var cfg Config
	// Default PreloadImages to true
	cfg.HandHolder.PreloadImages = true

	if _, err := toml.DecodeFile(path, &cfg); err != nil {
		return nil, fmt.Errorf("failed to decode config: %w", err)
	}

	// Apply default image if not set
	if cfg.Defaults.Image == "" {
		cfg.Defaults.Image = "ghcr.io/all-hands-ai/openhands:0.21.0"
	}

	// Apply default port if not set
	if cfg.Defaults.Port == 0 {
		cfg.Defaults.Port = 3000
	}

	// Apply default sandbox user ID if not set
	if cfg.Defaults.SandboxUserID == "" {
		u, err := user.Current()
		if err == nil {
			cfg.Defaults.SandboxUserID = u.Uid
		}
	}

	// Default to binding only to 127.0.0.1 for security
	if cfg.HandHolder.BindAddress == "" {
		cfg.HandHolder.BindAddress = "127.0.0.1"
	}

	// Always trust localhost by default
	localhosts := []string{"127.0.0.1", "::1"}
	for _, lh := range localhosts {
		found := false
		for _, tp := range cfg.HandHolder.TrustedProxies {
			if tp == lh {
				found = true
				break
			}
		}
		if !found {
			cfg.HandHolder.TrustedProxies = append(cfg.HandHolder.TrustedProxies, lh)
		}
	}

	if err := cfg.Validate(); err != nil {
		return nil, fmt.Errorf("config validation failed: %w", err)
	}

	return &cfg, nil
}

// Validate checks the configuration for consistency and basic correctness.
func (cfg *Config) Validate() error {
	ports := make(map[int]string)
	names := make(map[string]string)

	for id, ws := range cfg.Workspaces {
		// Validate port
		port := ws.Port
		if port == 0 {
			port = cfg.Defaults.Port
		}
		if port < 1024 || port > 65535 {
			return fmt.Errorf("invalid port %d for workspace %s (must be 1024-65535)", port, id)
		}
		if otherID, ok := ports[port]; ok {
			return fmt.Errorf("duplicate port %d used by workspaces %s and %s", port, id, otherID)
		}
		ports[port] = id

		// Validate name
		if ws.Name == "" {
			return fmt.Errorf("workspace %s missing name", id)
		}
		if otherID, ok := names[ws.Name]; ok {
			return fmt.Errorf("duplicate name %q used by workspaces %s and %s", ws.Name, id, otherID)
		}
		names[ws.Name] = id
	}

	// Also check HandHolder service port
	if cfg.HandHolder.Port != 0 {
		if cfg.HandHolder.Port < 1024 || cfg.HandHolder.Port > 65535 {
			return fmt.Errorf("invalid handholder port %d (must be 1024-65535)", cfg.HandHolder.Port)
		}
		if otherID, ok := ports[cfg.HandHolder.Port]; ok {
			return fmt.Errorf("handholder port %d conflicts with workspace %s", cfg.HandHolder.Port, otherID)
		}
	}

	return nil
}

// Overrides represents command-line flag overrides for HandHolder settings.
type Overrides struct {
	BindAddress        string
	Port               int
	Logging            string
	LogFormat          string
	DockerSocket       string
	TrustedProxies     string
	DisableSocketMount *bool
	PreloadImages      *bool
}

// ApplyOverrides applies the provided flag overrides to the configuration.
// It only overrides values that are non-zero/non-empty in the Overrides struct.
func (cfg *Config) ApplyOverrides(o Overrides) {
	if o.BindAddress != "" {
		cfg.HandHolder.BindAddress = o.BindAddress
	}
	if o.Port != 0 {
		cfg.HandHolder.Port = o.Port
	}
	if o.Logging != "" {
		cfg.HandHolder.Logging = o.Logging
	}
	if o.LogFormat != "" {
		cfg.HandHolder.LogFormat = o.LogFormat
	}
	if o.DockerSocket != "" {
		cfg.HandHolder.DockerSocket = o.DockerSocket
	}
	if o.TrustedProxies != "" {
		var proxies []string
		for _, p := range strings.Split(o.TrustedProxies, ",") {
			p = strings.TrimSpace(p)
			if p != "" {
				proxies = append(proxies, p)
			}
		}
		cfg.HandHolder.TrustedProxies = proxies
	}
	if o.DisableSocketMount != nil {
		cfg.HandHolder.DisableSocketMount = *o.DisableSocketMount
	}
	if o.PreloadImages != nil {
		cfg.HandHolder.PreloadImages = *o.PreloadImages
	}
}

// DefaultEnv returns the default environment variables for all containers.
// It also includes SANDBOX_BASE_CONTAINER_IMAGE, SANDBOX_USER_ID, LLM_MODEL, and LLM_API_KEY if specified in the defaults.
func DefaultEnv(defaults WorkspaceConfig) map[string]string {
	env := map[string]string{
		"RUNTIME": "docker",
	}
	if defaults.SandboxBaseImage != "" {
		env["SANDBOX_BASE_CONTAINER_IMAGE"] = EnsureTag(defaults.SandboxBaseImage)
	}
	if defaults.SandboxUserID != "" {
		env["SANDBOX_USER_ID"] = defaults.SandboxUserID
	}
	if defaults.LLMModel != "" {
		val := defaults.LLMModel
		if defaults.LLMProvider != "" && !strings.Contains(val, "/") {
			val = defaults.LLMProvider + "/" + val
		}
		env["LLM_MODEL"] = val
	}
	if defaults.LLMAPIKey != "" {
		env["LLM_API_KEY"] = defaults.LLMAPIKey
	}
	return env
}

// EnsureTag adds :latest if no tag is present in the image name.
func EnsureTag(image string) string {
	if !strings.Contains(image, ":") {
		return image + ":latest"
	}
	return image
}

// ResolveEnv merges environment variables from multiple sources based on priority.
// Priority (later overrides earlier):
// 0. Default: RUNTIME=docker (from DefaultEnv)
// 0.1 Global default SandboxBaseImage
// 1. Global/Default env_file
// 2. Global/Default env map
// 3. Workspace-specific SandboxBaseImage
// 4. Workspace-specific env_file
// 5. Workspace-specific env map
func (w *WorkspaceConfig) ResolveEnv(defaults WorkspaceConfig) (map[string]string, error) {
	resolved := DefaultEnv(defaults)

	// 1. Global/Default env_file
	if defaults.EnvFile != "" {
		if err := loadEnvFile(defaults.EnvFile, resolved); err != nil {
			return nil, err
		}
	}

	// 2. Global/Default env map
	for k, v := range defaults.Env {
		resolved[k] = v
	}

	// 3. Workspace-specific SandboxBaseImage
	if w.SandboxBaseImage != "" {
		resolved["SANDBOX_BASE_CONTAINER_IMAGE"] = EnsureTag(w.SandboxBaseImage)
	}

	// 3.1 Workspace-specific SandboxUserID
	if w.SandboxUserID != "" {
		resolved["SANDBOX_USER_ID"] = w.SandboxUserID
	}

	// 3.2 Workspace-specific LLM settings
	if w.LLMModel != "" {
		val := w.LLMModel
		provider := w.LLMProvider
		if provider == "" {
			provider = defaults.LLMProvider
		}
		if provider != "" && !strings.Contains(val, "/") {
			val = provider + "/" + val
		}
		resolved["LLM_MODEL"] = val
	} else if w.LLMProvider != "" && defaults.LLMModel != "" {
		// Only provider overridden, use default model
		val := defaults.LLMModel
		if !strings.Contains(val, "/") {
			val = w.LLMProvider + "/" + val
		}
		resolved["LLM_MODEL"] = val
	}

	if w.LLMAPIKey != "" {
		resolved["LLM_API_KEY"] = w.LLMAPIKey
	}

	// 4. Workspace-specific env_file
	if w.EnvFile != "" {
		if err := loadEnvFile(w.EnvFile, resolved); err != nil {
			return nil, err
		}
	}

	// 5. Workspace-specific env map
	for k, v := range w.Env {
		resolved[k] = v
	}

	return resolved, nil
}

// loadEnvFile parses a .env file and adds its contents to the target map.
func loadEnvFile(path string, target map[string]string) error {
	f, err := os.Open(path)
	if err != nil {
		return fmt.Errorf("failed to open env file %s: %w", path, err)
	}
	defer f.Close()

	envs, err := godotenv.Parse(f)
	if err != nil {
		return fmt.Errorf("failed to parse env file %s: %w", path, err)
	}

	for k, v := range envs {
		target[k] = v
	}
	return nil
}

// GetLogHandler returns a slog.Handler based on the provided logging and format configuration.
func GetLogHandler(logging string, format string) (slog.Handler, error) {
	var w io.Writer
	switch logging {
	case "stdout":
		w = os.Stdout
	case "stderr", "":
		w = os.Stderr
	default:
		f, err := os.OpenFile(logging, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
		if err != nil {
			return nil, err
		}
		w = f
	}

	opts := &slog.HandlerOptions{}
	if format == "json" {
		return slog.NewJSONHandler(w, opts), nil
	}
	return slog.NewTextHandler(w, opts), nil
}
