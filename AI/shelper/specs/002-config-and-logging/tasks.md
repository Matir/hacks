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

## Phase 3: User Story 1 - Unified TOML and CLI Configuration (Priority: P1) 🎯 MVP

**Goal**: Load configuration from CLI flags, TOML config, and environment variables following strict precedence rules.

**Independent Test**: Verify that CLI flags override TOML configurations, which override environment variables in `config/config_test.go`.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T005 [P] [US1] Test configuration precedence merging in `config/config_test.go`

### Implementation for User Story 1

- [x] T006 [US1] Add TOML file configuration parsing in `config/config.go`
- [x] T007 [US1] Implement CLI flag binding and dynamic default merging in `config/config.go`

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Resilient Logging (Priority: P2)

**Goal**: Log system telemetry, request prompts, LLM responses, and latencies using specified level and output.

**Independent Test**: Verify log output contains correct formats and latencies.

### Tests for User Story 2

- [x] T008 [P] [US2] Test telemetry logging format and file creation in `tests/integration/socket_integration_test.go`

### Implementation for User Story 2

- [x] T009 [US2] Initialize logger instance in `cmd/shelperd/main.go`
- [x] T010 [US2] Integrate logger and log lifecycle events in `daemon/listener.go`
- [x] T011 [US2] Log request payloads, responses, and latencies in `daemon/worker.go`

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Documentation updates and static analysis verification.

- [x] T012 [P] Document TOML configuration and CLI usage in `README.md`
- [x] T013 [P] Verify code quality with `go vet ./...`
- [x] T014 Run quickstart.md validation guide in `specs/002-config-and-logging/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - May integrate with US1 but should be independently testable

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- All tests for a user story marked [P] can run in parallel
- Models within a story marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# Run tests for configuration precedence setup
Task: "Test configuration precedence merging in config/config_test.go"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Each story adds value without breaking previous stories
