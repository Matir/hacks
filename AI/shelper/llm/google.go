package llm

import (
	"context"
	"fmt"
	"os"

	"google.golang.org/genai"
)

// GoogleGenAIProvider wraps the Google Gen AI Go SDK client.
type GoogleGenAIProvider struct {
	client *genai.Client
}

// NewGoogleGenAIProvider initializes the Google Gen AI SDK client.
// It automatically resolves the API key from the GEMINI_API_KEY environment variable.
func NewGoogleGenAIProvider() (*GoogleGenAIProvider, error) {
	apiKey := os.Getenv("GEMINI_API_KEY")
	if apiKey == "" {
		return nil, fmt.Errorf("GEMINI_API_KEY environment variable is not set")
	}

	// Initialize using default configuration
	ctx := context.Background()
	client, err := genai.NewClient(ctx, &genai.ClientConfig{
		APIKey: apiKey,
	})
	if err != nil {
		return nil, fmt.Errorf("failed to create Google Gen AI client: %w", err)
	}

	return &GoogleGenAIProvider{
		client: client,
	}, nil
}

// Name returns the provider name.
func (g *GoogleGenAIProvider) Name() string {
	return "google"
}

// Generate sends the prompt to the Gemini API and returns the generated content.
func (g *GoogleGenAIProvider) Generate(ctx context.Context, req *GenerateRequest) (*GenerateResponse, error) {
	model := req.Model
	if model == "" {
		model = "gemini-2.5-flash"
	}

	// We can configure system instructions and generation parameters.
	var config *genai.GenerateContentConfig
	if req.SystemPrompt != "" || req.Temperature != nil {
		config = &genai.GenerateContentConfig{}
		if req.SystemPrompt != "" {
			config.SystemInstruction = &genai.Content{
				Parts: []*genai.Part{
					{
						Text: req.SystemPrompt,
					},
				},
			}
		}
		if req.Temperature != nil {
			tempVal := float32(*req.Temperature)
			config.Temperature = &tempVal
		}
	}

	resp, err := g.client.Models.GenerateContent(ctx, model, genai.Text(req.UserPrompt), config)
	if err != nil {
		return nil, fmt.Errorf("gemini content generation failed: %w", err)
	}

	// Extract text response
	outputText := ""
	if len(resp.Candidates) > 0 && len(resp.Candidates[0].Content.Parts) > 0 {
		outputText = resp.Candidates[0].Content.Parts[0].Text
	}

	// Extract tokens usage metadata if available
	tokensUsed := 0
	if resp.UsageMetadata != nil {
		tokensUsed = int(resp.UsageMetadata.TotalTokenCount)
	}

	return &GenerateResponse{
		Output:     outputText,
		Model:      model,
		Provider:   "google",
		TokensUsed: tokensUsed,
	}, nil
}
