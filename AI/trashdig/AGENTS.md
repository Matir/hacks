# TrashDig: Agent Foundation & Mandates

TrashDig is an AI-powered, language-agnostic vulnerability scanner and security research assistant. It uses a multi-agent system built on the **Agent Development Kit (ADK)** to map codebases, trace data flows, and verify security findings.

## 🏗 Architecture & Agent Personas

TrashDig operates as a coordinated team of specialized agents:

1.  **Archaeologist Agent**:
    *   **Role**: Mapper and Scout.
    *   **Tasks**: Detects framework/tech stacks, respects `.gitignore`, and generates file summaries.
    *   **Goal**: Identify "high-value targets" (entry points, sensitive configurations, risky controllers).
2.  **Hunter Agent**:
    *   **Role**: Deep-Dive Researcher.
    *   **Tasks**: Performs hypothesis-driven analysis, AST-aware taint analysis, and cross-file symbol tracing.
    *   **Goal**: Connect untrusted user input to dangerous sinks.
3.  **Validator Agent**:
    *   **Role**: Proof-of-Concept Specialist.
    *   **Tasks**: Generates PoC scripts to confirm Hunter's findings.
    *   **Goal**: Prove exploitability and eliminate false positives.
4.  **TUI (Human-in-the-Loop)**:
    *   **Role**: Steering & Prioritization.
    *   **Interface**: Built with `Textual`.
    *   **Goal**: Allow researchers to "star" files and guide the Hunter agent.

## 🛠 Technical Stack

*   **Language**: Python 3.14+ (using `uv` and `mise`).
*   **Agent Framework**: Google ADK.
*   **Static Analysis**: `tree-sitter` (AST parsing), `semgrep` (pattern matching), `ripgrep` (fast search).
*   **UI**: `textual` for the TUI, `prompt_toolkit` for the REPL.

## 📜 Engineering Standards (The Rules)

These rules are foundational. Adhere to them for all modifications:

1.  **Testing**: Always provide unit tests in the `tests/` directory. All code should be written alongside corresponding tests. Whenever features are added, both the test suite and coverage must be checked; coverage metrics should generally trend upwards. Aim for high coverage of agent logic.
2.  **Typing**: Strict type hints are mandatory (`pyright`/`mypy` clean).
3.  **Environment**: Use `uv` for dependencies and `mise` for task orchestration. Prefer `mise` tasks (e.g., `mise run test`, `mise run coverage`, `mise run lint`) for all common development operations to ensure manual execution and agentic workflows remain in-sync.
4.  **Documentation**: Add descriptive docstrings (Google style) to all classes and functions.
5.  **Imports**: Always check `pyproject.toml` before adding new dependencies. Ensure all imports are placed at the top of the file. Ask the user before adding a new top-level import.
6.  **Prompt Management**: Keep agent prompts in separate `.md` files within the `prompts/` directory. Do not hardcode long prompts.
7.  **Model Configuration**: Every agent must be configurable via `trashdig.toml`. Support for Google/VertexAI and OpenRouter is required.
8.  **Security**: Never hardcode API keys. Use environment variables. Ensure `bash_tool` or PoC execution is scoped and safe.
9.  **Data Structuring**: Prefer structured data (Dicts, TypedDicts, or JSON-serializable objects) over raw strings for LLM returns and inter-agent communication whenever possible.

## 📂 Contextual References

*   `README.md`: High-level project goals and user workflow.
*   `TODO.md`: Current progress and upcoming milestones (Phase 1-4).
*   `trashdig.toml`: Central configuration for UI and Agent models.
*   `prompts/`: Directory containing the "brains" of each agent.
