package llm

import (
	"context"
)

// GenerateRequest represents a provider-agnostic request for LLM generation.
type GenerateRequest struct {
	Model        string
	SystemPrompt string
	UserPrompt   string
	Temperature  *float64
}

// GenerateResponse represents the provider-agnostic response payload.
type GenerateResponse struct {
	Output     string
	Model      string
	Provider   string
	TokensUsed int
}

// Provider defines the standard interface that all LLM client wrapper packages must satisfy.
type Provider interface {
	// Name returns the provider identifier string (e.g. "google", "openai").
	Name() string

	// Generate dispatches the structured prompt to the target LLM vendor.
	Generate(ctx context.Context, req *GenerateRequest) (*GenerateResponse, error)
}
