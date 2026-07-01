// Package recorder implements bounded traffic recording and JSON Lines audit log formatting.
package recorder

// TrafficRecord defines the JSON structure output for intercepted API transactions.
type TrafficRecord struct {
	SessionID       string              `json:"session_id"`
	Timestamp       string              `json:"timestamp"`
	Method          string              `json:"method"`
	URI             string              `json:"uri"`
	ClientHeaders   map[string][]string `json:"client_headers,omitempty"`
	RequestBody     string              `json:"request_body,omitempty"`
	StatusCode      int                 `json:"status_code"`
	ResponseHeaders map[string][]string `json:"response_headers,omitempty"`
	ResponseBody    string              `json:"response_body,omitempty"`
	Outcome         string              `json:"outcome"`
	MatchedRuleID   string              `json:"matched_rule_id"`
}
