package integration

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"net"
	"os"
	"path/filepath"
	"shelper/daemon"
	"shelper/llm"
	"shelper/log"
	"shelper/prompt"
	"strings"
	"testing"
	"time"
)

// MockProvider satisfies llm.Provider interface for testing.
type MockProvider struct{}

func (m *MockProvider) Name() string { return "mock" }
func (m *MockProvider) Generate(ctx context.Context, req *llm.GenerateRequest) (*llm.GenerateResponse, error) {
	return &llm.GenerateResponse{
		Output:   "Mock response for: " + req.UserPrompt,
		Model:    req.Model,
		Provider: "mock",
	}, nil
}

// FailingProvider simulates upstream API errors for testing resilience.
type FailingProvider struct{}

func (f *FailingProvider) Name() string { return "failing" }
func (f *FailingProvider) Generate(ctx context.Context, req *llm.GenerateRequest) (*llm.GenerateResponse, error) {
	return nil, fmt.Errorf("simulated upstream network timeout/failure")
}

func TestDaemonIntegration(t *testing.T) {
	tmpDir := t.TempDir()
	sockPath := filepath.Join(tmpDir, "test.sock")

	// 1. Initialize Loader
	loader := prompt.NewLoader("") // Using bundled default

	// 2. Initialize Provider Registry
	registry := llm.NewRegistry()
	registry.Register(&MockProvider{})
	registry.Register(&FailingProvider{})

	// 3. Define requestHandler matching cmd/shelperd/main.go
	handler := func(ctx context.Context, req *daemon.SocketRequest) (*daemon.SocketResponse, error) {
		if req.Input == "" {
			return &daemon.SocketResponse{
				ID:     req.ID,
				Status: "error",
				Error: &daemon.ResponseError{
					Code:    "INVALID_REQUEST",
					Message: "field 'input' cannot be empty",
				},
			}, nil
		}

		providerName := req.Provider
		if providerName == "" {
			providerName = "mock"
		}
		provider, err := registry.Get(providerName)
		if err != nil {
			return &daemon.SocketResponse{
				ID:     req.ID,
				Status: "error",
				Error: &daemon.ResponseError{
					Code:    "INVALID_REQUEST",
					Message: "unsupported or unregistered provider",
					Details: err.Error(),
				},
			}, nil
		}

		tmpl, source, err := loader.LoadTemplate(req.Template)
		if err != nil {
			return &daemon.SocketResponse{
				ID:     req.ID,
				Status: "error",
				Error: &daemon.ResponseError{
					Code:    "TEMPLATE_ERROR",
					Message: "failed to load template",
					Details: err.Error(),
				},
			}, nil
		}
		formattedPrompt, err := loader.Execute(tmpl, prompt.TemplateContext{
			Input:     req.Input,
			Variables: req.Variables,
		})
		if err != nil {
			return &daemon.SocketResponse{
				ID:     req.ID,
				Status: "error",
				Error: &daemon.ResponseError{
					Code:    "TEMPLATE_ERROR",
					Message: "failed to render template",
					Details: err.Error(),
				},
			}, nil
		}

		genReq := &llm.GenerateRequest{
			Model:      req.Model,
			UserPrompt: formattedPrompt,
		}
		resp, err := provider.Generate(ctx, genReq)
		if err != nil {
			return &daemon.SocketResponse{
				ID:     req.ID,
				Status: "error",
				Error: &daemon.ResponseError{
					Code:    "PROVIDER_ERROR",
					Message: "upstream LLM generation failed",
					Details: err.Error(),
				},
			}, nil
		}

		return &daemon.SocketResponse{
			ID:     req.ID,
			Status: "success",
			Output: resp.Output,
			Metadata: daemon.ResponseMetadata{
				Provider:       resp.Provider,
				Model:          resp.Model,
				LatencyMs:      10,
				TemplateSource: source,
			},
		}, nil
	}

	// 4. Start Daemon with dummy logger
	dummyLogger := log.NewLogger(os.Stdout, "error")
	d := daemon.NewDaemon(sockPath, handler, dummyLogger)
	if err := d.Start(); err != nil {
		t.Fatalf("failed to start daemon: %v", err)
	}
	defer d.Stop()

	// Give the daemon a moment to bind and start listening
	time.Sleep(50 * time.Millisecond)

	// 5. Connect and run tests
	conn, err := net.Dial("unix", sockPath)
	if err != nil {
		t.Fatalf("failed to connect to socket: %v", err)
	}
	defer conn.Close()
	scanner := bufio.NewScanner(conn)

	// A. Valid Request Check
	req := daemon.SocketRequest{
		ID:    "req-1",
		Input: "hello test",
	}
	data, _ := json.Marshal(req)
	conn.Write(append(data, '\n'))
	if !scanner.Scan() {
		t.Fatalf("no response read from socket for req-1")
	}
	var resp daemon.SocketResponse
	json.Unmarshal(scanner.Bytes(), &resp)
	if resp.Status != "success" || resp.Output == "" {
		t.Errorf("expected success for req-1, got status %s", resp.Status)
	}

	// B. Invalid Request Check (Empty Input)
	invalidReq := daemon.SocketRequest{
		ID:    "req-2",
		Input: "",
	}
	invalidData, _ := json.Marshal(invalidReq)
	conn.Write(append(invalidData, '\n'))
	if !scanner.Scan() {
		t.Fatalf("no response read from socket for req-2")
	}
	var resp2 daemon.SocketResponse
	json.Unmarshal(scanner.Bytes(), &resp2)
	if resp2.Status != "error" || resp2.Error == nil || resp2.Error.Code != "INVALID_REQUEST" {
		t.Errorf("expected INVALID_REQUEST error for empty input, got: %+v", resp2)
	}

	// C. Unsupported Provider Check
	unsupportedReq := daemon.SocketRequest{
		ID:       "req-3",
		Input:    "something",
		Provider: "nonexistent",
	}
	unsupportedData, _ := json.Marshal(unsupportedReq)
	conn.Write(append(unsupportedData, '\n'))
	if !scanner.Scan() {
		t.Fatalf("no response read from socket for req-3")
	}
	var resp3 daemon.SocketResponse
	json.Unmarshal(scanner.Bytes(), &resp3)
	if resp3.Status != "error" || resp3.Error == nil || resp3.Error.Code != "INVALID_REQUEST" {
		t.Errorf("expected INVALID_REQUEST error for unsupported provider, got: %+v", resp3)
	}

	// D. Upstream Provider Failure Check
	failingReq := daemon.SocketRequest{
		ID:       "req-4",
		Input:    "something",
		Provider: "failing",
	}
	failingData, _ := json.Marshal(failingReq)
	conn.Write(append(failingData, '\n'))
	if !scanner.Scan() {
		t.Fatalf("no response read from socket for req-4")
	}
	var resp4 daemon.SocketResponse
	json.Unmarshal(scanner.Bytes(), &resp4)
	if resp4.Status != "error" || resp4.Error == nil || resp4.Error.Code != "PROVIDER_ERROR" {
		t.Errorf("expected PROVIDER_ERROR error for failing provider, got: %+v", resp4)
	}

	// 7. Verify status query
	statusReq := daemon.SocketRequest{
		ID:   "req-status",
		Type: "status",
	}
	statusData, _ := json.Marshal(statusReq)
	conn.Write(append(statusData, '\n'))
	if !scanner.Scan() {
		t.Fatalf("no response read from socket for status")
	}
	var statusResp daemon.SocketResponse
	json.Unmarshal(scanner.Bytes(), &statusResp)
	if statusResp.Status != "success" {
		t.Errorf("expected status 'success', got %q", statusResp.Status)
	}

	conn.Close()

	// 8. Stop daemon and verify socket cleanup
	d.Stop()
	if _, err := net.Dial("unix", sockPath); err == nil {
		t.Errorf("expected socket file to be cleaned up, but dial succeeded")
	}
}

