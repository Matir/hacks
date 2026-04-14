# TrashDig TODO List

## Core Infrastructure
- [x] Implement `tree-sitter` for AST-based analysis.
- [x] Integrate `semgrep` for pattern-based vulnerability scanning.
- [x] Integrate `ripgrep` for fast textual search across the codebase.
- [x] Build a knowledge database of CWE entries with examples for agent reference.
- [x] Implement `bash_tool` for secure command execution (Phase 1).
- [x] Integrate `google_search` and `web_fetch` for automated security research.
- [x] **[HIGH]** Setup SQLite Project Database for persistent knowledge and session management (Phase 4).
- [x] **[HIGH]** Implement `Engine` State Machine (`src/trashdig/engine/`).
    - [x] Move core logic from `utils.run_prompt` into a formal `Engine` class.
    - [x] Manage the "Observer-Actor" loop, tool-call retries, and JSON schema validation.
- [x] **[MEDIUM]** Context Compaction & History Management.
    - [x] Implement a `ContextManager` to monitor tokens.
    - [x] Add "History Pruning" and "Recursive Summarization" to preserve model intent within context limits.
- [x] **[MEDIUM]** Implement Parallel Task Execution in `Coordinator`.
    - [x] Use `asyncio.Semaphore` for a configurable concurrency limit (e.g., `max_parallel_tasks` in `trashdig.toml`).
    - [x] Adopt a worker-pool pattern to handle recursive hypothesis generation without exhausting resources.

## Recon Agent Suite (Replacing Archaeologist)
- [x] **[HIGH]** StackScout Agent: Hybrid Environment Detection.
    - [x] Combine deterministic checks (regex/file signatures) with inference-based LLM analysis to explain how the stack is implemented.
- [x] **[MEDIUM]** WebRouteMapper Agent: Conditional Surface Mapping.
    - [x] Invoked only if `StackScout` detects a web application.
    - [x] Uses `tree-sitter` to map all endpoints (e.g., Express routes, FastAPI decorators) into a structured artifact for the Hunter.

## Hunter Agent Enhancements
- [x] Multi-file context and definition resolution.
- [x] Initial taint analysis guidance.
- [x] Implement recursive **Hypothesis-Driven** loop (Phase 2).
- [x] Upgrade to true AST-aware taint analysis (Phase 3).
- [x] **[HIGH]** Enhanced Taint Analysis: Trace data flows across multiple files from entry points to sinks.

## Multi-Stage Verification Pipeline
- [x] **[HIGH]** SkepticAgent: Adversarial Reviewer.
    - [x] Mandatory pre-validation gate for all Hunter findings.
    - [x] Attempts to debunk findings by identifying missed sanitizers, middleware, or logic-level defenses.
- [x] **[HIGH]** Safe Execution Environment: Implement containerized (Docker) PoC execution for the `ValidatorAgent`.
- [x] **[MEDIUM]** Refine `ValidatorAgent` for PoC Generation.
    - [x] Invoked only after `SkepticAgent` approval.
    - [x] Focuses on generating and executing PoC scripts in the containerized sandbox to prove reachability and exploitability.

## Services & Safety Middleware
- [x] **[HIGH]** Logic-Level Permission Middleware (`src/trashdig/services/permissions.py`).
    - [x] Intercept tool calls based on `trashdig.toml` policies (e.g., `allow_network`).
    - [x] Trigger manual TUI confirmation for sensitive or high-risk operations.
- [x] **[MEDIUM]** Cost Tracking Service (`src/trashdig/services/cost.py`).
    - [x] Map model names to USD rates for real-time financial monitoring of scan sessions.
- [x] **[MEDIUM]** Structural Refactor: Centralize Shared Logic.
    - [x] Move `RateLimiter`, `Database`, `CostTracker`, and `PermissionManager` into a `services` package to decouple infrastructure from agent logic.

## Semantic Intelligence (Phase 3)
- [x] Implement `FindReferences(symbol)` tool.
- [x] Implement `GetScope(file, line)` tool.
- [x] **[MEDIUM]** Dynamic Tool Configuration: Configure `semgrep` rules based on detected tech stack and `config.toml`.
- [x] **[HIGH]** Security Sandboxing (Linux/Minijail):
    - [x] Create `src/trashdig/sandbox/` abstraction layer.
    - [x] Implement `MinijailSandbox` with PID/Mount/Network namespaces.
    - [x] Add `require_sandbox` (default: True) to `trashdig.toml`.
    - [x] Refactor `bash_tool` and `ripgrep_search` to use the sandbox abstraction.

## TUI & Collaborative Steering
- [x] Functional REPL with history and autocomplete.
- [x] **[MEDIUM]** Real-time streaming of agent logs to the REPL.
- [ ] **[MEDIUM]** Interactive finding viewer (Markdown rendering).
- [ ] **[LOW]** "Agent Ask" mechanism for structured questioning (Phase 4).
- [ ] **[MEDIUM]** Progress Tracking: Add real-time progress bars or a task status dashboard.
- [ ] **[LOW]** Command History Persistence: Save REPL history between sessions.
