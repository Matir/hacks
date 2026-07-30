package llm

import (
	"context"
	"testing"
)

type MockProvider struct {
	name string
}

func (m *MockProvider) Name() string {
	return m.name
}

func (m *MockProvider) Generate(ctx context.Context, req *GenerateRequest) (*GenerateResponse, error) {
	return &GenerateResponse{
		Output:     "Mock Output for: " + req.UserPrompt,
		Model:      "mock-model",
		Provider:   m.name,
		TokensUsed: 10,
	}, nil
}

func TestRegistry(t *testing.T) {
	r := NewRegistry()
	mock := &MockProvider{name: "mock"}
	r.Register(mock)

	p, err := r.Get("mock")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if p.Name() != "mock" {
		t.Errorf("got name %q, want 'mock'", p.Name())
	}

	resp, err := p.Generate(context.Background(), &GenerateRequest{UserPrompt: "test prompt"})
	if err != nil {
		t.Fatalf("generate error: %v", err)
	}
	want := "Mock Output for: test prompt"
	if resp.Output != want {
		t.Errorf("got output %q, want %q", resp.Output, want)
	}

	_, err = r.Get("nonexistent")
	if err == nil {
		t.Errorf("expected error for nonexistent provider, got nil")
	}
}
