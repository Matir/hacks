package config

import (
	"errors"
	"fmt"
	"time"

	"github.com/BurntSushi/toml"
)

// Config is the top-level configuration structure loaded from a TOML file.
type Config struct {
	Server    ServerConfig    `toml:"server"`
	GitHubApp GitHubAppConfig `toml:"github_app"`
	Cache     CacheConfig     `toml:"cache"`
	Agents    []AgentConfig   `toml:"agents"`
}

// ServerConfig controls the listening addresses.
type ServerConfig struct {
	TCPAddr    string `toml:"tcp_addr"`
	UnixSocket string `toml:"unix_socket"`
}

// GitHubAppConfig holds GitHub App identity and private key source.
// Exactly one of PrivateKeyFile or GCPSecretName must be set.
type GitHubAppConfig struct {
	AppID          int64  `toml:"app_id"`
	PrivateKeyFile string `toml:"private_key_file"`
	GCPSecretName  string `toml:"gcp_secret_name"`
}

// CacheConfig controls in-memory caching behaviour.
type CacheConfig struct {
	InstallationTTL duration `toml:"installation_ttl"`
}

// AgentConfig describes a single agent's identity and policy.
type AgentConfig struct {
	ID             string        `toml:"id"`
	APIKey         string        `toml:"api_key"`
	AllowedRepos   []string      `toml:"allowed_repos"`
	MaxPermissions PermissionSet `toml:"max_permissions"`
}

// PermissionSet maps GitHub permission names to their access level ("read" or "write").
type PermissionSet map[string]string

// ValidLevels are the allowed permission level values.
var validLevels = map[string]int{
	"read":  1,
	"write": 2,
}

// Allows returns true when the requested level is within this set's maximum for the
// given permission name. An absent permission in the set means it is not allowed at all.
func (ps PermissionSet) Allows(name, requested string) bool {
	maxLevel, ok := ps[name]
	if !ok {
		return false
	}
	reqInt, ok := validLevels[requested]
	if !ok {
		return false
	}
	maxInt, ok := validLevels[maxLevel]
	if !ok {
		return false
	}
	return reqInt <= maxInt
}

// Load reads and parses the TOML file at path and validates the result.
func Load(path string) (*Config, error) {
	var cfg Config
	if _, err := toml.DecodeFile(path, &cfg); err != nil {
		return nil, fmt.Errorf("config: decode %s: %w", path, err)
	}
	if err := cfg.validate(); err != nil {
		return nil, fmt.Errorf("config: validation: %w", err)
	}
	return &cfg, nil
}

func (c *Config) validate() error {
	if c.Server.TCPAddr == "" && c.Server.UnixSocket == "" {
		return errors.New("server: at least one of tcp_addr or unix_socket must be set")
	}
	if c.GitHubApp.AppID == 0 {
		return errors.New("github_app: app_id must be set")
	}
	if c.GitHubApp.PrivateKeyFile == "" && c.GitHubApp.GCPSecretName == "" {
		return errors.New("github_app: one of private_key_file or gcp_secret_name must be set")
	}
	if c.GitHubApp.PrivateKeyFile != "" && c.GitHubApp.GCPSecretName != "" {
		return errors.New("github_app: only one of private_key_file or gcp_secret_name may be set")
	}
	if len(c.Agents) == 0 {
		return errors.New("agents: at least one agent must be configured")
	}
	seen := make(map[string]bool)
	for i, a := range c.Agents {
		if a.ID == "" {
			return fmt.Errorf("agents[%d]: id must be set", i)
		}
		if a.APIKey == "" {
			return fmt.Errorf("agents[%d] (%s): api_key must be set", i, a.ID)
		}
		if seen[a.ID] {
			return fmt.Errorf("agents[%d]: duplicate agent id %q", i, a.ID)
		}
		seen[a.ID] = true
		if len(a.AllowedRepos) == 0 {
			return fmt.Errorf("agents[%d] (%s): allowed_repos must not be empty", i, a.ID)
		}
	}
	return nil
}

// duration is a wrapper around time.Duration that implements TOML string decoding.
type duration struct {
	time.Duration
}

func (d *duration) UnmarshalText(text []byte) error {
	v, err := time.ParseDuration(string(text))
	if err != nil {
		return err
	}
	d.Duration = v
	return nil
}
