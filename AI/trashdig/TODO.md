# TrashDig TODO List

## 🏗️ ADK-Native Refactor (Priority)
- [x] **[HIGH]** Refactor `Coordinator` from Python loop to `LlmAgent`.
    - [x] Define sub-agents in `LlmAgent` constructor.
    - [x] Replace `run_loop` with agentic delegation.
- [x] **[HIGH]** Implement `TrashDigCallback` (ADK Callbacks).
    - [x] Move TUI tool-call updates to `before_tool_callback`.
    - [x] Integrate `CostTracker` and DB logging into `after_model_callback`.
    - [x] Replace `on_error` with `on_model_error_callback`.
- [x] **[MEDIUM]** Transition to `SessionService` for Shared Context.
    - [x] Use `SqliteSessionService` backed by `.trashdig/trashdig.db`.
    - [x] All agents in a scan share a `session_id_prefix`; stable IDs via `{prefix}:{agent.name}`.
    - [x] Scan sessions tracked in `scan_sessions` table for crash-safe resumption.
    - [x] Centralize `SessionService` management in `src/trashdig/services/session.py`.
- [x] **[MEDIUM]** Adopt ADK Artifact API.
    - [x] Refactor `@artifact_tool` to use `ToolContext.save_artifact` with legacy fallback.
    - [x] Update agents to use artifact references for large analysis blobs (ASTs, routes).
    - [x] Initialize `FileArtifactService` in `main.py` and pass to `Engine`.
- [x] **[LOW]** Standardize Agent Interfaces.
    - [x] Remove custom `.scan()`, `.hunt()`, `.map_routes()` methods.
    - [x] Move domain logic into prompts and use native `agent.run()` or `runner.run_async()`.

## Core Infrastructure
- [x] Implement `tree-sitter` for AST-based analysis.
- [x] Integrate `semgrep` for pattern-based vulnerability scanning.
- [x] Integrate `ripgrep` for fast textual search across the codebase.
- [x] Build a knowledge database of CWE entries with examples for agent reference.
- [x] Implement `bash_tool` for secure command execution (Phase 1).
- [x] Integrate `google_search` and `web_fetch` for automated security research.
- [x] **[HIGH]** Setup SQLite Project Database for persistent knowledge and session management (Phase 4).
- [x] **[REFAC]** Implement `Engine` State Machine (`src/trashdig/engine/`).
    - [x] Move core logic from `utils.run_prompt` into a formal `Engine` class.
    - [x] *Note: Custom Engine has been removed in favor of ADK Runner + Callbacks.*
- [x] **[REFAC]** Context Compaction & History Management.
    - [x] Implement a `ContextManager` to monitor tokens.
    - [x] *Note: Moving to ADK native compaction/summarization.*
- [x] **[REFAC]** Implement Parallel Task Execution in `Coordinator`.
    - [x] Use `asyncio.Semaphore` for a configurable concurrency limit.
    - [x] *Note: Moving to ADK native parallel agent execution.*

## Recon Agent Suite (Replacing Legacy Archeology)
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
- [x] **[MEDIUM]** Complex AST Expressions: Improve support for member access, await expressions, and nested call resolution in `trace_taint` and `get_scope_info`.

## Multi-Stage Verification Pipeline
- [x] **[HIGH]** SkepticAgent: Adversarial Reviewer.
    - [x] Mandatory pre-validation gate for all Hunter findings.
    - [x] Attempts to debunk findings by identifying missed sanitizers, middleware, or logic-level defenses.
- [x] **[HIGH]** Safe Execution Environment: Implement containerized (Docker) PoC execution for the `ValidatorAgent`.
- [x] **[MEDIUM]** Refine `ValidatorAgent` for PoC Generation.
    - [x] Invoked only after `SkepticAgent` approval.
    - [x] Focuses on generating and executing PoC scripts in the containerized sandbox to prove reachability and exploitability.
- [x] **[HIGH]** Iterative PoC Refinement: Implement a feedback loop where the `ValidatorAgent` analyzes failure logs from its own PoC execution and self-corrects.

## Services & Safety Middleware
- [x] **[HIGH]** Logic-Level Permission Middleware (`src/trashdig/services/permissions.py`).
    - [x] Intercept tool calls based on `trashdig.toml` policies (e.g., `allow_network`).
    - [x] Trigger manual TUI confirmation for sensitive or high-risk operations.
