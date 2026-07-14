package config

import (
	"errors"
	"os"
	"path/filepath"
	"testing"
)

func TestLoadRuleset_ValidSemantic(t *testing.T) {
	yamlData := []byte(`
version: "1.0"
default_action: allow
rules:
  - id: deny-priv
    action: deny
    command_types: ["create"]
    container_create:
      privileged: true
      allowed_mounts: ["^/var/log/.*"]
  - id: filter-list
    action: filter
    command_types: ["list"]
    response_filter:
      allowed_names: ["^safe-.*"]
`)
	tmpFile := filepath.Join(t.TempDir(), "rules_semantic.yaml")
	if err := os.WriteFile(tmpFile, yamlData, 0600); err != nil {
		t.Fatalf("failed writing temp rules file: %v", err)
	}

	rs, err := LoadRuleset(tmpFile)
	if err != nil {
		t.Fatalf("unexpected error loading semantic ruleset: %v", err)
	}

	if len(rs.Rules) != 2 {
		t.Fatalf("expected 2 rules, got %d", len(rs.Rules))
	}
	if rs.Rules[0].ContainerCreate == nil || rs.Rules[0].ContainerCreate.Privileged == nil || !*rs.Rules[0].ContainerCreate.Privileged {
		t.Errorf("expected privileged=true in ContainerCreateRule")
	}
	if rs.Rules[1].ResponseFilter == nil || len(rs.Rules[1].ResponseFilter.AllowedNames) != 1 {
		t.Errorf("expected allowed_names in ResponseFilterRule")
	}
}

func TestLoadRuleset_InvalidSemanticRegex(t *testing.T) {
	yamlData := []byte(`
version: "1.0"
rules:
  - id: bad-mount-regex
    action: deny
    container_create:
      allowed_mounts: ["[unclosed"]
`)
	tmpFile := filepath.Join(t.TempDir(), "bad_regex.yaml")
	_ = os.WriteFile(tmpFile, yamlData, 0600)

	_, err := LoadRuleset(tmpFile)
	if !errors.Is(err, ErrInvalidRule) {
		t.Errorf("expected ErrInvalidRule on bad semantic regex, got %v", err)
	}
}

func TestLoadRuleset_Valid(t *testing.T) {
	yamlData := []byte(`
version: "1.0"
default_action: deny
rules:
  - id: allow-get
    methods: ["GET"]
    path_pattern: "^/v[\\d\\.]+/containers/json$"
    action: allow
`)
	tmpFile := filepath.Join(t.TempDir(), "rules.yaml")
	if err := os.WriteFile(tmpFile, yamlData, 0600); err != nil {
		t.Fatalf("failed writing temp rules file: %v", err)
	}

	rs, err := LoadRuleset(tmpFile)
	if err != nil {
		t.Fatalf("unexpected error loading ruleset: %v", err)
	}

	if rs.Version != "1.0" {
		t.Errorf("expected version 1.0, got %s", rs.Version)
	}
	if rs.DefaultAction != "deny" {
		t.Errorf("expected default action deny, got %s", rs.DefaultAction)
	}
	if len(rs.Rules) != 1 {
		t.Fatalf("expected 1 rule, got %d", len(rs.Rules))
	}
	if rs.Rules[0].ID != "allow-get" {
		t.Errorf("expected rule ID allow-get, got %s", rs.Rules[0].ID)
	}
}

func TestLoadRuleset_NotFound(t *testing.T) {
	_, err := LoadRuleset("/path/to/nonexistent/file.yaml")
	if !errors.Is(err, ErrRulesetNotFound) {
		t.Errorf("expected ErrRulesetNotFound, got %v", err)
	}
}

func TestLoadRuleset_Malformed(t *testing.T) {
	tmpFile := filepath.Join(t.TempDir(), "bad.yaml")
	_ = os.WriteFile(tmpFile, []byte("version: [unclosed"), 0600)

	_, err := LoadRuleset(tmpFile)
	if !errors.Is(err, ErrInvalidRule) {
		t.Errorf("expected ErrInvalidRule, got %v", err)
	}
}
