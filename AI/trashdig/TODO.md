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
- [ ] **[MEDIUM]** Interactive finding viewer (Markdown rendering).
- [ ] **[LOW]** "Agent Ask" mechanism for structured questioning (Phase 4).
- [ ] **[MEDIUM]** Progress Tracking: Add real-time progress bars or a task status dashboard.
- [x] **[LOW]** Command History Persistence: Save REPL history between sessions.

## ADK Feature Gaps (not yet tracked)

### Workflow Agents
- [x] **[MEDIUM]** Use `LoopAgent` for the hypothesis-driven hunting cycle.
    - [x] Replace the manual `asyncio` retry/loop in `Coordinator.run_loop()` with ADK's `LoopAgent` + escalation condition.

### Session & Memory
- [x] **[MEDIUM]** Adopt a persistent `SessionService` (e.g., database-backed) to allow scan resumption across CLI invocations.
    - [x] Using `SqliteSessionService` from `google.adk.sessions.sqlite_session_service`.
    - [x] Shares `.trashdig/trashdig.db` with `ProjectDatabase` (no schema conflicts).
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
- [x] **[MEDIUM]** Improve `get_ast_summary` and `get_scope_info`: support nested definitions, JS arrow functions, and local variable assignments.
- [x] **[MEDIUM]** Decouple language-specific logic: move hardcoded node types and skips (like `self`/`cls`) from tools to a configuration or metadata structure.
- [x] **[MEDIUM]** Advanced Taint Analysis: Add support for variable aliasing (data flow through assignments).
- [ ] **[MEDIUM]** Broaden AST Support: Expand `tree-sitter` node coverage (e.g., arrow functions, expressions) and language support.
- [ ] **[LOW]** Optimize `tree-sitter` initialization: Move library imports out of hot paths and validate binary dependencies at startup.

### Language Expansion (tree-sitter)

Each item requires: (1) adding the grammar package to `pyproject.toml`, (2) adding a `LanguageMetadata` entry in `src/trashdig/metadata/languages.py`.

- [ ] **[MEDIUM]** Add C support (`tree-sitter-c`).
  - `extensions`: `.c`, `.h`
  - `definition_types`: `function_definition`
  - `scope_types`: `function_definition`, `compound_statement`
  - `assignment_types`: `assignment_expression`, `init_declarator`
  - `parameter_types`: `parameter_declaration`
  - `sinks`: `system`, `popen`, `exec`, `execv`, `execve`, `execvp`, `gets`, `scanf`, `sprintf`, `strcpy`, `strcat`, `memcpy`
  - `method_sinks`: (none — C has no methods)
  - `attr_separators`: `.`, `->`
  - `definition_patterns`: `r"\b{name}\s*\("`

- [ ] **[MEDIUM]** Add C++ support (`tree-sitter-cpp`).
  - `extensions`: `.cpp`, `.cc`, `.cxx`, `.hpp`, `.h`
  - `definition_types`: `function_definition`, `class_specifier`, `struct_specifier`, `template_declaration`
  - `scope_types`: `function_definition`, `class_specifier`, `namespace_definition`
  - `assignment_types`: `assignment_expression`, `init_declarator`, `declaration`
  - `parameter_types`: `parameter_declaration`
  - `sinks`: all C sinks + `new`, `delete`
  - `method_sinks`: `execute`, `query`
  - `skip_symbols`: `this`
  - `attr_separators`: `.`, `->`, `::`
  - `definition_patterns`: `r"\b{name}\s*\("`, `r"\b\w+::{name}\s*\("`

- [ ] **[MEDIUM]** Add Java support (`tree-sitter-java`).
  - `extensions`: `.java`
  - `definition_types`: `method_declaration`, `constructor_declaration`, `class_declaration`, `interface_declaration`
  - `scope_types`: `method_declaration`, `constructor_declaration`, `class_declaration`
  - `assignment_types`: `assignment_expression`, `local_variable_declaration`, `variable_declarator`
  - `parameter_types`: `formal_parameter`, `spread_parameter`
  - `sinks`: `exec`, `loadClass`, `eval`, `forName`
  - `method_sinks`: `execute`, `executeQuery`, `executeUpdate`, `prepareStatement`, `write`
  - `skip_symbols`: `this`, `super`
  - `attr_separators`: `.`
  - `definition_patterns`: `r"\b{name}\s*\("`

- [ ] **[LOW]** Add Ruby support (`tree-sitter-ruby`).
  - `extensions`: `.rb`
  - `definition_types`: `method`, `singleton_method`, `class`, `module`
  - `scope_types`: `method`, `singleton_method`, `class`, `module`, `block`
  - `assignment_types`: `assignment`, `multiple_assignment`, `operator_assignment`
  - `parameter_types`: `identifier`, `splat_parameter`, `hash_splat_parameter`, `optional_parameter`, `block_parameter`
  - `sinks`: `system`, `exec`, `eval`, `send`, `public_send`, `constantize`
  - `method_sinks`: `execute`, `query`, `where`, `html_safe`, `raw`
  - `skip_symbols`: `self`
  - `attr_separators`: `.`, `::`
  - `definition_patterns`: `r"\bdef\s+{name}\b"`, `r"\bdef\s+self\.{name}\b"`

- [ ] **[LOW]** Add Rust support (`tree-sitter-rust`).
  - `extensions`: `.rs`
  - `definition_types`: `function_item`, `impl_item`, `struct_item`, `enum_item`, `trait_item`
  - `scope_types`: `function_item`, `impl_item`, `closure_expression`
  - `assignment_types`: `let_declaration`, `assignment_expression`
  - `parameter_types`: `parameter`, `self_parameter`
  - `sinks`: `Command`, `from_utf8_unchecked`, `transmute`, `write`
  - `method_sinks`: `execute`, `query`, `exec`
  - `skip_symbols`: `self`
  - `attr_separators`: `.`, `::`
  - `definition_patterns`: `r"\bfn\s+{name}\b"`

- [ ] **[LOW]** Add PHP support (`tree-sitter-php`).
  - `extensions`: `.php`
  - `definition_types`: `function_definition`, `method_declaration`, `class_declaration`
  - `scope_types`: `function_definition`, `method_declaration`, `class_declaration`
  - `assignment_types`: `assignment_expression`
  - `parameter_types`: `simple_parameter`, `variadic_parameter`
  - `sinks`: `system`, `exec`, `passthru`, `shell_exec`, `popen`, `proc_open`, `eval`, `assert`, `include`, `require`, `include_once`, `require_once`
  - `method_sinks`: `query`, `execute`, `prepare`
  - `skip_symbols`: `$this`
  - `attr_separators`: `.`, `->`, `::`
  - `definition_patterns`: `r"\bfunction\s+{name}\b"`

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
- [ ] **[LOW]** Configurable `noisy_dirs`: Move the hardcoded list in `get_project_structure` to `trashdig.toml`.
- [ ] **[LOW]** Consolidate `Coordinator` logic: Reduce redundancy between `run_full_scan` and TUI-specific methods (`run_recon`, `run_hunter`).
- [x] **[MEDIUM]** Standardize Task/Hypothesis IDs: Resolve naming inconsistency between `id` and `task_id` across database schema, types, and tools.
- [x] **[LOW]** Enforce Python import standards: Consistent grouping (stdlib, 3rd party, trashdig), alphabetical sorting, and top-level placement via Ruff/isort.
- [x] **[LOW]** Shared Database Connection: Refactor tools to use a singleton `ProjectDatabase` or connection pool to avoid SQLite locking issues during parallel agent execution.