- [x] **[MEDIUM]** Cost Tracking Service (`src/trashdig/services/cost.py`).
    - [x] Map model names to USD rates for real-time financial monitoring of scan sessions.
- [x] **[MEDIUM]** Structural Refactor: Centralize Shared Logic.
    - [x] Move `RateLimiter`, `Database`, `CostTracker`, and `PermissionManager` into a `services` package to decouple infrastructure from agent logic.


### Path Handling Standards Compliance
- [x] **[HIGH]** Remove hardcoded `.trashdig/trashdig.db` defaults from `src/trashdig/services/database.py` and `src/trashdig/tools.py`.
- [x] **[MEDIUM]** Refactor `init_artifact_manager` to rely on `Config` rather than hardcoded path segments.
- [x] **[MEDIUM]** Audit and fix any `src/` modules that use `os.getcwd()` or hardcoded relative paths instead of resolving them through the `Config` workspace root.
- [x] **[LOW]** Audit `tests/` to ensure all tests requiring a filesystem use `tmp_path` fixtures rather than local `./.trashdig` or other project-root directories.
- [x] **[LOW]** Centralize path resolution in `Config` to handle workspace vs. data directory mappings consistently.


### Semantic Intelligence (Phase 3)

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
- [x] **[MEDIUM]** Interactive finding viewer (Markdown rendering).
- [x] **[LOW]** "Agent Ask" mechanism for structured questioning (Phase 4).
- [ ] **[MEDIUM]** Progress Tracking: Add real-time progress bars or a task status dashboard.
- [ ] **[LOW]** Command History Persistence: Save REPL history between sessions.

## ADK Feature Gaps (not yet tracked)

### Workflow Agents
- [x] **[MEDIUM]** Use `LoopAgent` for the hypothesis-driven hunting cycle.
    - [x] Replace the manual `asyncio` retry/loop in `Coordinator.run_loop()` with ADK's `LoopAgent` + escalation condition.
- [x] **[HIGH]** Parallel Hunting: Split codebase into logical segments during Recon and review them with parallel Hunter sessions.
- [ ] **[HIGH]** "Pause & Steer" Collaborative Steering:
    - [ ] Define `EngineState.PAUSED` and `EngineState.STEERING` in `types.py`.
    - [ ] Implement a global `asyncio.Event` or interrupt flag in `Coordinator` to signal pause.
    - [ ] Update `TrashDigCallback.on_before_model` to check for pause state and await a resume event.
    - [ ] Add `pause` and `resume` commands to the TUI/REPL.
    - [ ] Add a `hint <text>` command to inject user context into the current agent session as a high-priority message.
    - [ ] Add a `hypotheses` command to the REPL to list and manually reprioritize/delete hypotheses.
    - [ ] Implement structured "Agent Ask" UI to allow agents to proactively request steering.

### Session & Memory
- [x] **[MEDIUM]** Adopt a persistent `SessionService` (e.g., database-backed) to allow scan resumption across CLI invocations.
    - [x] Using `SqliteSessionService` from `google.adk.sessions.sqlite_session_service`.
    - [x] Shares `.trashdig/trashdig.db` with `ProjectDatabase` (no schema conflicts).
- [x] **[MEDIUM]** Summarizer Wiring: Hook up the `SummarizerAgent` in the core `run_agent` helper to compact conversation history when token limits are approached.
- [ ] **[LOW]** Evaluate ADK `MemoryService` for cross-session long-term knowledge retention.
    - [ ] Distinguish from `SessionService` (per-conversation) vs. `MemoryService` (persistent cross-session facts).
    - [ ] Assess overlap with existing `ProjectDatabase` — may be redundant.

### Tool Ecosystem
- [x] **[MEDIUM]** Integrate MCP (Model Context Protocol) tools via ADK's native MCP support.
    - [x] Evaluate existing security-focused MCP servers (e.g., static analysis, CVE lookup) as drop-in tools.
    - [x] See ADK docs: `docs/mcp/index.md` and `docs/tools/mcp-tools.md`.
    - [x] Implemented: `McpServerConfig` in `config.py`, `tools/mcp_toolsets.py` factory, `extra_tools` on all agent factories, wired in `Coordinator`. Configure via `[[mcp_servers]]` in `trashdig.toml`.
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
- [ ] **[HIGH]** Implement ADK Evaluation (`adk eval`) for agent regression testing. [DEFERRED]
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

## 🛠️ Post-Review Refinements (from April 2026 Review)

