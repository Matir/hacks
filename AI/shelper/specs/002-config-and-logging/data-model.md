# Data Model: Configuration & Logging Schemas

## Configuration Schema

The configuration entity represents the resolved runtime parameters.

### Fields

| Field Name | Source | Configuration Key | Default Value | Description |
|------------|--------|-------------------|---------------|-------------|
| `LLMProvider` | Flag / TOML / Env | `llm_provider` | `gemini` | The active LLM backend provider (`gemini` or `openai`). |
| `LLMModel` | Flag / TOML / Env | `llm_model` | `gemini-2.5-flash` | The specific model ID to request. |
| `GeminiAPIKey` | Flag / TOML / Env | `gemini_api_key` | None | API credential for Google Gen AI. |
| `OpenAIAPIKey` | Flag / TOML / Env | `openai_api_key` | None | API credential for OpenAI. |
| `LogFile` | Flag / TOML / Env | `logfile` | None | Path to write operational logs. If empty, all logging is disabled (`io.Discard`). |
| `LogLevel` | Flag / TOML / Env | `loglevel` | `info` | Filter for logged events (`info`, `warning`, `error`). |
| `SocketPath` | Flag / Env | N/A | Resolved | Path of the Unix Domain Socket (resolved dynamically). |

---

## Log Telemetry Schema

When logging at `info` level, the payload written to the log destination MUST conform to the following text format containing telemetry and masking.

### Standard Format

```text
[TIMESTAMP] [LEVEL] [EVENT] [METADATA...]
```

### Telemetry Log Format (For LLM Requests)

```text
[TIMESTAMP] INFO LLM Request ID: [ID] | Provider: [PROVIDER] | Model: [MODEL]
Prompt: [PROMPT_CONTENT_MASKED]
Response: [RESPONSE_CONTENT]
Latency: [DELTA_MS]ms
```

### Key Validation & Masking Rules

1. **API Key Masking**: Any logs containing configuration details or error traces must mask API keys to prevent exposure:
   - Format: `[API_KEY_MASKED]` or showing only the first 4 characters.
2. **Log Levels Mapping**:
   - `info`: Logs startup, shutdown, incoming request, prompt, response, latency, and system telemetry.
   - `warning`: Logs failed provider attempts, retry status.
   - `error`: Logs socket binding errors, fatal API failures, syntax parsing issues.
