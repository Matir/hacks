# Tasks: Docker API Proxy & Ruleset Recording

**Input**: Design documents from `/specs/001-docker-api-proxy/`
**Prerequisites**: `plan.md`, `spec.md`, `data-model.md`, `research.md`, `quickstart.md`, `contracts/`
**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (`[US1]`, `[US2]`, `[US3]`)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, dependency management, and base directory layout

- [x] T001 Initialize Go module dependencies (`gopkg.in/yaml.v3`) in `go.mod`
- [x] T002 [P] Configure linter rules (`golangci-lint`) in `.golangci.yml`
- [x] T003 [P] Create package directory layout (`cmd/dockerproxy/`, `config/`, `listener/`, `proxy/`, `rules/`, `recorder/`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core socket and logging utilities required before user story proxying can begin

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Define shared domain error types and logging utilities in `config/errors.go`
- [x] T005 Implement socket listener interface and Unix/TCP listener management in `listener/listener.go`
- [x] T006 [P] Write unit tests for socket listener creation and clean shutdown in `listener/listener_test.go`

**Checkpoint**: Foundation ready - user story implementation can now begin in priority order

---

## Phase 3: User Story 1 - Transparent Docker API Proxying over Unix and TCP Sockets (Priority: P1) 🎯 MVP

**Goal**: Establish transparent bidirectional HTTP/REST proxying between Docker clients and daemons across both Unix domain sockets and TCP endpoints without corrupting traffic or breaking connection upgrades.

**Independent Test**: Configure the proxy to listen on a local Unix or TCP socket forwarding to an upstream Docker daemon socket, execute standard client commands (`curl --unix-socket ...`), and confirm responses match direct daemon communication exactly.

### Tests for User Story 1

- [x] T007 [P] [US1] Write co-located unit tests for reverse proxy routing and Unix/TCP transport dialing in `proxy/proxy_test.go`
- [x] T008 [P] [US1] Write end-to-end integration test for transparent Unix and TCP proxying in `tests/integration/proxy_test.go`

### Implementation for User Story 1

- [x] T009 [P] [US1] Define session tracking model `ProxySession` in `proxy/session.go`
- [x] T010 [P] [US1] Implement upstream socket dialer (`http.Transport` supporting Unix domain and TCP sockets) in `proxy/transport.go`
- [x] T011 [US1] Implement core HTTP reverse proxy (`httputil.ReverseProxy` wrapper) with session context tracking in `proxy/proxy.go`
- [x] T012 [US1] Implement HTTP connection upgrade interception (`Connection: Upgrade` / `docker exec` hijacking via `http.Hijacker`) in `proxy/hijack.go`
- [x] T013 [US1] Wire CLI flags (`--listen`, `--upstream`) and initialize reverse proxy server inside main package entrypoint in `cmd/dockerproxy/main.go`

**Checkpoint**: At this point, User Story 1 is fully functional and testable independently as an MVP.

---

## Phase 4: User Story 2 - Policy-Based Request Denial (Priority: P2)

**Goal**: Evaluate incoming Docker API requests against declarative YAML rulesets and immediately deny prohibited operations with an HTTP 403 Forbidden status.

**Independent Test**: Load a denial ruleset (`rules.yaml`), send prohibited requests (e.g. privileged container creation) and allowed requests, and verify prohibited calls receive HTTP 403 while permitted calls succeed.

### Tests for User Story 2

- [x] T014 [P] [US2] Write co-located unit tests for YAML ruleset parsing and rule matching algorithms in `rules/evaluator_test.go` and `config/loader_test.go`
- [x] T015 [P] [US2] Write end-to-end integration test verifying HTTP 403 denial responses and default allow/deny actions in `tests/integration/rules_test.go`

### Implementation for User Story 2

- [x] T016 [P] [US2] Define ruleset models (`Ruleset`, `PolicyRule`, `Action`) in `rules/rule.go`
- [x] T017 [P] [US2] Implement YAML configuration parser adhering to schema `contracts/ruleset.schema.yaml` in `config/loader.go`
- [x] T018 [US2] Implement rule matching engine (HTTP method matching, URI regex matching, body pattern matching, and default action handling) in `rules/evaluator.go`
- [x] T019 [US2] Integrate ruleset evaluator middleware into HTTP reverse proxy pipeline in `proxy/middleware.go`
- [x] T020 [US2] Add `--rules` CLI flag and integrate ruleset loading into entrypoint in `cmd/dockerproxy/main.go`

**Checkpoint**: At this point, User Stories 1 and 2 both work independently and in tandem.

---

## Phase 5: User Story 3 - API Traffic Recording and Inspection (Priority: P3)

**Goal**: Capture complete transaction audit records (timestamps, headers, status codes, and bounded 64KB body snippets) in JSON Lines format (`jsonl`).

**Independent Test**: Enable recording (`--record`), execute client API calls, and inspect the resulting JSONL audit file against `contracts/traffic-record.schema.json`.

### Tests for User Story 3

- [x] T021 [P] [US3] Write contract test verifying recorded JSON Lines records against `contracts/traffic-record.schema.json` in `tests/contract/recorder_test.go`
- [x] T022 [P] [US3] Write end-to-end integration test verifying transaction recording for both allowed and denied requests in `tests/integration/recorder_test.go`

### Implementation for User Story 3

- [x] T023 [P] [US3] Define audit record entity `TrafficRecord` adhering to schema in `recorder/record.go`
- [x] T024 [US3] Implement bounded body buffer (`io.LimitReader` capped at 64KB) and JSON Lines sink writer in `recorder/writer.go`
- [x] T025 [US3] Implement recording middleware wrapping `http.ResponseWriter` and request body inspection in `recorder/middleware.go`
- [x] T026 [US3] Integrate recording middleware into proxy handler pipeline in `proxy/middleware.go`
- [x] T027 [US3] Add `--record` CLI flag and wire recorder sink initialization in `cmd/dockerproxy/main.go`

**Checkpoint**: All three user stories are now fully functional, integrated, and independently verified.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation polish, lint compliance, and end-to-end quickstart verification across all stories

- [x] T028 [P] Add godocs for all exported symbols across `config`, `listener`, `proxy`, `rules`, and `recorder`
- [x] T029 Run `golangci-lint run` and resolve any static analysis warnings across the entire repository
- [x] T030 Execute all validation scenarios documented in `quickstart.md` (`go build -o bin/dockerproxy ./cmd/dockerproxy`) and confirm zero regression

## Phase 7: Convergence

- [x] T031 [P] Define native Docker operation structures and semantic rule models (`SemanticRule`, `ContainerCreateRule`, `ExecCreateRule`, `ResponseFilterRule`, `ActionFilter`) in `rules/rule.go` per FR-005 (missing)
- [x] T032 [P] Update YAML configuration loader and regex pattern validation for `SemanticRule` fields in `config/loader.go` and `config/loader_test.go` per FR-004 (partial)
- [x] T033 [P] Implement semantic request evaluation engine (command category identification, native struct deserialization, and multi-criteria logical AND matching) in `rules/evaluator.go` and `rules/evaluator_test.go` per FR-006 (missing)
- [x] T034 Implement response list filtering middleware (intercepting `GET /containers/json` and `GET /images/json`, evaluating allowlists on unmarshaled items, and writing sanitized JSON) in `proxy/middleware.go` per FR-007 (missing)
- [x] T035 [P] Update end-to-end integration tests verifying semantic `--privileged` container creation denial and list response filtering in `tests/integration/rules_test.go` per Constitution II (missing)
- [x] T036 Run `golangci-lint run` and verify all validation scenarios pass (`go test ./...`, `go build -o bin/dockerproxy ./cmd/dockerproxy`) with zero regression per Constitution I (missing)

## Phase 8: Convergence

- [x] T037 [P] Add official `github.com/moby/moby/api/types` dependencies (`container`, `image`) to `go.mod` and replace custom ad-hoc structs in `rules/rule.go` with references/aliases to canonical Moby API types per FR-005 (contradicts)
- [x] T038 [P] Refactor semantic request evaluation engine in `rules/evaluator.go` and `rules/evaluator_test.go` to deserialize payloads into official `container.Config`, `container.HostConfig`, and `container.ExecCreateRequest` structs per FR-005 (partial)
- [ ] T039 Refactor response list filtering in `proxy/middleware.go` to deserialize and sanitize slices of official `container.Summary` and `image.Summary` types per FR-005 (partial)
- [ ] T040 Run `golangci-lint run` and verify all validation scenarios pass (`go test ./...`, `go build -o bin/dockerproxy ./cmd/dockerproxy`) with zero regression per Constitution I (missing)