### New Tools (April 2026)
- [x] **[LOW]** Implement `list_files` tool (ls equivalent).
- [x] **[LOW]** Implement `find_files` tool (find equivalent).
- [x] **[LOW]** Implement `detect_language` tool (file-level and project-level language detection).

### Semantic Intelligence & Taint Tracing
- [x] **[HIGH]** Fix `trace_taint_cross_file` limitations: handle namespaces, imports, and complex callee expressions (e.g., `obj.method()`).
- [ ] **[MEDIUM]** Fix `_find_calls_passing_variable` (`src/trashdig/tools/trace_taint_cross_file.py`) missing chained/fluent callee expressions: when a call's receiver is itself a call (e.g. Java `Runtime.getRuntime().exec(cmd)`), callee-name extraction fails to identify the call and the tainted argument is silently dropped from the trace. Confirmed via direct test (2026-08-08): a plain call (`execCommand(cmd)`) and a simple member call (`rt.exec(cmd)`) are both detected, but the chained form is not. Likely affects any language, not just Java. Not an `argument_types` config issue — verified `JAVASCRIPT_METADATA`, `GO_METADATA`, `CSHARP_METADATA`, `C_METADATA`, `CPP_METADATA`, `JAVA_METADATA`, `RUBY_METADATA` all resolve `argument_list`/`arguments` nodes correctly.
- [x] **[MEDIUM]** Improve `get_ast_summary` and `get_scope_info`: support nested definitions, JS arrow functions, and local variable assignments.
- [x] **[MEDIUM]** Decouple language-specific logic: move hardcoded node types and skips (like `self`/`cls`) from tools to a configuration or metadata structure.
- [x] **[MEDIUM]** Advanced Taint Analysis: Add support for variable aliasing (data flow through assignments).
- [x] **[MEDIUM]** Broaden AST Support: Expand `tree-sitter` node coverage (e.g., arrow functions, expressions) and language support.
- [x] **[LOW]** Optimize `tree-sitter` initialization: Move library imports out of hot paths and validate binary dependencies at startup.

### Language Expansion (tree-sitter)

Each item requires: (1) adding the grammar package to `pyproject.toml`, (2) adding a `LanguageMetadata` entry in `src/trashdig/metadata/languages.py`.

- [x] **[MEDIUM]** Add C support (`tree-sitter-c`).
- [x] **[MEDIUM]** Add C++ support (`tree-sitter-cpp`).
- [x] **[MEDIUM]** Add Java support (`tree-sitter-java`).
- [x] **[LOW]** Add Ruby support (`tree-sitter-ruby`).
- [x] **[LOW]** Add Rust support (`tree-sitter-rust`).
- [x] **[LOW]** Add PHP support (`tree-sitter-php`).

