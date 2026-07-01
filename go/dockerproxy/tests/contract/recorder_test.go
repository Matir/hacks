package contract

import (
	"encoding/json"
	"testing"
	"time"

	"github.com/Matir/hacks/go/dockerproxy/recorder"
)

func TestTrafficRecord_JSONSchemaContract(t *testing.T) {
	rec := recorder.TrafficRecord{
		SessionID:     "test_session_123",
		Timestamp:     time.Now().UTC().Format(time.RFC3339),
		Method:        "GET",
		URI:           "/v1.43/containers/json",
		StatusCode:    200,
		Outcome:       "allowed",
		MatchedRuleID: "default",
	}

	data, err := json.Marshal(rec)
	if err != nil {
		t.Fatalf("unexpected error marshaling TrafficRecord: %v", err)
	}

	var parsed map[string]interface{}
	if err := json.Unmarshal(data, &parsed); err != nil {
		t.Fatalf("unexpected error unmarshaling to map: %v", err)
	}

	requiredFields := []string{
		"session_id",
		"timestamp",
		"method",
		"uri",
		"status_code",
		"outcome",
		"matched_rule_id",
	}

	for _, field := range requiredFields {
		if _, ok := parsed[field]; !ok {
			t.Errorf("contract violation: missing required JSON field %q", field)
		}
	}
}
