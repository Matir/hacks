package audit

import (
	"encoding/json"
	"fmt"
	"io"
	"time"

	"github.com/matir/hacks/go/ghtokenbroker/config"
)

// Decision indicates whether a token request was allowed or denied.
type Decision string

const (
	DecisionAllow Decision = "allow"
	DecisionDeny  Decision = "deny"
)

// Event records a single token request decision. Token values must never appear
// in this struct.
type Event struct {
	Timestamp            time.Time            `json:"timestamp"`
	CorrelationID        string               `json:"correlation_id"`
	CallerID             string               `json:"caller_id"`
	Repo                 string               `json:"repo"`
	TaskID               string               `json:"task_id,omitempty"`
	Purpose              string               `json:"purpose,omitempty"`
	RequestedPermissions config.PermissionSet `json:"requested_permissions"`
	GrantedPermissions   config.PermissionSet `json:"granted_permissions,omitempty"`
	Decision             Decision             `json:"decision"`
	Reason               string               `json:"reason,omitempty"`
}

// Logger writes audit events as newline-delimited JSON to an io.Writer.
type Logger struct {
	w io.Writer
}

// New returns a Logger that writes to w.
func New(w io.Writer) *Logger {
	return &Logger{w: w}
}

// Log serialises event as a single JSON line. Errors are non-fatal; the broker
// should not fail a request because of a log write failure, but callers may
// inspect the error for monitoring purposes.
func (l *Logger) Log(event Event) error {
	if event.Timestamp.IsZero() {
		event.Timestamp = time.Now().UTC()
	}
	data, err := json.Marshal(event)
	if err != nil {
		return fmt.Errorf("audit: marshal event: %w", err)
	}
	data = append(data, '\n')
	_, err = l.w.Write(data)
	return err
}
