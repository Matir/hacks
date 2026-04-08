package audit_test

import (
	"bytes"
	"encoding/json"
	"strings"
	"testing"
	"time"

	"github.com/matir/hacks/go/ghtokenbroker/audit"
	"github.com/matir/hacks/go/ghtokenbroker/config"
)

func TestLogger_AllowEvent(t *testing.T) {
	var buf bytes.Buffer
	l := audit.New(&buf)

	err := l.Log(audit.Event{
		CorrelationID:        "corr-1",
		CallerID:             "agent1",
		Repo:                 "org/repo",
		TaskID:               "task-42",
		RequestedPermissions: config.PermissionSet{"contents": "read"},
		GrantedPermissions:   config.PermissionSet{"contents": "read"},
		Decision:             audit.DecisionAllow,
	})
	if err != nil {
		t.Fatalf("Log returned error: %v", err)
	}

	line := strings.TrimSpace(buf.String())
	var got map[string]interface{}
	if err := json.Unmarshal([]byte(line), &got); err != nil {
		t.Fatalf("output is not valid JSON: %v\noutput: %s", err, line)
	}

	if got["decision"] != "allow" {
		t.Errorf("decision = %v, want allow", got["decision"])
	}
	if got["caller_id"] != "agent1" {
		t.Errorf("caller_id = %v, want agent1", got["caller_id"])
	}
	if got["repo"] != "org/repo" {
		t.Errorf("repo = %v, want org/repo", got["repo"])
	}
	if _, ok := got["token"]; ok {
		t.Error("token field must not appear in audit logs")
	}
}

func TestLogger_DenyEvent(t *testing.T) {
	var buf bytes.Buffer
	l := audit.New(&buf)

	_ = l.Log(audit.Event{
		CorrelationID:        "corr-2",
		CallerID:             "agent2",
		Repo:                 "org/other",
		RequestedPermissions: config.PermissionSet{"contents": "write"},
		Decision:             audit.DecisionDeny,
		Reason:               "repo not allowed",
	})

	var got map[string]interface{}
	if err := json.Unmarshal([]byte(strings.TrimSpace(buf.String())), &got); err != nil {
		t.Fatalf("invalid JSON: %v", err)
	}
	if got["decision"] != "deny" {
		t.Errorf("decision = %v, want deny", got["decision"])
	}
	if got["reason"] != "repo not allowed" {
		t.Errorf("reason = %v, want 'repo not allowed'", got["reason"])
	}
}

func TestLogger_TimestampFilled(t *testing.T) {
	var buf bytes.Buffer
	l := audit.New(&buf)
	before := time.Now().UTC()
	_ = l.Log(audit.Event{Decision: audit.DecisionAllow})
	after := time.Now().UTC()

	var got map[string]interface{}
	_ = json.Unmarshal([]byte(strings.TrimSpace(buf.String())), &got)

	tsStr, _ := got["timestamp"].(string)
	ts, err := time.Parse(time.RFC3339Nano, tsStr)
	if err != nil {
		t.Fatalf("timestamp parse error: %v", err)
	}
	if ts.Before(before) || ts.After(after) {
		t.Errorf("timestamp %v outside expected range [%v, %v]", ts, before, after)
	}
}

func TestLogger_NoTokenInGrantedPermissions(t *testing.T) {
	var buf bytes.Buffer
	l := audit.New(&buf)
	_ = l.Log(audit.Event{
		Decision:           audit.DecisionAllow,
		GrantedPermissions: config.PermissionSet{"contents": "write"},
	})

	output := buf.String()
	if strings.Contains(output, "ghp_") || strings.Contains(output, "ghs_") {
		t.Error("token value must not appear in audit log")
	}
}
