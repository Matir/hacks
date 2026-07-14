# Implementation Plan: Docker API Proxy with Semantic Ruleset Evaluation & Recording

**Branch**: `001-docker-api-proxy` | **Date**: 2026-07-01 | **Spec**: [spec.md](file:///Users/davidtomaschik/Personal/hacks/go/dockerproxy/specs/001-docker-api-proxy/spec.md)

**Input**: Feature specification from `/specs/001-docker-api-proxy/spec.md`

## Summary

Build a standalone, modular Go CLI utility that proxies bidirectional HTTP/REST connections between Docker clients and upstream Docker daemons over Unix domain sockets and TCP endpoints. The application evaluates incoming non-streaming API requests and list responses against declarative YAML semantic policy rulesets (`SemanticRule`). By deserializing operational payloads directly into official canonical Docker message types (`container.CreateRequest`, `container.ExecCreateRequest`, `container.Summary`, `image.Summary` from `github.com/moby/moby/api/types`), the proxy enforces granular per-operation assertions (such as blocking `--privileged` containers, unauthorized mount destinations, or unlisted port forwards) and transparently filters container/image lists returned to multi-tenant clients. When enabled, it captures structured transaction logs in JSON Lines format (`jsonl`). The architecture maintains strict separation between interface components (`cmd`, `config`, `listener`) and core processing engines (`proxy`, `rules`, `recorder`).

## Technical Context

**Language/Version**: Go 1.22+

**Primary Dependencies**: `github.com/moby/moby/api/types/container`, `github.com/moby/moby/api/types/image` (official Docker Engine API types), `gopkg.in/yaml.v3` (declarative YAML ruleset parsing), Go standard library (`encoding/json`, `net`, `net/http`, `net/http/httputil`, `context`, `io`, `regexp`)

**Storage**: File-based ruleset configuration files (YAML v3) and structured transaction audit sinks (JSON Lines format to file or stdout)

**Testing**: Go standard testing package (`testing`), `net/http/httptest`, and `golangci-lint`

**Target Platform**: Linux and macOS (supporting Unix domain sockets and TCP endpoints)

**Project Type**: CLI tool & daemon proxy application

**Performance Goals**: <10ms latency overhead per proxied request under standard load

**Constraints**: Strict architectural decoupling between presentation/interface layers and proxy/policy engines; memory usage strictly bounded (<64KB per payload recording buffer); non-streaming operational payloads deserialized cleanly into canonical Moby API structs

**Scale/Scope**: Support concurrent Docker client sessions, interactive hijacked streams (`docker exec -it`), and large chunked transfers safely without socket leaks or memory exhaustion

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Constitutional Principle | Alignment Status & Verification Gate |
| :--- | :--- |
| **I. Code Quality & Maintainability** | ✅ **Pass**: Enforces strict package separation (`cmd`, root packages), zero-warning `golangci-lint` compliance, explicit error propagation without silent discards, and self-documenting godocs. |
| **II. Testing Standards & Discipline** | ✅ **Pass**: Mandates test-first verification using standard `testing` and `httptest` packages. Unit tests will cover semantic payload deserialization, multi-criteria rule matching algorithms, response array filtering, and socket listeners; integration contract tests will verify end-to-end proxying and HTTP 403 denial responses. |
| **III. User Experience (UX) Consistency** | ✅ **Pass**: Uniform CLI flag naming (`--listen`, `--upstream`, `--rules`, `--record`), structured actionable diagnostic error messages, and predictable YAML configuration schema. |
| **IV. Performance & Efficiency** | ✅ **Pass**: Uses Go's native `httputil.ReverseProxy` and `net.Listener` for minimal routing overhead. Deserialization is applied strictly to non-streaming operational payloads; large streaming bodies bypass unmarshaling. Bounded 64KB payload buffers (`io.LimitReader`) and explicit `context.Context` cancellation prevent goroutine/memory leaks. |

## Project Structure

### Documentation (this feature)

```text
specs/001-docker-api-proxy/
├── spec.md              # Feature specification
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   ├── ruleset.schema.yaml
│   └── traffic-record.schema.json
└── checklists/
    └── requirements.md
```

### Source Code (repository root)

```text
cmd/dockerproxy/
└── main.go              # CLI entrypoint, flag parsing, signal handling, component wiring

config/                  # Declarative configuration and semantic ruleset file loading/validation (*_test.go co-located)
listener/                # Interface layer for Unix/TCP socket management & shutdown (*_test.go co-located)
proxy/                   # Core HTTP reverse proxy engine, connection upgrade hijacking & response filtering (*_test.go co-located)
rules/                   # Core semantic policy evaluation engine, struct deserialization & rule matching algorithms (*_test.go co-located)
recorder/                # Core traffic recording & JSONL audit formatting (*_test.go co-located)

tests/
├── contract/            # Contract tests against ruleset & traffic recording schemas
└── integration/         # End-to-end socket proxying, semantic ruleset denial & response filtering tests
```

**Structure Decision**: Selected a modular single-project Go layout separating entrypoint/interface components (`cmd/dockerproxy`, `config`, `listener`) from core domain packages (`proxy`, `rules`, `recorder`). Unit tests are co-located within the same package directories per idiomatic Go practice.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | All architectural decisions align strictly with the four constitutional principles without deviation. |
