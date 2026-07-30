package contract

import (
	"encoding/json"
	"shelper/daemon"
	"testing"
)

func TestNDJSONSerialization(t *testing.T) {
	t.Run("Valid SocketRequest serialization", func(t *testing.T) {
		reqJSON := `{"id":"req-001","type":"request","provider":"google","model":"gemini-2.5-flash","input":"list files","variables":{"shell":"zsh"}}`
		var req daemon.SocketRequest
		err := json.Unmarshal([]byte(reqJSON), &req)
		if err != nil {
			t.Fatalf("unmarshal error: %v", err)
		}
		if req.ID != "req-001" || req.Type != "request" || req.Provider != "google" || req.Model != "gemini-2.5-flash" || req.Input != "list files" {
			t.Errorf("request unmarshal mismatch: %+v", req)
		}
		if req.Variables["shell"] != "zsh" {
			t.Errorf("expected variables.shell to be 'zsh'")
		}
	})

	t.Run("Valid SocketResponse serialization", func(t *testing.T) {
		resp := daemon.SocketResponse{
			ID:     "req-001",
			Status: "success",
			Output: "ls -la",
			Metadata: daemon.ResponseMetadata{
				Provider:       "openai",
				Model:          "gpt-4o",
				LatencyMs:      150,
				TemplateSource: "bundled",
			},
		}
		data, err := json.Marshal(resp)
		if err != nil {
			t.Fatalf("marshal error: %v", err)
		}

		var got map[string]interface{}
		if err := json.Unmarshal(data, &got); err != nil {
			t.Fatalf("unmarshal map error: %v", err)
		}
		if got["id"] != "req-001" || got["status"] != "success" || got["output"] != "ls -la" {
			t.Errorf("response marshal mismatch: %s", string(data))
		}

		meta, ok := got["metadata"].(map[string]interface{})
		if !ok {
			t.Fatalf("missing metadata sub-struct")
		}
		if meta["provider"] != "openai" || meta["model"] != "gpt-4o" || meta["latency_ms"].(float64) != 150 {
			t.Errorf("metadata marshal mismatch: %+v", meta)
		}
	})

	t.Run("Error SocketResponse serialization", func(t *testing.T) {
		resp := daemon.SocketResponse{
			ID:     "req-002",
			Status: "error",
			Error: &daemon.ResponseError{
				Code:    "INVALID_REQUEST",
				Message: "Missing input field",
				Details: "The field 'input' was empty or invalid",
			},
		}

		data, err := json.Marshal(resp)
		if err != nil {
			t.Fatalf("marshal error: %v", err)
		}

		var got map[string]interface{}
		if err := json.Unmarshal(data, &got); err != nil {
			t.Fatalf("unmarshal error: %v", err)
		}

		if got["status"] != "error" || got["id"] != "req-002" {
			t.Errorf("unexpected outer structure: %s", string(data))
		}

		errObj, ok := got["error"].(map[string]interface{})
		if !ok {
			t.Fatalf("missing error object field")
		}

		if errObj["code"] != "INVALID_REQUEST" || errObj["message"] != "Missing input field" {
			t.Errorf("unexpected error payload: %+v", errObj)
		}
	})
}

