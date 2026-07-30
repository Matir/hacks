package llm

import (
	"context"
	"fmt"

	"github.com/openai/openai-go"
	"github.com/openai/openai-go/option"
	"github.com/openai/openai-go/shared"
)

// OpenAIProvider wraps the OpenAI Go SDK client.
type OpenAIProvider struct {
	client openai.Client
}

// NewOpenAIProvider initializes the OpenAI client using the explicitly injected key.
func NewOpenAIProvider(apiKey string) (*OpenAIProvider, error) {
	if apiKey == "" {
		return nil, fmt.Errorf("OpenAI API key is empty")
	}

	client := openai.NewClient(option.WithAPIKey(apiKey))
	return &OpenAIProvider{
		client: client,
	}, nil
}

// Name returns the provider name.
func (o *OpenAIProvider) Name() string {
	return "openai"
}

// Generate sends the prompt to the OpenAI API and returns the generated content.
func (o *OpenAIProvider) Generate(ctx context.Context, req *GenerateRequest) (*GenerateResponse, error) {
	modelName := req.Model
	if modelName == "" {
		modelName = "gpt-4o"
	}

	// Prepare messages array
	var messages []openai.ChatCompletionMessageParamUnion
	if req.SystemPrompt != "" {
		messages = append(messages, openai.SystemMessage(req.SystemPrompt))
	}
	messages = append(messages, openai.UserMessage(req.UserPrompt))

	// Configure chat completion parameters
	params := openai.ChatCompletionNewParams{
		Model:    shared.ChatModel(modelName),
		Messages: messages,
	}
	if req.Temperature != nil {
		params.Temperature = openai.Float(*req.Temperature)
	}

	resp, err := o.client.Chat.Completions.New(ctx, params)
	if err != nil {
		return nil, fmt.Errorf("openai chat completions failed: %w", err)
	}

	// Extract text response
	outputText := ""
	if len(resp.Choices) > 0 {
		outputText = resp.Choices[0].Message.Content
	}

	// Extract tokens usage metadata
	tokensUsed := 0
	if resp.Usage.TotalTokens > 0 {
		tokensUsed = int(resp.Usage.TotalTokens)
	}

	return &GenerateResponse{
		Output:     outputText,
		Model:      modelName,
		Provider:   "openai",
		TokensUsed: tokensUsed,
	}, nil
}
