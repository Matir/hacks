package policy_test

import (
	"errors"
	"testing"

	"github.com/matir/hacks/go/ghtokenbroker/config"
	"github.com/matir/hacks/go/ghtokenbroker/policy"
)

func makeEngine(t *testing.T) *policy.Engine {
	t.Helper()
	agents := []config.AgentConfig{
		{
			ID:           "coder",
			APIKey:       "coder-key",
			AllowedRepos: []string{"org/repo1"},
			MaxPermissions: config.PermissionSet{
				"contents":      "write",
				"pull_requests": "write",
				"issues":        "write",
				"metadata":      "read",
			},
		},
		{
			ID:           "reviewer",
			APIKey:       "reviewer-key",
			AllowedRepos: []string{"org/repo1", "org/repo2"},
			MaxPermissions: config.PermissionSet{
				"contents":      "read",
				"pull_requests": "write",
				"issues":        "write",
				"metadata":      "read",
			},
		},
	}
	e, err := policy.New(agents)
	if err != nil {
		t.Fatalf("policy.New: %v", err)
	}
	return e
}

func TestAuthenticate_Valid(t *testing.T) {
	e := makeEngine(t)
	agent, err := e.Authenticate("coder-key")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if agent.ID != "coder" {
		t.Errorf("agent.ID = %q, want coder", agent.ID)
	}
}

func TestAuthenticate_UnknownKey(t *testing.T) {
	e := makeEngine(t)
	_, err := e.Authenticate("bad-key")
	if !errors.Is(err, policy.ErrUnknownAgent) {
		t.Errorf("expected ErrUnknownAgent, got %v", err)
	}
}

func TestAuthorize_AllowedRepo(t *testing.T) {
	e := makeEngine(t)
	agent, _ := e.Authenticate("coder-key")
	req := config.PermissionSet{"contents": "write", "metadata": "read"}
	granted, err := e.Authorize(agent, "org/repo1", req)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if granted["contents"] != "write" {
		t.Errorf("granted contents = %q, want write", granted["contents"])
	}
}

func TestAuthorize_DisallowedRepo(t *testing.T) {
	e := makeEngine(t)
	agent, _ := e.Authenticate("coder-key")
	_, err := e.Authorize(agent, "org/secret", config.PermissionSet{"contents": "read"})
	if err == nil {
		t.Fatal("expected error for disallowed repo")
	}
}

func TestAuthorize_ElevatedPermission(t *testing.T) {
	e := makeEngine(t)
	// reviewer has max contents=read; requesting write should fail
	agent, _ := e.Authenticate("reviewer-key")
	_, err := e.Authorize(agent, "org/repo1", config.PermissionSet{"contents": "write"})
	if err == nil {
		t.Fatal("expected error for elevated permission")
	}
}

func TestAuthorize_ExactMaxPermission(t *testing.T) {
	e := makeEngine(t)
	agent, _ := e.Authenticate("reviewer-key")
	_, err := e.Authorize(agent, "org/repo1", config.PermissionSet{"contents": "read"})
	if err != nil {
		t.Fatalf("unexpected error at exact max permission: %v", err)
	}
}

func TestAuthorize_UnknownPermissionName(t *testing.T) {
	e := makeEngine(t)
	agent, _ := e.Authenticate("coder-key")
	_, err := e.Authorize(agent, "org/repo1", config.PermissionSet{"administration": "write"})
	if err == nil {
		t.Fatal("expected error for permission not in max set")
	}
}

func TestNew_DuplicateAPIKey(t *testing.T) {
	agents := []config.AgentConfig{
		{ID: "a1", APIKey: "same", AllowedRepos: []string{"org/r"}, MaxPermissions: config.PermissionSet{"metadata": "read"}},
		{ID: "a2", APIKey: "same", AllowedRepos: []string{"org/r"}, MaxPermissions: config.PermissionSet{"metadata": "read"}},
	}
	_, err := policy.New(agents)
	if err == nil {
		t.Fatal("expected error for duplicate API key")
	}
}

func TestAuthorize_GrantedMatchesRequested(t *testing.T) {
	e := makeEngine(t)
	agent, _ := e.Authenticate("coder-key")
	req := config.PermissionSet{"contents": "read", "metadata": "read"}
	granted, err := e.Authorize(agent, "org/repo1", req)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	for k, v := range req {
		if granted[k] != v {
			t.Errorf("granted[%q] = %q, want %q", k, granted[k], v)
		}
	}
}
