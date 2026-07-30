package daemon

// SocketRequest represents an incoming client NDJSON payload.
type SocketRequest struct {
	ID          string            `json:"id,omitempty"`
	Type        string            `json:"type,omitempty"` // "request" (default) or "status"
	Provider    string            `json:"provider,omitempty"`
	Model       string            `json:"model,omitempty"`
	Input       string            `json:"input"`
	Template    string            `json:"template,omitempty"`
	Variables   map[string]string `json:"variables,omitempty"`
	Temperature *float64          `json:"temperature,omitempty"`
}

// ResponseError details error diagnostic context.
type ResponseError struct {
	Code    string `json:"code"`
	Message string `json:"message"`
	Details string `json:"details,omitempty"`
}

// ResponseMetadata records execution statistics and provider information.
type ResponseMetadata struct {
	Provider       string `json:"provider"`
	Model          string `json:"model"`
	LatencyMs      int64  `json:"latency_ms"`
	TemplateSource string `json:"template_source"`
}

// SocketResponse represents the outgoing NDJSON payload sent to the client.
type SocketResponse struct {
	ID       string           `json:"id"`
	Status   string           `json:"status"` // "success" or "error"
	Output   string           `json:"output,omitempty"`
	Error    *ResponseError   `json:"error,omitempty"`
	Metadata ResponseMetadata `json:"metadata"`
}
