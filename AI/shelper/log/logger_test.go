package log

import (
	"bytes"
	"strings"
	"testing"
)

func TestLogLevelFiltering(t *testing.T) {
	t.Run("Filters Info logs at Warning level", func(t *testing.T) {
		buf := new(bytes.Buffer)
		l := NewLogger(buf, "warning")

		l.Info("some info log")
		l.Warning("some warning log")
		l.Error("some error log")

		output := buf.String()
		if strings.Contains(output, "INFO") {
			t.Errorf("did not expect INFO logs: %q", output)
		}
		if !strings.Contains(output, "WARNING") || !strings.Contains(output, "ERROR") {
			t.Errorf("expected WARNING and ERROR logs: %q", output)
		}
	})

	t.Run("Logs all at Info level", func(t *testing.T) {
		buf := new(bytes.Buffer)
		l := NewLogger(buf, "info")

		l.Info("info message")
		l.Warning("warning message")
		l.Error("error message")

		output := buf.String()
		if !strings.Contains(output, "INFO") || !strings.Contains(output, "WARNING") || !strings.Contains(output, "ERROR") {
			t.Errorf("expected all levels logged, got: %q", output)
		}
	})
}

func TestKeyMasking(t *testing.T) {
	buf := new(bytes.Buffer)
	l := NewLogger(buf, "info")
	l.Mask("my-secret-api-key")

	l.Info("API key is my-secret-api-key inside this log")

	output := buf.String()
	if strings.Contains(output, "my-secret-api-key") {
		t.Errorf("expected key to be masked, got: %q", output)
	}
	if !strings.Contains(output, "[API_KEY_MASKED]") {
		t.Errorf("expected placeholder [API_KEY_MASKED] to be present, got: %q", output)
	}
}

func TestLogLLMRequest(t *testing.T) {
	buf := new(bytes.Buffer)
	l := NewLogger(buf, "info")
	l.Mask("secret-key")

	l.LogLLMRequest("req-123", "gemini", "gemini-2.5-flash", "What is secret-key?", "It is secret.", 150)

	output := buf.String()
	// Check standard elements
	if !strings.Contains(output, "req-123") || !strings.Contains(output, "150ms") {
		t.Errorf("expected telemetry output elements: %q", output)
	}
	// Check prompt and response are logged
	if !strings.Contains(output, "Prompt: What is [API_KEY_MASKED]?") {
		t.Errorf("expected masked prompt, got: %q", output)
	}
	if !strings.Contains(output, "Response: It is secret.") {
		t.Errorf("expected response logged, got: %q", output)
	}
}
