package policy

import (
	"errors"
	"fmt"

	"github.com/matir/hacks/go/ghtokenbroker/config"
)

// ErrUnknownAgent is returned when no agent matches the provided API key.
var ErrUnknownAgent = errors.New("policy: unknown agent")

// Engine resolves authentication and authorisation decisions from a static
// set of agent policies.
type Engine struct {
	// byKey maps API key to the corresponding agent config.
	byKey map[string]*config.AgentConfig
}

// New builds an Engine from the provided agent configs. It returns an error if
// any two agents share an API key (which would be a misconfiguration).
func New(agents []config.AgentConfig) (*Engine, error) {
	byKey := make(map[string]*config.AgentConfig, len(agents))
	for i := range agents {
		a := &agents[i]
		if _, exists := byKey[a.APIKey]; exists {
			return nil, fmt.Errorf("policy: duplicate api_key for agent %q", a.ID)
		}
		byKey[a.APIKey] = a
	}
	return &Engine{byKey: byKey}, nil
}

// Authenticate looks up the agent associated with apiKey. Returns
// ErrUnknownAgent if no match is found.
func (e *Engine) Authenticate(apiKey string) (*config.AgentConfig, error) {
	a, ok := e.byKey[apiKey]
	if !ok {
		return nil, ErrUnknownAgent
	}
	return a, nil
}

// Authorize checks whether agent is permitted to request the given permissions
// on repo. It returns the intersection of the requested and maximum permitted
// permissions, or an error describing the first violation.
//
// Rules:
//  1. The repo must be in agent.AllowedRepos.
//  2. Each requested permission must be present in agent.MaxPermissions and the
//     requested level must not exceed the maximum level.
func (e *Engine) Authorize(agent *config.AgentConfig, repo string, requested config.PermissionSet) (config.PermissionSet, error) {
	if !repoAllowed(agent, repo) {
		return nil, fmt.Errorf("policy: repo %q is not allowed for agent %q", repo, agent.ID)
	}
	for name, level := range requested {
		if !agent.MaxPermissions.Allows(name, level) {
			return nil, fmt.Errorf("policy: permission %q=%q is not allowed for agent %q", name, level, agent.ID)
		}
	}
	// Granted set is the requested set (already validated against max).
	granted := make(config.PermissionSet, len(requested))
	for k, v := range requested {
		granted[k] = v
	}
	return granted, nil
}

func repoAllowed(agent *config.AgentConfig, repo string) bool {
	for _, r := range agent.AllowedRepos {
		if r == repo {
			return true
		}
	}
	return false
}
