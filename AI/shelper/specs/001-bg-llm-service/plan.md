# Implementation Plan: Background LLM Processing Service

**Branch**: `001-bg-llm-service` | **Date**: 2026-07-30 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-bg-llm-service/spec.md`

## Summary

Build a background daemon application (`shelperd`) written in Golang that listens for client request messages over a Unix Domain Socket, and interactive shell line editor integration scripts (`shell/shelper.bash` and `shell/shelper.zsh`). The daemon parses NDJSON payloads, resolves and executes prompt templates with shell context metadata (`$HOME/.config/shelper/prompt.md` with an embedded fallback), dispatches formatted prompts to an LLM provider via a modular Go `Provider` interface (supporting Google Gen AI and OpenAI Go SDKs), and returns structured JSON responses back to the socket. The shell widgets capture line buffer input (`READLINE_LINE` / `$BUFFER`) upon pressing `Ctrl+X Ctrl+E`, transmit the prompt and shell name (`bash`/`zsh`) over the socket, and replace the buffer line with the generated command.

## Technical Context

**Language/Version**: Go 1.22+, POSIX Shell / Bash 4.0+ / Zsh 5.0+

**Primary Dependencies**:
- Google Gen AI Go SDK (`google.golang.org/genai`)
- OpenAI Go SDK (`github.com/openai/openai-go`)

**Storage**: Local filesystem (`$HOME/.config/shelper/prompt.md`, Unix domain socket binding)

**Testing**: Standard Go `testing` framework (`go test ./...`) for backend daemon, unit/contract tests, and shell widget integration tests

**Target Platform**: Linux / POSIX systems (Bash / Zsh shells)

**Project Type**: CLI / Background daemon service + Shell integration scripts

**Performance Goals**:
- <50ms socket request connection & acknowledgment
- <10ms prompt formatting execution latency
- <1s shell line buffer capture & replacement roundtrip (excluding LLM network call)
- Support 20+ concurrent request workers without memory leakage or blocking

**Constraints**:
- Unix Domain Socket path resolution order:
  1. `$SHELPER_SOCK`
  2. `${XDG_RUNTIME_DIR}/shelper.sock`
  3. `${TMPDIR}/shelper.${UID}.sock` (defaulting to `/tmp/shelper.${UID}.sock` if unset)
- Support modular provider interface (`llm.Provider`) for vendor pluggability
- Non-blocking, non-destructive line buffer manipulation in Readline/ZLE line editors

**Scale/Scope**: Local IPC service daemon for terminal assistant workflows and prompt line interactions

## Constitution Check

*GATE: Passed prior to Phase 0 research. Re-evaluated post-Phase 1 design.*

| Constitution Principle | Status | Compliance Verification Strategy |
|------------------------|--------|----------------------------------|
| **I. Code Quality** | PASSED | Modular package structure (`daemon`, `llm`, `prompt`). Clean Go interface boundaries and typed models. Dedicated shell integration scripts in `shell/`. |
| **II. Testing Standards** | PASSED | Comprehensive unit tests for prompt template resolution, contract testing for socket API NDJSON serialization, and shell widget execution tests. |
| **III. User Experience Consistency** | PASSED | Seamless `Ctrl+X Ctrl+E` key binding across Bash and Zsh line editors. Consistent JSON request/response schema with structured error codes (`INVALID_REQUEST`, `PROVIDER_ERROR`, `TEMPLATE_ERROR`). |
| **IV. Performance Requirements** | PASSED | High-efficiency Unix socket stream handling, low memory overhead, asynchronous worker pool processing. |

## Project Structure

### Documentation (this feature)

```text
specs/001-bg-llm-service/
├── spec.md              # Feature specification
├── plan.md              # Implementation plan
├── research.md          # Phase 0 technical research & choices
├── data-model.md        # Phase 1 data model & state diagrams
├── quickstart.md        # Phase 1 verification & test guide
└── contracts/           # Phase 1 API schemas & contracts
    ├── socket-api.json  # NDJSON IPC protocol schema
    ├── provider-interface.go # Go LLM Provider interface contract
    └── shell-integration.md  # Shell line editor widget contract
```

### Source Code Structure

```text
cmd/
└── shelperd/
    └── main.go          # CLI entry point for background daemon

config/              # Configuration loading & socket path resolution
├── config.go
└── config_test.go
daemon/              # Unix Domain Socket listener & connection worker pool
├── listener.go
├── worker.go
└── daemon_test.go
llm/                 # Modular LLM provider abstractions & SDK clients
├── provider.go      # Provider interface definition
├── google.go        # Google Gen AI Go SDK integration
├── openai.go        # OpenAI Go SDK integration
├── registry.go      # Provider factory registry
└── llm_test.go
prompt/              # Prompt template resolution & formatting
├── template.go      # Loader & text/template execution
├── prompt.md        # Embedded default prompt template (//go:embed)
└── prompt_test.go

shell/                   # Shell line editor integration scripts
├── shelper.bash         # Bash Readline widget script (bind -x '\C-xe')
└── shelper.zsh          # Zsh ZLE widget script (bindkey '^X^E')

tests/
├── contract/            # Socket NDJSON API schema tests
└── integration/         # End-to-end socket request & shell widget tests
```

**Structure Decision**: Selected Go layout with `cmd/` for daemon entry point, root-level module packages (`config`, `daemon`, `llm`, `prompt`), and a dedicated `shell/` directory for Bash and Zsh line editor integration scripts.

## Complexity Tracking

*No constitution violations. Zero unjustified complexity.*
