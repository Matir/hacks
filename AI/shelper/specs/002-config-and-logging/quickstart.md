# Quickstart Validation Guide: Config and Logging

This guide details manual validation tests to verify configuration overrides, log silencing, and daemon exit on credential absence.

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

---

## Test Case 2: Silent Logging when LogFile is Empty

Verify that if no log file is specified, no output is printed to stdout or stderr.

### 1. Clear Environment Credentials & TOML Config
Make sure no log file is specified in `shelper.toml` or CLI.

### 2. Run Daemon in Foreground (without logfile)
Start the daemon directly:
```bash
./bin/shelperd --llm-provider=gemini --gemini-api-key="some-key"
```
Verify that:
- The terminal remains silent (no log output is written to stdout/stderr).

---

## Test Case 3: Immediate Exit on Credentials Lack

Verify that if no LLM provider has credentials, the daemon exits immediately with an error.

### 1. Run Daemon with empty configuration/environment
Unset credentials and start the daemon:
```bash
GEMINI_API_KEY="" OPENAI_API_KEY="" ./bin/shelperd --gemini-api-key="" --openai-api-key=""
```
Verify that:
- The command exits immediately with exit code 1.
- An error message is written to standard error: `Error: No LLM provider credentials configured. Daemon cannot start.`
