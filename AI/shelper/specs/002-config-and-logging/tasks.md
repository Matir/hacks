# Tasks: Config and Logging

**Input**: Design documents from `/specs/002-config-and-logging/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: Included as required for regression and precedence merging verification.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Add TOML parser dependency github.com/BurntSushi/toml in `go.mod`
- [x] T002 Run `go mod tidy` in repository root

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 [P] Implement logging levels and key masking in `log/logger.go`
- [x] T004 [P] Test logging levels and key masking in `log/logger_test.go`

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Unified TOML and CLI Configuration & Credentials Check (Priority: P1) 🎯 MVP

**Goal**: Load configuration from CLI flags, TOML config, and environment variables following strict precedence rules. Exit immediately if no credentials are configured on startup.

**Independent Test**: Verify configuration precedence in `config/config_test.go` and verify daemon exits when credentials are missing.

### Tests for User Story 1

- [x] T005 [P] [US1] Test configuration precedence merging in `config/config_test.go`
- [x] T015 [P] [US1] Test that daemon exits immediately on lack of provider credentials in `tests/integration/socket_integration_test.go`

### Implementation for User Story 1

- [x] T006 [US1] Add TOML file configuration parsing in `config/config.go`
- [x] T007 [US1] Implement CLI flag binding and dynamic default merging in `config/config.go`
- [x] T017 [US1] Exit immediately on startup if no provider is registered due to lack of credentials in `cmd/shelperd/main.go`

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Resilient & Silent Logging (Priority: P2)

**Goal**: Log system telemetry to configured file, and completely disable all logs (stdout/stderr) if logfile is empty.

**Independent Test**: Verify log output is silenced when logfile is empty.

### Tests for User Story 2

- [x] T008 [P] [US2] Test telemetry logging format and file creation in `tests/integration/socket_integration_test.go`
- [x] T016 [P] [US2] Test that empty logfile disables logging output in `tests/integration/socket_integration_test.go`

### Implementation for User Story 2

- [x] T009 [US2] Initialize logger instance in `cmd/shelperd/main.go`
- [x] T010 [US2] Integrate logger and log lifecycle events in `daemon/listener.go`
- [x] T011 [US2] Log request payloads, responses, and latencies in `daemon/worker.go`
- [x] T018 [US2] Update logger initialization in `cmd/shelperd/main.go` to use io.Discard when logfile is empty.

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Documentation updates and static analysis verification.

- [x] T012 [P] Document TOML configuration and CLI usage in `README.md`
- [x] T013 [P] Verify code quality with `go vet ./...`
- [x] T014 Run quickstart.md validation guide in `specs/002-config-and-logging/quickstart.md`
- [x] T019 Run updated quickstart.md validation guide in `specs/002-config-and-logging/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
- **Polish (Final Phase)**: Depends on all desired user stories being complete
