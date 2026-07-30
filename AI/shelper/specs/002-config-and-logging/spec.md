# Feature Specification: Config and Logging

**Feature Branch**: `002-config-and-logging`

**Created**: 2026-07-30

**Status**: Draft

**Input**: User description: "Add configuration options available as both flags in a ~/.config/shelper/shelper.toml: - llm_provider: openai or gemini (default gemini) - llm_model: specific model name (default 3.5-flash) - gemini_api_key: API key for gemini - openai_api_key: API key for OpenAI - logfile: a file to log things to - loglevel: info, warning, error for level of logging. Add logging at major events, particular of failures or significant events. At info level, log every prompt string and response, and include the time delta. If no logfile is specified, do not print any log output at all. If no LLM provider is available due to a lack of credentials, exit immediately."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Unified TOML and CLI Configuration (Priority: P1)

The background daemon should read configuration from a TOML file at `~/.config/shelper/shelper.toml` and CLI flags, merging them with existing environment variables using a clear precedence hierarchy.

**Why this priority**: Core functionality needed to configure the daemon without hardcoding or rely solely on environment variables.

**Independent Test**:
- Create a configuration file at `~/.config/shelper/shelper.toml` specifying a custom default model.
- Launch the daemon with a command-line flag overriding that model.
- Send a request and verify that the provider uses the model specified by the CLI flag (highest precedence).

**Acceptance Scenarios**:

1. **Given** a TOML configuration specifying `llm_provider = "openai"`, **When** the daemon starts without flags, **Then** it initializes and defaults to the OpenAI provider.
2. **Given** a TOML configuration specifying `llm_provider = "openai"`, **When** the daemon starts with CLI flag `--llm-provider=gemini`, **Then** it overrides the TOML file and uses the Gemini provider.
3. **Given** no configuration file or flags, **When** the daemon starts, **Then** it falls back to environment variables (`GEMINI_API_KEY`, etc.) and default compiled values.
4. **Given** no API credentials (API keys) are set in configuration or environment variables, **When** the daemon starts, **Then** it exits immediately with exit code 1.

---

### User Story 2 - Resilient Logging (Priority: P2)

The daemon should log operational events and LLM interaction telemetry to a file specified by `logfile` using the configured `loglevel`. If no `logfile` is specified, all log output must be disabled.

**Why this priority**: Essential for observability, auditing, and troubleshooting daemon performance, while keeping output clean when logging is not desired.

**Independent Test**:
- Start the daemon with `logfile` set to a path and `loglevel` set to `info`.
- Send a request to the socket.
- Inspect the log file and verify it contains the raw prompt string, the LLM response, and the time delta of the request.

**Acceptance Scenarios**:

1. **Given** `loglevel = "info"` and a valid `logfile` path, **When** a request is processed, **Then** the daemon logs the prompt, response, and elapsed time to the file.
2. **Given** `loglevel = "warning"` and a valid `logfile` path, **When** a provider fails but recovers on retry, **Then** the daemon logs a warning showing the retry attempt to the file.
3. **Given** `loglevel = "error"` and a valid `logfile` path, **When** an invalid request comes in, **Then** the daemon logs an error containing the diagnostic code to the file.
4. **Given** no `logfile` is specified, **When** the daemon starts or processes requests, **Then** no log output is written to stdout, stderr, or any files.

---

### Edge Cases

- **Invalid TOML syntax**: If the TOML file contains syntax errors, the daemon should log a warning/error (if logging is enabled) and fallback to defaults/CLI flags instead of crashing.
- **Unwritable log file**: If the path specified by `logfile` cannot be opened or written to, the daemon should log a warning to stderr and fallback to disabling logs or stderr.
- **Malformed log level**: If an invalid log level is provided (e.g. `verbose`), it should default to `info`.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The daemon MUST load configuration from `~/.config/shelper/shelper.toml` if it exists.
- **FR-002**: The daemon MUST support command-line flags for all configuration options: `--llm-provider`, `--llm-model`, `--gemini-key`, `--openai-key`, `--logfile`, `--loglevel`.
- **FR-003**: Configuration precedence MUST follow: CLI Flags > TOML Config > Environment Variables > Defaults.
- **FR-004**: The default LLM provider MUST be `gemini` (mapping to Google Gen AI), and the default model MUST be `gemini-2.5-flash` (or `gemini-1.5-flash` mapping the user's `3.5-flash` default request).
- **FR-005**: If `logfile` is configured, all logs MUST be redirected to that file. If no `logfile` is configured, all logging outputs MUST be disabled.
- **FR-006**: At `info` level, the system MUST log every prompt payload, LLM response output, and execution latency to the logfile.
- **FR-007**: Major daemon lifecycle events (startup, graceful shutdown, socket bind) MUST be logged if logging is enabled.
- **FR-008**: Sensitive API keys MUST be masked or omitted from logs.
- **FR-009**: If no LLM provider has valid credentials (no API keys configured in flags, TOML, or environment), the daemon MUST exit immediately on startup with a non-zero exit status (code 1).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Configuration resolution overhead is minimal, contributing less than 5ms to startup time.
- **SC-002**: The logs generated include the exact duration of each LLM request with millisecond precision.

## Assumptions

- **Config Directory**: The configuration directory `~/.config/shelper` will be created automatically if it doesn't exist.
- **LVM Provider Mapping**: The provider value `gemini` maps to the Google Gen AI provider.
- **Model Name Default**: The default model `3.5-flash` is assumed to refer to `gemini-2.5-flash` for the Google Gen AI provider.
- **TOML Parser**: We will use a standard TOML parsing library in Go (e.g., `github.com/BurntSushi/toml` or `github.com/pelletier/go-toml`).

