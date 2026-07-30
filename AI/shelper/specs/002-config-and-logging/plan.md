# Implementation Plan: Config and Logging

**Branch**: `002-config-and-logging` | **Date**: 2026-07-30 | **Spec**: [specs/002-config-and-logging/spec.md](file:///usr/local/google/home/davidtomaschik/Personal/hacks/AI/shelper/specs/002-config-and-logging/spec.md)

**Input**: Feature specification from `specs/002-config-and-logging/spec.md`

## Summary

This feature introduces a unified configuration system (supporting CLI flags and a `shelper.toml` configuration file) and an observability logging engine. We will extend `config/config.go` to parse the TOML file and CLI flags, merging them with environment variables using strict precedence.
Additionally:
- If no logfile is specified, all log output will be disabled (no stdout/stderr logs).
- If no LLM provider is successfully initialized due to lack of credentials (missing API keys), the daemon will exit immediately on startup.

## Technical Context

**Language/Version**: Go 1.22+

**Primary Dependencies**: `github.com/BurntSushi/toml` (for parsing the TOML configuration file)

**Storage**: Configuration file at `~/.config/shelper/shelper.toml`, and log file outputs as configured.

**Testing**: Go unit tests (using `testing` package) and integration socket tests.

**Target Platform**: Linux

**Project Type**: CLI / Background Daemon

**Performance Goals**: Configuration load overhead under 5ms, logging latency under 1ms.

**Constraints**:
- Precedence order MUST be: CLI flags > TOML File > Environment variables > Defaults.
- If `logfile` is empty, logging is disabled (no fallback to stdout/stderr).
- If both Google/OpenAI providers fail to initialize because of credentials, exit immediately.

**Scale/Scope**: Local developer tool.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Code Quality Gate**: Configuration parsing must be modular and testable. Do not leak TOML parsing details directly into the `main` package.
- **Testing Standards Gate**: The precedence merger logic must be covered by comprehensive unit tests asserting all combination options.
- **User Experience Gate**: All CLI flags must have user-friendly descriptions available via `--help`. Invalid configurations must return clean actionable error logs.
- **Performance Gate**: Log writing must be asynchronous or highly efficient to prevent blocking the socket request processing pipeline.

## Project Structure

### Documentation

```text
specs/002-config-and-logging/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── contracts/           # Phase 1 output (empty or N/A)
```

### Source Code

```text
cmd/shelperd/
└── main.go              # Entrypoint updated to load flags, initialize logger, and check credentials on startup

config/
├── config.go            # Updated to support TOML parsing, CLI flag parsing, and merging
└── config_test.go       # Updated to verify config precedence logic

daemon/
├── listener.go          # Updated to receive logging instance
├── worker.go            # Updated to log prompt, response, and elapsed time details

log/                     # New package for structured logging
├── logger.go            # Structured logger implementation (supports disabling logging if writer is nil/empty)
└── logger_test.go       # Logger unit tests
```

**Structure Decision**: Single project layout, extending `config` module and adding a dedicated `log` module to handle log writing.
