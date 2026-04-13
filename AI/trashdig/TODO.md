# TrashDig TODO List

## Core Infrastructure
- [x] Implement `tree-sitter` for AST-based analysis.
- [x] Integrate `semgrep` for pattern-based vulnerability scanning.
- [x] Integrate `ripgrep` for fast textual search across the codebase.
- [x] Build a knowledge database of CWE entries with examples for agent reference.
- [x] Implement `bash_tool` for secure command execution (Phase 1).
- [x] Integrate `google_search` and `web_fetch` for automated security research.
- [x] **[HIGH]** Setup SQLite Project Database for persistent knowledge and session management (Phase 4).
- [ ] **[MEDIUM]** Implement Parallel Task Execution in `Coordinator` using `asyncio.gather`.

## Archaeologist Agent Enhancements
- [x] Framework and technology stack detection.
- [ ] **[MEDIUM]** Use `ripgrep` to quickly find entry points (e.g., routes, controllers).
- [ ] **[LOW]** Improve file summarization by providing more context to the LLM.

## Hunter Agent Enhancements
- [x] Multi-file context and definition resolution.
- [x] Initial taint analysis guidance.
- [x] Implement recursive **Hypothesis-Driven** loop (Phase 2).
- [x] Upgrade to true AST-aware taint analysis (Phase 3).
- [x] **[HIGH]** Enhanced Taint Analysis: Trace data flows across multiple files from entry points to sinks.

## Validation & Verification (Phase 1)
- [x] Create `ValidatorAgent` for PoC generation.
- [x] Implement finding verification loop (Prove the bug).
- [x] **[HIGH]** Safe Execution Environment: Implement containerized (Docker) PoC execution for the `ValidatorAgent`.

## Semantic Intelligence (Phase 3)
- [x] Implement `FindReferences(symbol)` tool.
- [x] Implement `GetScope(file, line)` tool.
- [ ] **[MEDIUM]** Dynamic Tool Configuration: Configure `semgrep` rules based on detected tech stack and `config.toml`.


## TUI & Collaborative Steering
- [x] Functional REPL with history and autocomplete.
- [ ] **[MEDIUM]** Real-time streaming of agent logs to the REPL.
- [ ] **[MEDIUM]** Interactive finding viewer (Markdown rendering).
- [ ] **[LOW]** "Agent Ask" mechanism for structured questioning (Phase 4).
- [ ] **[MEDIUM]** Progress Tracking: Add real-time progress bars or a task status dashboard.
- [ ] **[LOW]** Command History Persistence: Save REPL history between sessions.
