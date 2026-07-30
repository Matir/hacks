// Package llm defines the core provider contracts and data structures for SHelper LLM integration.
package llm

import (
	"context"
)

// GenerateRequest represents the provider-agnostic LLM generation request.
type GenerateRequest struct {
	Model       string
	SystemPrompt string
	UserPrompt   string
	Temperature *float64
}

// GenerateResponse represents the provider-agnostic LLM completion response.
type GenerateResponse struct {
	Output     string
	Model      string
	Provider   string
	TokensUsed int
}

// Provider defines the interface that all LLM vendors (Google Gen AI, OpenAI, etc.) must implement.
type Provider interface {
	// Name returns the provider identifier (e.g. "google", "openai").
	Name() string

	// Generate performs the LLM completion API call.
	Generate(ctx context.Context, req *GenerateRequest) (*GenerateResponse, error)
}