func TestDaemonLoggingIntegration(t *testing.T) {
	tmpDir := t.TempDir()
	sockPath := filepath.Join(tmpDir, "test.sock")
	logFilePath := filepath.Join(tmpDir, "shelper.log")

	// Set up log file
	logFile, err := os.OpenFile(logFilePath, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0666)
	if err != nil {
		t.Fatalf("failed to open log file: %v", err)
	}
	defer logFile.Close()

	logger := log.NewLogger(logFile, "info")

	// Setup simple request handler
	handler := func(ctx context.Context, req *daemon.SocketRequest) (*daemon.SocketResponse, error) {
		logger.LogLLMRequest(req.ID, "mock", "mock-model", req.Input, "echo 'hello'", 100)
		return &daemon.SocketResponse{
			ID:     req.ID,
			Status: "success",
			Output: "echo 'hello'",
			Metadata: daemon.ResponseMetadata{
				Provider:       "mock",
				Model:          "mock-model",
				LatencyMs:      100,
				TemplateSource: "bundled",
			},
		}, nil
	}

	d := daemon.NewDaemon(sockPath, handler, logger)
	if err := d.Start(); err != nil {
		t.Fatalf("failed to start: %v", err)
	}
	defer d.Stop()

	// Dial socket and send request
	time.Sleep(50 * time.Millisecond)
	conn, err := net.Dial("unix", sockPath)
	if err != nil {
		t.Fatalf("failed to connect: %v", err)
	}
	defer conn.Close()

	req := daemon.SocketRequest{
		ID:    "req-log-test",
		Input: "say hello",
	}
	data, _ := json.Marshal(req)
	conn.Write(append(data, '\n'))

	scanner := bufio.NewScanner(conn)
	if !scanner.Scan() {
		t.Fatalf("failed to read response")
	}
	conn.Close()

	// Flush and read log file
	logFile.Sync()
	logBytes, err := os.ReadFile(logFilePath)
	if err != nil {
		t.Fatalf("failed to read log file: %v", err)
	}
	logContent := string(logBytes)

	// Verify telemetry log exists in the file
	if !strings.Contains(logContent, "req-log-test") {
		t.Errorf("expected Request ID 'req-log-test' inside logs: %q", logContent)
	}
	if !strings.Contains(logContent, "Prompt: say hello") {
		t.Errorf("expected prompt text inside logs: %q", logContent)
	}
	if !strings.Contains(logContent, "Response: echo 'hello'") {
		t.Errorf("expected response text inside logs: %q", logContent)
	}
	if !strings.Contains(logContent, "Latency: 100ms") {
		t.Errorf("expected latency delta in logs: %q", logContent)
	}
}
