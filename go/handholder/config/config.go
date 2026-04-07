// Package config handles the parsing and management of HandHolder configuration.
package config

import (
	"fmt"
	"io"
	"os"

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
	Port         int    `toml:"port"`
	Logging      string `toml:"logging"`
	LogFormat    string `toml:"logformat"`
	DockerSocket string `toml:"docker_socket"`
}

// WorkspaceConfig contains settings for a specific OpenHands workspace or global defaults.
type WorkspaceConfig struct {
	Workspace string            `toml:"workspace"`
	Name      string            `toml:"name"`
	Port      int               `toml:"port"`
	Image     string            `toml:"image"`
	EnvFile   string            `toml:"env_file"`
	Env       map[string]string `toml:"env"`
}

// LoadConfig reads and parses a TOML configuration file from the given path.
func LoadConfig(path string) (*Config, error) {
	var cfg Config
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

	return &cfg, nil
}

// ResolveEnv merges environment variables from multiple sources based on priority.
// Priority (later overrides earlier):
// 1. Global/Default env_file
// 2. Global/Default env map
// 3. Workspace-specific env_file
// 4. Workspace-specific env map
func (w *WorkspaceConfig) ResolveEnv(defaults WorkspaceConfig) (map[string]string, error) {
	resolved := make(map[string]string)

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

	// 3. Workspace-specific env_file
	if w.EnvFile != "" {
		if err := loadEnvFile(w.EnvFile, resolved); err != nil {
			return nil, err
		}
	}

	// 4. Workspace-specific env map
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

// GetLogWriter returns an io.Writer based on the provided logging configuration string.
// Supports "stdout", "stderr", or a file path.
func GetLogWriter(logging string) (io.Writer, error) {
	switch logging {
	case "stdout":
		return os.Stdout, nil
	case "stderr", "":
		return os.Stderr, nil
	default:
		return os.OpenFile(logging, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	}
}
