# TrashDig TODO List

## Core Infrastructure
- [x] Implement `tree-sitter` for AST-based analysis.
- [x] Integrate `semgrep` for pattern-based vulnerability scanning.
- [x] Integrate `ripgrep` for fast textual search across the codebase.
- [x] Build a knowledge database of CWE entries with examples for agent reference.
- [x] Implement `bash_tool` for secure command execution (Phase 1).
- [x] Integrate `google_search` and `web_fetch` for automated security research.
- [ ] Setup SQLite Project Database for persistent knowledge (Phase 4).

## Archaeologist Agent Enhancements
- [x] Framework and technology stack detection.
- [ ] Use `ripgrep` to quickly find entry points (e.g., routes, controllers).
- [ ] Improve file summarization by providing more context to the LLM.

## Hunter Agent Enhancements
- [x] Multi-file context and definition resolution.
- [x] Initial taint analysis guidance.
- [x] Implement recursive **Hypothesis-Driven** loop (Phase 2).
- [x] Upgrade to true AST-aware taint analysis (Phase 3).

## Validation & Verification (Phase 1)
- [x] Create `ValidatorAgent` for PoC generation.
- [x] Implement finding verification loop (Prove the bug).

## Semantic Intelligence (Phase 3)
- [x] Implement `FindReferences(symbol)` tool.
- [x] Implement `GetScope(file, line)` tool.


## TUI & Collaborative Steering
- [x] Functional REPL with history and autocomplete.
- [ ] Real-time streaming of agent logs to the REPL.
- [ ] Interactive finding viewer (Markdown rendering).
- [ ] "Agent Ask" mechanism for structured questioning (Phase 4).
