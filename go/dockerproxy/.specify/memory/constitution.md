<!--
SYNC IMPACT REPORT
Version change: uninitialized -> 1.0.0
Modified principles:
  - Principle I: Code Quality & Maintainability (Added)
  - Principle II: Testing Standards & Discipline (Added)
  - Principle III: User Experience (UX) Consistency (Added)
  - Principle IV: Performance Requirements & Efficiency (Added)
Added sections:
  - Quality Gates & Verification Standards
  - Development Workflow
Removed sections:
  - None (Replaced template placeholders)
Templates requiring updates:
  - .specify/templates/plan-template.md: ✅ verified (generic Constitution Check gating supports these principles)
  - .specify/templates/spec-template.md: ✅ verified (requirement formatting and user scenarios align with UX and performance principles)
  - .specify/templates/tasks-template.md: ✅ verified (test-first phase organization aligns with testing standards)
Follow-up TODOs:
  - None
-->
# DockerProxy Constitution

## Core Principles

### I. Code Quality & Maintainability
All code written or modified MUST adhere to the highest standards of clarity, modularity, and idiomatic Go practices:
- **Idiomatic & Clean Code**: Code MUST follow standard Go formatting (`gofmt`/`goimports`), clear naming conventions, and idiomatic error handling. Errors MUST NOT be ignored or discarded silently; they MUST be handled or propagated with context.
- **Modularity & Separation of Concerns**: Features MUST be implemented as cohesive, loosely coupled packages with well-defined, minimal public interfaces to prevent circular dependencies and state entanglement.
- **Self-Documenting & Explicit Logic**: Complex business logic and algorithms MUST be accompanied by clear comments explaining *why* the implementation choice was made. All exported symbols (functions, types, packages) MUST have descriptive godocs.
- **Static Analysis Compliance**: Code submissions MUST pass all configured linter checks (`golangci-lint` or equivalent static analysis tools) with zero warnings or errors.

### II. Testing Standards & Discipline
Automated testing is mandatory to guarantee reliability and prevent regressions across the codebase:
- **Test-Driven & Verification-First**: Every new feature, functional modification, and bug fix MUST include automated tests. Bug fixes MUST include a regression test that fails prior to applying the fix and passes afterward.
- **Comprehensive Coverage**: Unit and package-level tests MUST verify happy paths, boundary conditions, malformed inputs, and failure recovery modes (including network errors, timeouts, and resource exhaustion).
- **Deterministic & Isolated Execution**: Tests MUST execute rapidly and deterministically. Tests MUST NOT rely on unmocked external network services, race-prone concurrency patterns, or arbitrary sleep timers. Mocking or local test doubles MUST be used for external dependencies.
- **Contract & Integration Verification**: Integration tests MUST validate critical interactions between core proxy components, CLI handlers, and network/protocol boundaries.

### III. User Experience (UX) Consistency
Interactions with the project tools, APIs, and command-line interfaces MUST provide a predictable and seamless user experience:
- **Predictable Interfaces**: CLI flags, configuration schemas, environment variables, and output formatting MUST follow uniform naming and behavioral conventions across all commands and utilities.
- **Actionable Diagnostics**: Log outputs and error messages MUST be clear, structured, and informative. When an error occurs, the output MUST explain what failed, why it failed, and provide actionable guidance on how the user can resolve the configuration or runtime issue.
- **Backward Compatibility**: Public interfaces, configuration files, and communication protocols MUST preserve backward compatibility where feasible. Any unavoidable breaking changes MUST be clearly documented with deprecation warnings and clear migration paths.

### IV. Performance Requirements & Efficiency
As a system networking and proxy tool, efficiency and minimal resource overhead are critical architectural constraints:
- **Low Latency & Minimal Overhead**: Proxy forwarding, stream handling, and request interception hot paths MUST add minimal latency overhead to the underlying connection stream.
- **Strict Resource Bounding**: Memory allocations, goroutine lifecycles, and network/file descriptors MUST be strictly bounded. Every spawned goroutine or open resource MUST have a clear lifecycle termination mechanism (e.g., using `context.Context` cancellation and explicit `Close()` defers) to eliminate leaks.
- **Scalability & Graceful Degradation**: The system MUST sustain high concurrency and throughput without memory exhaustion or panics. Performance benchmarks (`go test -bench`) MUST be maintained and validated for critical performance-sensitive execution paths.

## Quality Gates & Verification Standards

- **Pre-Merge Verification**: All code submissions MUST pass automated compilation, linting, and full test suites prior to merge approval.
- **Code Review Rigor**: Peer and automated agent reviews MUST evaluate adherence to all four core principles, specifically verifying error handling rigor, goroutine/resource cleanup, and test quality.
- **Input Validation & Security**: All external data inputs (CLI arguments, configuration files, network sockets) MUST be rigorously validated and sanitized before processing to prevent crashes, command injections, or denial-of-service vulnerabilities.

## Development Workflow

- **Specification Before Implementation**: Architectural modifications and non-trivial features MUST begin with a clear feature specification (`spec.md`) and implementation plan (`plan.md`) verifying constitutional alignment.
- **Incremental Delivery**: Changes SHOULD be structured as focused, independently testable tasks that preserve codebase integrity and passing test states at every step.
- **Synchronized Documentation**: Architectural diagrams, API documentation, and README instructions MUST be updated concurrently with code changes.

## Governance

- **Supremacy**: This Constitution supersedes all ad-hoc conventions or informal development practices. All human contributors and automated agents MUST adhere strictly to these principles.
- **Amendments**: Amendments to this Constitution require explicit documentation of rationale, evaluation of impact across project specification templates, and formal ratification.
- **Semantic Versioning**: Constitution updates adhere to semantic versioning rules:
  - **MAJOR**: Backward-incompatible governance removals, principle redefinitions, or structural changes.
  - **MINOR**: Addition of new core principles or materially expanded governance standards.
  - **PATCH**: Non-semantic refinements, wording improvements, or typo corrections.
- **Compliance Review**: All implementation plans (`plan.md`) and feature specifications (`spec.md`) MUST explicitly verify alignment with the principles established in this Constitution.

**Version**: 1.0.0 | **Ratified**: 2026-07-01 | **Last Amended**: 2026-07-01
