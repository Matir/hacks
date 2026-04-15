# TrashDig TODO List

## 🏗️ ADK-Native Refactor (Priority)
- [ ] **[HIGH]** Refactor `Coordinator` from Python loop to `LlmAgent`.
    - [ ] Define sub-agents in `LlmAgent` constructor.
    - [ ] Replace `run_loop` with agentic delegation.
- [ ] **[HIGH]** Implement `TrashDigCallback` (ADK Callbacks).
    - [ ] Move TUI updates to `on_tool_call_start` and `on_run_step_end`.
    - [ ] Integrate `CostTracker` and DB logging into the callback chain.
- [ ] **[MEDIUM]** Transition to `SessionService` for Shared Context.
    - [ ] Ensure all agents in a scan session share a single `session_id`.
    - [ ] Remove manual context passing between `Coordinator` and agents.
- [ ] **[MEDIUM]** Adopt ADK Artifact API.
    - [ ] Refactor `@artifact_tool` to return `google.adk.artifacts.Artifact`.
    - [ ] Update agents to use artifact references for large analysis blobs (ASTs, routes).
- [ ] **[LOW]** Standardize Agent Interfaces.
    - [ ] Remove custom `.scan()`, `.hunt()`, `.map_routes()` methods.
    - [ ] Move domain logic into prompts and use `agent.run()`.

## Core Infrastructure
- [x] Implement `tree-sitter` for AST-based analysis.
- [x] Integrate `semgrep` for pattern-based vulnerability scanning.
- [x] Integrate `ripgrep` for fast textual search across the codebase.
- [x] Build a knowledge database of CWE entries with examples for agent reference.
- [x] Implement `bash_tool` for secure command execution (Phase 1).
- [x] Integrate `google_search` and `web_fetch` for automated security research.
- [x] **[HIGH]** Setup SQLite Project Database for persistent knowledge and session management (Phase 4).
- [ ] **[REFAC]** Implement `Engine` State Machine (`src/trashdig/engine/`).
    - [x] Move core logic from `utils.run_prompt` into a formal `Engine` class.
    - [ ] *Note: Custom Engine is being deprecated in favor of ADK Runner + Callbacks.*
- [ ] **[REFAC]** Context Compaction & History Management.
    - [x] Implement a `ContextManager` to monitor tokens.
    - [ ] *Note: Moving to ADK native compaction/summarization.*
- [ ] **[REFAC]** Implement Parallel Task Execution in `Coordinator`.
    - [x] Use `asyncio.Semaphore` for a configurable concurrency limit.
    - [ ] *Note: Moving to ADK native parallel agent execution.*

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

## ADK Feature Gaps (not yet tracked)

### Workflow Agents
- [ ] **[MEDIUM]** Use `LoopAgent` for the hypothesis-driven hunting cycle.
    - [ ] Replace the manual `asyncio` retry/loop in `Coordinator.run_loop()` with ADK's `LoopAgent` + escalation condition.
    - [ ] *Note: `SequentialAgent`/`ParallelAgent` are already noted in the ADK-Native Refactor section above.*

### Session & Memory
- [ ] **[MEDIUM]** Adopt a persistent `SessionService` (e.g., database-backed) to allow scan resumption across CLI invocations.
    - [ ] Currently only `InMemorySessionService` is used; sessions are lost on exit.
    - [ ] Evaluate `VertexAiSessionService` or a custom SQLite-backed implementation.
- [ ] **[LOW]** Evaluate ADK `MemoryService` for cross-session long-term knowledge retention.
    - [ ] Distinguish from `SessionService` (per-conversation) vs. `MemoryService` (persistent cross-session facts).
    - [ ] Assess overlap with existing `ProjectDatabase` — may be redundant.

### Tool Ecosystem
- [ ] **[MEDIUM]** Integrate MCP (Model Context Protocol) tools via ADK's native MCP support.
    - [ ] Evaluate existing security-focused MCP servers (e.g., static analysis, CVE lookup) as drop-in tools.
    - [ ] See ADK docs: `docs/mcp/index.md` and `docs/tools/mcp-tools.md`.
- [ ] **[LOW]** Use ADK OpenAPI tool generation for third-party security APIs.
    - [ ] Candidates: NVD/CVE API, bug bounty platform APIs (HackerOne, Bugcrowd), GitHub Security Advisory API.
    - [ ] See ADK docs: `docs/tools/openapi-tools.md`.

### Runtime Configuration
- [ ] **[LOW]** Leverage ADK `RunConfig` for explicit streaming mode and response modality control.
    - [ ] Currently streaming is implicit via `runner.run_async()`; `RunConfig` enables finer-grained control.
    - [ ] See ADK docs: `docs/runtime/runconfig.md`.

### Provider & Model Backends
- [ ] **[LOW]** Document and test LiteLLM as a model backend option via ADK's model abstraction.
    - [ ] ADK supports LiteLLM natively; would enable Claude, Mistral, and other non-Gemini models without custom provider hacks.
    - [ ] See ADK docs: `docs/agents/models.md`.

### Agent-to-Agent (A2A) Protocol
- [ ] **[LOW]** Evaluate A2A protocol for distributed/remote agent deployment.
    - [ ] Useful if agents are deployed as separate services (e.g., Hunter on GPU node, Validator in isolated cloud VM).
    - [ ] See ADK docs: A2A integration example in `adk-python` README.

### Evaluation & Testing
- [ ] **[HIGH]** Implement ADK Evaluation (`adk eval`) for agent regression testing.
    - [ ] Build an eval dataset of known vulnerable code samples with expected findings (CWE labels, file/line).
    - [ ] Run `adk eval` in CI to catch agent prompt regressions.
    - [ ] See ADK docs: `docs/evaluate/index.md`.
- [ ] **[LOW]** Use ADK Dev UI during development for interactive agent debugging.
    - [ ] `adk web` provides a built-in chat UI to test individual agents without the full TUI.
    - [ ] Useful for prompt iteration on Hunter/Skeptic/Validator without running a full scan.

### Deployment
- [ ] **[LOW]** Add Cloud Run deployment configuration for running TrashDig as a service.
    - [ ] Containerize with Docker; configure ADK for Cloud Run target.
    - [ ] See ADK docs: `docs/deploy/cloud-run.md`.
- [ ] **[LOW]** Evaluate Vertex AI Agent Engine for production-scale managed deployment.
    - [ ] See ADK docs: `docs/deploy/agent-engine.md`.
