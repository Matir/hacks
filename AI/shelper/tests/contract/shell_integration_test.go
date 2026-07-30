package contract

import (
	"encoding/json"
	"shelper/daemon"
	"testing"
)

func TestShellWidgetPayload(t *testing.T) {
	t.Run("Bash Widget Payload Injection", func(t *testing.T) {
		req := daemon.SocketRequest{
			Input: "list files",
			Variables: map[string]string{
				"shell": "bash",
			},
		}

		data, err := json.Marshal(req)
		if err != nil {
			t.Fatalf("failed to marshal: %v", err)
		}

		var parsed map[string]interface{}
		if err := json.Unmarshal(data, &parsed); err != nil {
			t.Fatalf("failed to unmarshal: %v", err)
		}

		vars, ok := parsed["variables"].(map[string]interface{})
		if !ok {
			t.Fatalf("variables field is missing or not a map")
		}

		if vars["shell"] != "bash" {
			t.Errorf("expected variables.shell to be 'bash', got %q", vars["shell"])
		}
	})

	t.Run("Zsh Widget Payload Injection", func(t *testing.T) {
		req := daemon.SocketRequest{
			Input: "list files",
			Variables: map[string]string{
				"shell": "zsh",
			},
		}

		data, err := json.Marshal(req)
		if err != nil {
			t.Fatalf("failed to marshal: %v", err)
		}

		var parsed map[string]interface{}
		if err := json.Unmarshal(data, &parsed); err != nil {
			t.Fatalf("failed to unmarshal: %v", err)
		}

		vars, ok := parsed["variables"].(map[string]interface{})
		if !ok {
			t.Fatalf("variables field is missing or not a map")
		}

		if vars["shell"] != "zsh" {
			t.Errorf("expected variables.shell to be 'zsh', got %q", vars["shell"])
		}
	})

	t.Run("Fish Widget Payload Injection", func(t *testing.T) {
		req := daemon.SocketRequest{
			Input: "list files",
			Variables: map[string]string{
				"shell": "fish",
			},
		}

		data, err := json.Marshal(req)
		if err != nil {
			t.Fatalf("failed to marshal: %v", err)
		}

		var parsed map[string]interface{}
		if err := json.Unmarshal(data, &parsed); err != nil {
			t.Fatalf("failed to unmarshal: %v", err)
		}

		vars, ok := parsed["variables"].(map[string]interface{})
		if !ok {
			t.Fatalf("variables field is missing or not a map")
		}

		if vars["shell"] != "fish" {
			t.Errorf("expected variables.shell to be 'fish', got %q", vars["shell"])
		}
	})
}