### Sandbox & Safety
- [x] **[HIGH]** Fix Sandbox platform compatibility: Strictly enforce `require_sandbox` and fail on non-Linux platforms if required.
- [x] **[MEDIUM]** Implement native sandboxing for non-Linux platforms (e.g., `sandbox-exec` for macOS) to fulfill the `require_sandbox` mandate natively.
    - [x] Implemented `BxSandbox` (`src/trashdig/sandbox/bx.py`) using [bx-mac](https://github.com/holtwick/bx-mac). Allow-first model: blocks `~/.ssh`, `~/.gnupg`, sibling projects, etc. Install: `brew install holtwick/tap/bx`.
    - Note: Network isolation (`network=False`) is not enforceable via bx. Use `container_bash_tool` (Docker) when network isolation is required on macOS.
- [x] **[MEDIUM]** Harden `bash_tool`: Default `network=False` and verify User Namespace (`-U`) behavior in `MinijailSandbox`.
- [x] **[MEDIUM]** Secure `container_bash_tool`: Enforce containerization when `require_sandbox` is True.

### Infrastructure & Refinement
- [x] **[HIGH]** Robust JSON Parsing: Implement centralized `parse_json_response` and `extract_json_list` utilities for all agent responses.
- [x] **[HIGH]** Fix `PermissionManager` metadata loss: Ensure `wrap_tool` preserves original tool name and description.
- [x] **[MEDIUM]** Capture LLM Prompts: Update `TrashDigCallback` to record the actual prompt sent to the model in the database.
- [x] **[MEDIUM]** Configurable Cost Tracking: Refactor `CostTracker` to use configurable or dynamically fetched rates (via LiteLLM JSON).
- [x] **[MEDIUM]** Recursive Agent Search: Update `Coordinator._agent_by_name` to find nested agents for callback accounting.
- [x] **[LOW]** Configurable `noisy_dirs`: Move the hardcoded list in `get_project_structure` to `trashdig.toml`.
- [ ] **[LOW]** Consolidate `Coordinator` logic: Reduce redundancy between `run_full_scan` and TUI-specific methods (`run_recon`, `run_hunter`).
- [x] **[MEDIUM]** Standardize Task/Hypothesis IDs: Resolve naming inconsistency between `id` and `task_id` across database schema, types, and tools.
- [x] **[LOW]** Enforce Python import standards: Consistent grouping (stdlib, 3rd party, trashdig), alphabetical sorting, and top-level placement via Ruff/isort.
- [x] **[LOW]** Shared Database Connection: Refactor tools to use a singleton `ProjectDatabase` or connection pool to avoid SQLite locking issues during parallel agent execution.
- [x] **[MEDIUM]** Add a VulnDB for vulnerability information retrieval.
- [x] **[MEDIUM]** Critic Agent: Implement an adversarial reviewer agent and wire it as a tool for Hunter and Validator agents.
- [ ] **[MEDIUM]** Add deterministic checks for the verifier.
- [ ] **[MEDIUM]** Use long term MemoryService for findings, conversation history, memory across sessions.

## 🚀 Post-Assessment Roadmap (New Additions)
These priorities were established following codebase analysis to improve human steerability, external integrations, memory, and testing stability:

- [x] **[HIGH]** **Implement "Pause - [ ] **[HIGH]** **Implement "Pause & Steer" Steer" (Human-in-the-Loop)**: Introduce `EngineState.PAUSED` for a fully collaborative mode within the Textual UI. Permit researchers to manually pause, review pending bugs, provide contextual hints, and explicitly override hypotheses.
- [ ] **[MEDIUM]** **Tool Ecosystem Expansion**: Automate external security API interfaces (e.g., NVD/CVE APIs, GitHub Security Advisories, or Bugcrowd/HackerOne mappings) via dynamic ADK OpenAPI integrations, phasing out explicitly hand-written wrappers.
- [ ] **[MEDIUM]** **Cross-Session Memory Evolution**: Expand the architecture beyond edge `SqliteSessionService` by rolling out ADK's `MemoryService`. Guarantee long-term facts, findings, and code interactions persist identically across entirely distinct CLI invocation sessions against the same project.
- [ ] **[HIGH]** **Agent Evaluation Module (`adk eval`)**: Ensure prompt/logic integrity natively via synthetic datasets of known vulnerability samples (e.g., Juliet or OWASP modules) tested automatically against the multi-agent verification workflow to catch regressions.
- [x] **[LOW]** **RunConfig Adjustments**: Evolve from implicit invocations towards formal ADK `RunConfig` mechanisms for precisely controlling message streaming modalities, parameters, and bounded executions per payload interaction.

## 🐞 Bug Fixes (from August 2026 Functionality Review)
Verified functionality bugs found during a full codebase review on 2026-08-08. Ordered by priority.

- [x] **[HIGH]** Fix REPL console input never being mounted (`src/trashdig/tui/app.py:196`). `Input(...)` is passed only as the `target` arg to `AutoComplete` and never `yield`ed itself; `AutoComplete.compose()` only mounts its dropdown, not the target. The entire Interactive Console (help/scan/hunt/star/verify/status/exit, history, autocomplete) is unusable, and stray keystrokes fall through to global keybindings instead. *Fixed: the `Input` is now `yield`ed as its own widget and the same instance passed to `AutoComplete` as `target`.*
- [x] **[HIGH]** Declare `aiohttp` as a real dependency in `pyproject.toml`/`uv.lock`. `src/trashdig/tools/web_fetch.py:1` imports it unconditionally and it's loaded eagerly via `tools/__init__.py`, but it's absent from the lockfile — a clean `uv sync` breaks `import trashdig.tools` entirely (`ModuleNotFoundError`). *Fixed: added `aiohttp>=3.14.3` to `[project] dependencies` and regenerated `uv.lock`.*
- [x] **[HIGH]** Fix `Config.db_path` vs `Config.data_dir` reading different config keys (`src/trashdig/config.py:135-160`). *Fixed: extracted `_raw_data_dir()` helper honoring the nested `[database].data_dir` key, used by both `data_dir` and the `{datadir}` token; the token's raw value now has its own tokens (e.g. `{workspace}`) resolved before substitution into the outer path template, fixing the single-pass re-expansion gap.*
- [x] **[HIGH]** Attach `TrashDigCallback` to the `hunter` agent itself, not just `hunter_orchestrator` (`src/trashdig/agents/coordinator.py:217`). *Fixed: wiring loop now includes `hunter` explicitly alongside `hunter_orchestrator`.*
- [x] **[HIGH]** Wire `check_pause()` into `run_hunter` and `verify_finding` (`src/trashdig/agents/coordinator.py:638`, `:705`), not just `run_recon` (`:570`). *Fixed: `run_hunter` now awaits `check_pause()` before each target, and `verify_finding` awaits it at the start of each verification.*
- [x] **[HIGH]** Fix shared-singleton `TrashDigCallback._turn_counts` race during parallel hunting (`src/trashdig/agents/utils/callbacks.py:77`, called from `src/trashdig/agents/coordinator.py:648`). *Fixed: `_turn_counts` is now keyed by `(invocation_id, agent_name)` instead of `agent_name` alone, so concurrent `runner.run_async()` invocations sharing an agent name (e.g. parallel hunter segments) never share a counter. The now-unnecessary `reset_turn_counts()` calls in `run_recon`/`run_hunter` were removed (each invocation is naturally fresh); the one in `run_full_scan` remains as housekeeping since it's a single non-concurrent entry point. Added `test_turn_limit_independent_across_concurrent_invocations` regression test.*
- [x] **[HIGH]** Add missing `argument_types={"arguments"}` override to `JAVASCRIPT_METADATA` (`src/trashdig/metadata/languages.py:76-94`). *Fixed: verified `_find_calls_passing_variable` returned `[]` for JS call sites before the fix and now correctly resolves them.*
- [x] **[MEDIUM]** Pass a real environment (at least merged with `os.environ`) into `MinijailSandbox` (`src/trashdig/sandbox/minijail.py:103`). *Fixed: `get_sandbox()` now takes an `env` parameter, merges it over `os.environ`, and passes the result through a new `filter_env()` (`src/trashdig/sandbox/base.py`) that strips credential-shaped variables (API keys, tokens, passwords, SSH/GPG agent sockets, cloud credentials, etc.) by exact name and substring match before handing the environment to any sandbox backend. Also fixed `BxSandbox`/`NullSandbox`, which were re-merging raw `os.environ` in `run()` and silently undoing any filtering — they now trust `self.env` as the complete, already-filtered environment, matching `MinijailSandbox`'s existing contract.*
- [x] **[MEDIUM]** Close the SQLite connection in `get_next_hypothesis` (`src/trashdig/tools/get_next_hypothesis.py:20`). *Fixed: wrapped the connection in `contextlib.closing` so it's always closed, not just committed/rolled back.*
- [x] **[MEDIUM]** Fix cost-rate prefix matching to prefer the longest/most-specific match (`src/trashdig/services/cost.py:119-125`). *Fixed: extracted `CostTracker._best_prefix_match()`, used by both the loaded-rates prefix search and the `DEFAULT_RATES` fallback, which scans all matching keys and picks the longest rather than the first dict-order match.*
- [x] **[MEDIUM]** Use `config.db_path` (not manual `config.data_dir + "/trashdig.db"`) when initializing the session service (`src/trashdig/main.py:135`). *Fixed: now calls `init_session_service(db_path=config.db_path)`, matching every other DB-path consumer.*
- [x] **[MEDIUM]** Close the leaked pipe FD on the timeout branch in `landlock_tool.py:409-411`. *Fixed: widened the `try/finally` so `parent_conn.close()` runs for the timeout branch too, not just the success/EOFError paths.*
- [x] **[LOW]** Check `cursor.rowcount` in `update_hypothesis_status` (`src/trashdig/tools/update_hypothesis_status.py:16`, backed by `services/database.py:295-304`). *Fixed: `ProjectDatabase.update_hypothesis_status` now returns `bool` from `cursor.rowcount > 0`; the tool wrapper surfaces a stale/mistyped `task_id` as an error string instead of a false "updated" message.*
- [x] **[LOW]** Make concurrent "verify all findings" runs use `exclusive`/shared state correctly (`src/trashdig/tui/app.py:254`, `:534-558`). *Fixed: added an `_active_verifications` counter on `TrashDigApp`; `run_verification` now only reverts `_phase` to `"Idle"` once every concurrently-running verification worker has finished, not just the first one.*
