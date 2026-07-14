// Package rules implements policy ruleset models and matching algorithms for API requests.
package rules

import (
	"github.com/moby/moby/api/types/container"
	"github.com/moby/moby/api/types/image"
)

// Action defines the decision outcome for a policy evaluation.
type Action string

const (
	// ActionAllow permits the request to be forwarded upstream.
	ActionAllow Action = "allow"
	// ActionDeny blocks the request and returns HTTP 403 Forbidden.
	ActionDeny Action = "deny"
	// ActionFilter indicates response list items should be sanitized.
	ActionFilter Action = "filter"
)

// ContainerCreateRequest aliases canonical container.CreateRequest from official Moby API types.
type ContainerCreateRequest = container.CreateRequest

// ExecCreateRequest aliases canonical container.ExecCreateRequest from official Moby API types.
type ExecCreateRequest = container.ExecCreateRequest

// ContainerSummary aliases canonical container.Summary from official Moby API types.
type ContainerSummary = container.Summary

// ImageSummary aliases canonical image.Summary from official Moby API types.
type ImageSummary = image.Summary

// HostConfig aliases canonical container.HostConfig from official Moby API types.
type HostConfig = container.HostConfig

// ContainerCreateRule defines semantic constraints evaluated against container creation requests.
type ContainerCreateRule struct {
	Privileged    *bool    `yaml:"privileged"`
	AllowedMounts []string `yaml:"allowed_mounts"`
	AllowedPorts  []string `yaml:"allowed_ports"`
	AllowedImages []string `yaml:"allowed_images"`
	AllowedNames  []string `yaml:"allowed_names"`
}

// ExecCreateRule defines semantic constraints evaluated against exec creation requests.
type ExecCreateRule struct {
	AllowedCommands   []string `yaml:"allowed_commands"`
	AllowedContainers []string `yaml:"allowed_containers"`
}

// ResponseFilterRule defines allowlist criteria applied to filter container or image list responses.
type ResponseFilterRule struct {
	AllowedNames  []string          `yaml:"allowed_names"`
	AllowedLabels map[string]string `yaml:"allowed_labels"`
}

// SemanticRule defines an individual access control or filtering directive within a ruleset.
type SemanticRule struct {
	ID              string               `yaml:"id"`
	Action          Action               `yaml:"action"`
	Message         string               `yaml:"message"`
	Methods         []string             `yaml:"methods"`
	PathPattern     string               `yaml:"path_pattern"`
	BodyPattern     string               `yaml:"body_pattern"`
	CommandTypes    []string             `yaml:"command_types"`
	ContainerCreate *ContainerCreateRule `yaml:"container_create"`
	ExecCreate      *ExecCreateRule      `yaml:"exec_create"`
	ResponseFilter  *ResponseFilterRule  `yaml:"response_filter"`
}

// PolicyRule alias for backwards compatibility during migration.
type PolicyRule = SemanticRule

// Ruleset defines the top-level security policy evaluated against incoming requests.
type Ruleset struct {
	Version       string         `yaml:"version"`
	DefaultAction Action         `yaml:"default_action"`
	Rules         []SemanticRule `yaml:"rules"`
}
