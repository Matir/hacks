# Tasks: Background LLM Processing Service

**Input**: Design documents from `/specs/001-bg-llm-service/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Explicit file paths included in all task descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic directory structure

- [x] T001 Initialize Go module and directory structure (`cmd/shelperd`, `config`, `daemon`, `llm`, `prompt`, `shell/`, `tests/contract`, `tests/integration`) in `go.mod`
- [x] T002 [P] Add Go SDK dependencies (`google.golang.org/genai`, `github.com/openai/openai-go`) in `go.mod`
- [x] T003 [P] Add embedded default prompt template file in `prompt/prompt.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Implement socket path resolution logic (`$SHELPER_SOCK` -> `${XDG_RUNTIME_DIR}/shelper.sock` -> `${TMPDIR}/shelper.${UID}.sock`) in `config/config.go`
- [x] T005 [P] Unit tests for config loading and socket path resolution in `config/config_test.go`
- [x] T006 Implement LLM Provider interface definition and request/response models in `llm/provider.go`
- [x] T007 Implement LLM Provider factory registry in `llm/registry.go`
- [x] T008 [P] Implement IPC SocketRequest and SocketResponse data models in `daemon/types.go`

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Process Background Request with Prompt Formatting (Priority: P1) 🎯 MVP

**Goal**: Accept incoming NDJSON requests over Unix socket, format prompts using `$HOME/.config/shelper/prompt.md` (or embedded fallback), call target LLM provider, and return completion response.

**Independent Test**: Start daemon, send NDJSON request over Unix socket using `socat` or client code, verify formatted prompt execution and structured JSON completion response.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T009 [P] [US1] Unit test for prompt template loading and variable substitution in `prompt/prompt_test.go`
- [x] T010 [P] [US1] Unit tests for LLM provider interface and factory registry in `llm/llm_test.go`
- [x] T011 [P] [US1] Contract test for socket NDJSON request/response serialization in `tests/contract/socket_api_test.go`

### Implementation for User Story 1

- [x] T012 [US1] Implement prompt template loader with file override (`$HOME/.config/shelper/prompt.md`) and embedded fallback (`//go:embed`) in `prompt/template.go`
- [x] T013 [P] [US1] Implement Google Gen AI SDK provider client wrapper (`google.golang.org/genai`) in `llm/google.go`
- [x] T014 [P] [US1] Implement OpenAI SDK provider client wrapper (`github.com/openai/openai-go`) in `llm/openai.go`
- [x] T015 [US1] Implement Unix domain socket listener and connection worker dispatch in `daemon/listener.go`
- [x] T016 [US1] Implement NDJSON request handler worker logic combining template formatting and LLM provider invocation in `daemon/worker.go`
- [x] T017 [US1] Implement main entry point for background daemon CLI in `cmd/shelperd/main.go`
- [x] T018 [US1] Integration test for end-to-end socket request processing in `tests/integration/socket_integration_test.go`

**Checkpoint**: At this point, User Story 1 is fully functional and testable independently (MVP ready!)

---

## Phase 4: User Story 2 - Interactive Shell Line Editor Integration (Priority: P2)

**Goal**: Shell integration function bound to `Ctrl+X Ctrl+E` capturing current line editor buffer (`READLINE_LINE` / `$BUFFER`), sending text + shell name (`bash`/`zsh`) over Unix socket, and updating the line buffer with the returned command.

**Independent Test**: Source `shell/shelper.bash` or `shell/shelper.zsh`, type prompt in command line, press `Ctrl+X Ctrl+E`, and verify buffer updates to returned command output.

### Tests for User Story 2

- [x] T019 [P] [US2] Contract test for shell widget payload formatting and variable injection in `tests/contract/shell_integration_test.go`

### Implementation for User Story 2

- [x] T020 [P] [US2] Implement Bash Readline widget integration script (`_shelper_cmd_widget` & `bind -x '"\C-xe"'`) in `shell/shelper.bash`
- [x] T021 [P] [US2] Implement Zsh ZLE widget integration script (`_shelper_cmd_widget` & `bindkey '^X^E'`) in `shell/shelper.zsh`
- [x] T022 [US2] Integration test for interactive shell line editor buffer capture and insertion in `tests/integration/shell_widget_integration_test.sh`

**Checkpoint**: Interactive shell line editor integration works seamlessly in Bash and Zsh

---

## Phase 5: User Story 3 - Health and Status Monitoring of Background Daemon (Priority: P2)

**Goal**: Query status, uptime, worker counts, and active connections over Unix domain socket.

**Independent Test**: Issue status request over socket, verify active daemon status, worker metrics, and graceful shutdown behavior.

### Tests for User Story 3

- [x] T023 [P] [US3] Unit test for daemon status collector and metrics reporting in `daemon/daemon_test.go`

### Implementation for User Story 3

- [x] T024 [US3] Implement health and status query handler in `daemon/worker.go`
- [x] T025 [US3] Add graceful shutdown signal handling and cleanup in `cmd/shelperd/main.go`
- [x] T026 [US3] Integration test verifying health status response and graceful shutdown in `tests/integration/socket_integration_test.go`

**Checkpoint**: User Stories 1, 2, and 3 work independently and predictably

---

## Phase 6: User Story 4 - Error Handling & Resilient Recovery (Priority: P3)

**Goal**: Return structured diagnostic error codes (`INVALID_REQUEST`, `PROVIDER_ERROR`, `TEMPLATE_ERROR`), payload validation, and retry handling for provider timeouts.

**Independent Test**: Send malformed payload or simulate upstream LLM failure, assert structured error response returned.

### Tests for User Story 4

- [x] T027 [P] [US4] Unit test for payload validation and error formatting in `daemon/worker_test.go`

### Implementation for User Story 4

- [x] T028 [US4] Implement request payload validation rules in `daemon/types.go`
- [x] T029 [US4] Implement retry handling and error mapping for provider failures in `llm/registry.go`
- [x] T030 [US4] Integration test verifying structured error responses for invalid inputs and API failures in `tests/integration/socket_integration_test.go`

**Checkpoint**: All user stories are independently functional and resilient

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, static analysis, and end-to-end verification

- [x] T031 [P] Update project usage documentation and shell installation instructions in `README.md`
- [x] T032 [P] Run linter and static code analysis (`golangci-lint run ./...`)
- [x] T033 Run end-to-end quickstart validation per `specs/001-bg-llm-service/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
- **Polish (Phase 7)**: Depends on completion of target user stories

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Client-side shell scripts interacting with socket
- **User Story 3 (P2)**: Can start after Foundational (Phase 2) - Extends worker state reporting
- **User Story 4 (P3)**: Can start after Foundational (Phase 2) - Enhances worker validation and registry error handling

---

## Parallel Execution Opportunities

```bash
# User Story 2 Parallel Tasks:
Task: "T019 [P] [US2] Contract test for shell widget in tests/contract/shell_integration_test.go"
Task: "T020 [P] [US2] Implement Bash Readline widget script in shell/shelper.bash"
Task: "T021 [P] [US2] Implement Zsh ZLE widget script in shell/shelper.zsh"
```
