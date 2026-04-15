# TrashDig: Agent Foundation & Mandates

TrashDig is an AI-powered, language-agnostic vulnerability scanner and security research assistant. It is built on the **Agent Development Kit (ADK)** and leverages a decentralized, agentic architecture to map codebases, trace data flows, and verify security findings.

## 🏗 Architecture & Agent Personas

TrashDig operates as a team of specialized agents coordinated by a top-level **Coordinator Agent**. Unlike scripted workflows, TrashDig uses ADK's native delegation, where the Coordinator dynamically assigns tasks to sub-agents.

1.  **Coordinator Agent (Orchestrator)**:
    *   **Role**: Strategic Lead.
    *   **Tasks**: High-level planning, delegation to specialized agents, and cross-agent state management.
    *   **Goal**: Oversee the end-to-end vulnerability discovery lifecycle.
2.  **Recon Suite (Sub-Agents)**:
    *   **StackScout Agent**:
        *   **Role**: Hybrid Environment Detection.
        *   **Tasks**: Detects framework/tech stacks using deterministic checks and LLM inference.
        *   **Goal**: Build a project profile and initial hunt hypotheses.
    *   **WebRouteMapper Agent**:
        *   **Role**: Attack Surface Mapper.
        *   **Tasks**: Uses AST-aware parsing to map all web endpoints (e.g., Express routes, FastAPI decorators).
        *   **Goal**: Generate a structured artifact of the application's attack surface.
3.  **Hunter Agent (Sub-Agent)**:
    *   **Role**: Deep-Dive Researcher.
    *   **Tasks**: Performs hypothesis-driven analysis, AST-aware taint analysis, and **Cross-File** symbol tracing.
    *   **Goal**: Connect untrusted user input to dangerous sinks.
4.  **Verification Pipeline (Sub-Agents)**:
    *   **Skeptic Agent**:
        *   **Role**: Adversarial Reviewer.
        *   **Tasks**: Pre-validation gate for all Hunter findings. Attempts to debunk findings by identifying missed sanitizers or logic-level defenses.
        *   **Goal**: Reduce false positives and ensure high-quality findings.
    *   **Validator Agent**:
        *   **Role**: Proof-of-Concept Specialist.
        *   **Tasks**: Generates and executes PoC scripts in a containerized environment to prove reachability and exploitability.
        *   **Goal**: Empirical proof of vulnerability.

## 🛠 Technical Stack & ADK Integration

TrashDig is designed to be "ADK-Native," leveraging the framework's high-level abstractions for orchestration and state:

*   **Orchestration**: Uses ADK's `LlmAgent` with `sub_agents` for dynamic delegation. The manual Python task loop is replaced by an agentic "brain" that decides which tool or agent to call next.
*   **State & Memory**: Uses ADK `SessionService` and `MemoryService` to maintain shared context across all agents. This ensures that the Hunter agent understands the project structure discovered by StackScout without redundant re-analysis.
*   **Observability (Callbacks)**: Employs a unified `TrashDigCallback` (inheriting from ADK's `BaseCallback`) to handle real-time TUI updates, cost tracking, and database logging.
*   **Artifacts**: Uses the native **ADK Artifact API** to manage large tool outputs (ASTs, call graphs, scan results), ensuring context efficiency by referencing files instead of inlining massive text blocks.
*   **Static Analysis**: `tree-sitter` (AST parsing), `semgrep` (pattern matching), `ripgrep` (fast search).
*   **Services Layer**:
    *   **ProjectDatabase**: ADK-compatible storage for findings, symbols, and session history.
    *   **CostTracker**: Integrated into the ADK callback chain for real-time USD monitoring.
    *   **PermissionManager**: ADK `Tool` wrapper that intercepts calls based on security policies (e.g., TUI confirmation for unsandboxed commands).
*   **Isolation**: PoCs are executed in isolated **Docker containers** (Validator) or **Minijail** sandboxes (Hunter tools) to ensure host safety.

## 🛡️ Security & Tool Sandboxing

## 🛡️ Security & Tool Sandboxing

To ensure the safety of the host system during automated research and PoC execution, TrashDig employs a multi-layered sandboxing strategy for all external tool invocations (e.g., `bash_tool`, `semgrep`, `ripgrep`).

### Sandboxing Architecture
*   **Abstraction Layer**: A unified `Sandbox` interface (`src/trashdig/sandbox/`) abstracts OS-specific sandboxing technologies.
*   **Linux Implementation**: Uses `minijail` to provide a restricted execution environment.
    *   **Filesystem Isolation**: The sandbox only sees the project workspace. The rest of the user's home directory is hidden.
    *   **Permissions**: Tools run as the current user to maintain file ownership but are restricted from writing outside the workspace.
    *   **Network**: Network access is enabled by default but can be toggled per-tool.
    *   **Allowlisting**: The sandbox includes read-only mounts for standard system binaries and libraries (e.g., `/bin`, `/usr`, `/lib`, `/etc/ssl/certs`) to ensure tool functionality while preventing host compromise.
*   **Logic-Level Gatekeeping**: Controlled by the `PermissionManager` service and the `require_sandbox` setting in `trashdig.toml` (default: `True`).

## 🛡️ Enhanced Taint Analysis (Phase 3)

The Hunter agent uses a multi-stage approach to trace untrusted data:
1.  **Intra-file Taint**: Identify local data flow from sources to sinks within a single function or module.
2.  **Cross-file Tracing**: Use `trace_taint_cross_file` to follow data into callees, resolving parameter names across module boundaries.
3.  **Semantic Resolution**: Leverages `tree-sitter` to distinguish between simple variable usages and assignments/sinks.

## 📜 Engineering Standards (The Rules)

These rules are foundational. Adhere to them for all modifications:

1.  **Testing**: Always provide unit tests in the `tests/` directory. All code should be written alongside corresponding tests. Whenever features are added, both the test suite and coverage must be checked; coverage metrics should generally trend upwards.
2.  **Typing**: Strict type hints are mandatory (`pyright`/`mypy` clean).
3.  **Environment**: Use `uv` for dependencies and `mise` for task orchestration.
4.  **Documentation**: Add descriptive docstrings (Google style) to all classes and functions.
5.  **Prompt Management**: Keep agent prompts in separate `.md` files within the `prompts/` directory.
6.  **Data Structuring**: Prefer structured data (Dicts, TypedDicts, or JSON-serializable objects) over raw strings for inter-agent communication.

## 📂 Contextual References

*   `README.md`: High-level project goals and user workflow.
*   `TODO.md`: Current progress and upcoming milestones.
*   `trashdig.toml`: Central configuration for UI and Agent models.
*   `prompts/`: Directory containing the "brains" of each agent.
