# Quickstart Validation Guide: Config and Logging

This guide details manual validation tests to verify that configuration precedence (CLI > TOML > Env > Default) and logging level behaviors are functioning correctly.

## Prerequisites

- Built `shelperd` daemon binary.
- Installed `socat` for sending requests.
- Configuration directory created: `~/.config/shelper/`.

---

## Test Case 1: Configuration Resolution & Precedence

Verify that the CLI flags override TOML configurations.

### 1. Set up TOML Configuration
Write a TOML file at `~/.config/shelper/shelper.toml`:

```toml
llm_provider = "openai"
llm_model = "gpt-4o-mini"
logfile = "/tmp/toml-shelper.log"
loglevel = "warning"
```

### 2. Start Daemon with CLI Overrides
Launch the daemon with command-line flags overriding the provider and log level:

```bash
./bin/shelperd --llm-provider=gemini --loglevel=info --logfile=/tmp/cli-shelper.log
```

### 3. Verify Active Configurations
- Check that the daemon creates the log file at `/tmp/cli-shelper.log` (CLI override) instead of `/tmp/toml-shelper.log` (TOML value).
- Query the daemon status endpoint:
  ```bash
  echo '{"type":"status"}' | socat - UNIX-CONNECT:/run/user/$(id -u)/shelper.sock
  ```
- Inspect the log file `/tmp/cli-shelper.log` and verify it contains logs at `info` level (e.g. startup logs, status request logs).

---

## Test Case 2: Request Telemetry Logging

Verify that at `info` level, prompts, responses, and latencies are successfully logged.

### 1. Send processing request
Send a processing request:
```bash
echo '{"id":"req-telemetry","input":"print hello world in python"}' | socat - UNIX-CONNECT:/run/user/$(id -u)/shelper.sock
```

### 2. Inspect Log File
Verify that the log file contains the request telemetry, including:
- The raw prompt string.
- The returned LLM response.
- The latency time delta.

Example expected log:
```text
2026/07/30 11:15:20 INFO LLM Request ID: req-telemetry | Provider: gemini | Model: gemini-2.5-flash
Prompt: print hello world in python
Response: print("Hello, World!")
Latency: 245ms
```
