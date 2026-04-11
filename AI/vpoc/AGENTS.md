# VPOC - Vulnerability Scanner

- See @README.md for an overview of the goals and purpose of the project.
- See @TODOs.md for a list of standing TODOs.

## Framework & Environment

- This application uses the Google Agent Development Kit (ADK) as its foundation.
- **Dependency Management**: Use `uv` for all package management and virtual environment creation.
- **Virtual Environment**: All development and execution should occur within a `uv`-managed virtualenv.
- **Persistence**: Use **SQLModel** (SQLAlchemy + Pydantic) for ORM and data validation, with **SQLite** as the storage engine.

The [source is on Github](https://github.com/google/adk-python) and there is
[documentation for agentic development by LLMs](https://github.com/google/adk-python/blob/main/llms.txt).

## Agent Roles & Intelligence Profiles

Each agent in VPOC combines **Deterministic Logic** (for reliability and speed) with **LLM-Driven Intelligence** (for reasoning and complex synthesis).

### 1. Orchestrator Agent
- **Deterministic**: State machine management, budget enforcement, finding lifecycle transitions, database transactions, and event broadcasting (Pub/Sub).
- **LLM-Driven**: Interpreting broad user hints to adjust project-wide strategy and resolving conflicts between agent findings.

### 2. Attack Surface Mapper (Recon Agent)
- **Tool-Driven**: Static analysis of routing files (e.g., `routes.rb`, `urls.py`), configuration files (`docker-compose.yml`), and dependency manifests.
- **LLM-Driven**: Reasoning about the *semantic importance* of endpoints (e.g., identifying high-value targets like authentication or payment flows) and inferring hidden parameters from naming conventions.

### 3. Environment Architect (Build Agent)
- **Tool-Driven**: Executing build commands (`make`, `npm install`, `cmake`), capturing exit codes, and parsing standard error output.
- **LLM-Driven**: Interpreting complex compiler/linker errors to suggest missing system libraries and synthesizing build hints from unstructured `README.md` or `INSTALL` files.

### 4. Source Review Agent
- **Tool-Driven**: Orchestrating static analysis tools (Semgrep, CodeQL, Joern), sharding codebases, and deduplicating raw findings.
- **LLM-Driven**: Pre-screening tool findings to filter out false positives and correlating disparate "weak signals" into a coherent vulnerability hypothesis.

### 5. PoC Agent
- **Tool-Driven**: Staging files to the filesystem and triggering Docker image builds.
- **LLM-Driven**: Generating the exploit script (Python/Bash) and synthesizing specialized Dockerfiles to install dependencies for the specific exploit.

### 6. Validation Agent
- **Tool-Driven**: Managing the hardened Docker sandbox (gVisor/seccomp), monitoring container resource usage (CPU/RAM peaks), and capturing execution logs.
- **LLM-Driven**: Analyzing the *outcome* of a PoC execution (e.g., "The heap dump confirms a buffer overflow" vs "The 500 error was a generic timeout").

### 7. Reporting Agent
- **Tool-Driven**: Markdown/PDF template rendering and finding-log aggregation.
- **LLM-Driven**: Synthesizing technical logs into human-readable executive summaries, impact assessments, and remediation advice.

## Finding Lifecycle & Streaming

To maximize efficiency, VPOC employs a **pipelined analysis** model rather than a batch process.
- **Streaming Handoff**: The Orchestrator does not wait for the Source Review Agent to complete the entire project. As soon as a "Potential Finding" is promoted, it is placed in a **priority-weighted queue**.
- **Concurrent Processing**: The PoC Agent and Validation Agent begin working on findings as they arrive, allowing vulnerability discovery and PoC validation to occur in parallel.
- **Priority Scoring**: Findings are prioritized based on their projected impact (e.g., RCE > XSS) and confidence scores from the Source Review tools.

## Sandbox Hardening (The "Hardened Sandbox")

To safely execute autonomous PoCs, the **Validation Agent** enforces a strict security profile for all target containers:
1. **Runtime Isolation**: Prefer **gVisor (`runsc`)** or **Kata Containers** to provide a strong security boundary between the container and the host kernel. If unavailable, use a restrictive custom **seccomp** profile and **AppArmor/SELinux** policies.
2. Network Isolation: 
    - **Build Phase**: During environment setup and dependency resolution, containers MAY be granted restricted external network access to reach official package registries (e.g., npm, PyPI, crates.io).
    - **PoC/Validation Phase**: Egress is strictly prohibited (`--network none`) during the execution of PoCs to prevent data exfiltration or unintended impact. If a multi-container target is required, the Orchestrator creates a transient, isolated private bridge with no external egress/ingress. Exceptions are only permitted if the vulnerability specifically requires network interaction, and must be explicitly flagged for human approval.

3. **Privilege Reduction**:
    - Containers MUST run as a non-root user.
    - All capabilities are dropped (`--cap-drop ALL`).
    - The root filesystem is mounted as **read-only** (`--read-only`), with only specific, temporary `tmpfs` mounts for required writable paths.
4. **Resource Constraints**:
    - **CPU**: Hard limit (default: 0.5 cores).
    - **RAM**: Hard limit (default: 512MB).
    - **PIDs**: Limit the maximum number of processes to prevent fork bombs.

## Project Initialization (Kickoff)

Every review session must start with a human-guided kickoff phase. This is handled via a wizard in the web interface or a specialized TUI mode for single projects. It captures:
- **Target Description**: Free-text context about the application's purpose and threat model.
- **Source Retrieval**: Supports git URLs, download URLs (e.g., zip/tarball), or direct file uploads.
- **High-Value Targets**: Specific files, directories, or endpoints to prioritize.
- **Build/Environment Hints**: Custom commands for dependency installation or build steps.
- **Exclusions**: Paths or vulnerability types to ignore.

## TUI Mode

VPOC provides a terminal-based interface optimized for single-project analysis. It supports multiple "screens" for interactive sessions:
- **Status Screen**: Real-time overview of agent activity, tool progress, and budget status.
- **Chat Screen**: Interactive communication with the Orchestrator for providing hints and guiding analysis.
- **Findings Screen**: View, triage, and explore potential and validated findings.
- **Log Screen**: Real-time, multiplexed execution logs from all active agents and tools, synchronized via an internal Pub/Sub event bus.

## Global Server Configuration (`config.toml`)

VPOC uses a top-level `config.toml` file to manage global settings and defaults. This configuration MUST be validated using a centralized Pydantic model (`ServerConfig`) defined in `core/models.py`.

### 1. Configuration Schema
The global configuration should include the following sections and entries:

- **[server]**:
    - `host`: The interface for the web dashboard to bind to (default: `127.0.0.1`).
    - `port`: The port for the web dashboard (default: `8080`).
    - `debug`: Boolean flag to enable verbose debugging logs and TUI features.
- **[storage]**:
    - `workspaces_dir`: The base path where all project analysis data is stored (default: `~/.vpoc/workspaces/`).
- **[llm]**:
    - `default_provider`: The preferred AI platform (e.g., `vertexai`, `openai`).
    - `model_mapping`: A table mapping agent names to specific model versions (e.g., `SourceReviewAgent = "gemini-1.5-pro"`).
    - `daily_budget_limit`: A hard numeric cap on total token expenditure across all projects.
- **[sandbox]**:
    - `runtime`: The container runtime to use (default: `runsc` for gVisor).
    - `max_concurrent_containers`: Global limit on concurrent validation sandboxes.
    - `default_cpu_limit`: Default CPU core allocation for validation containers.
    - `default_memory_limit`: Default RAM allocation for validation containers.
- **[logging]**:
    - `level`: Minimum log level (e.g., `INFO`, `DEBUG`).
    - `format`: Logging format (e.g., `text` or `json`).

## System Architecture & Interfaces

VPOC operates as a **single unified process** that houses the Orchestrator, all active agents, and the user interfaces.

### 1. Interface Activation
The user controls which interfaces are active via command-line flags:
- `--tui`: Launches the Terminal User Interface for the current project.
- `--web`: Starts the Web Dashboard server.
- Both can be active simultaneously, synchronized via an internal **Pub/Sub Event Bus**.

### 2. Pub/Sub Event Bus (`core/events.py`)
VPOC uses an asynchronous, in-process event bus based on `asyncio.Queue` for real-time synchronization:
- **Fan-Out Architecture**: Every subscriber (TUI, Web, Orchestrator) receives its own dedicated queue.
- **Async-First**: Native support for the ADK `asyncio` loop, with thread-safe publishing for synchronous agents.
- **Event Schema**: All messages follow a strict Pydantic-based `Event` model (topic, payload, timestamp).

### 3. Concurrency & Integrity
- **Single Process**: All components share a single memory space for the Event Bus, ensuring real-time responsiveness.
- **Transactional DB**: All state transitions in the `project.db` (findings triage, budget updates, agent checkpoints) MUST be performed within ACID-compliant transactions to prevent race conditions between the TUI, Web, and background agents.

## Data Storage & Persistence

To ensure isolation and traceability, VPOC employs a **Project Workspace** architecture. Each analysis session is isolated within its own directory and database.

### 1. Workspace Structure
Workspaces are stored in a configurable base directory (default: `~/.vpoc/workspaces/`):
```text
/workspaces/
  <project_id>/
    source/             # Target source code
    artifacts/          # Generated Dockerfiles, exploits, logs
    project.db          # SQLite database (SQLModel)
    config.toml         # Kickoff configuration
```

### 2. State Management & Resumption
A core mandate of VPOC is **state durability**. Every agent execution must record enough state to allow for seamless resumption after a stop or crash.
- **Checkpointing**: Agents periodically save their current progress, context, and tool outputs to the `project.db`.
- **Stateless Re-entry**: Upon restart, the Orchestrator reads the last recorded state and re-initializes agents at their last known point of progress without significant loss of quality or redundant token usage.

### 3. Centralized Storage Manager (`StorageManager`)
A dedicated `StorageManager` class handles all database interactions:
- **Findings**: Stores potential, validated, and rejected findings with full LLM rationale and tool metadata.
- **Executions**: Logs PoC generation and validation attempts, including container IDs and exit codes.
- **Budgeting**: Tracks token usage (input/output) per agent and model for deterministic cost control.

### 4. Concurrency
SQLite is configured in **WAL (Write-Ahead Logging)** mode to support concurrent read/write operations from multiple specialized agents (Orchestrator, Source Review, PoC, etc.).

## Coding Style

- All code should conform to PEP-8.
- All public functions and methods should have pydoc-ready docstrings.
- Private functions and methods should begin with `_`.
- Use classes wherever it makes sense to encapsulate things. Build as if it is
  object-oriented whenever it makes sense.
- Prefer importing modules over importing individual classes (e.g., `import os` instead of `from os import path`).
- Ensure granular exception handling (avoid broad `except Exception` blocks).
- Build unit tests for any complex code.
- Always stub out calls to real LLMs in Unit Tests.
- Use python typing. (PEP 484, etc.) All functions, methods, and class variables MUST have explicit type hints.
- Prompts for agents MUST be loaded from separate `.md` (Markdown) files and NOT in-lined into the source code.
    - Path structure: `prompts/<agent_name>.md` or `prompts/<agent_name>/<prompt_name>.md` for multi-prompt agents.
    - Implementation: Use a centralized `PromptLoader` utility in `core/utils.py`.
- Tool Execution Strategy:
    - Tools MUST support both host-based execution and Docker-based isolation.
    - Implement `ContainerTool` as a subclass of `AsyncTool` for tools requiring sandbox isolation.
- Error Handling & Tool Failures:
    - Tools MUST NOT fail silently. Use a standardized `ToolError` schema.
    - A `ToolError` should include: `tool_name`, `error_type` (e.g., BUILD_FAILURE, RUNTIME_ERROR, TIMEOUT), `stderr_tail`, and `suggested_fix` (optionally provided by an LLM).
- Configuration Management:
    - All project configurations MUST be validated using a centralized Pydantic model (`ProjectConfig`) defined in `core/models.py`.
    - TOML (`config.toml`) is the required format for persistent configuration files to ensure human readability and structural integrity.
    - This model is the single source of truth for `build_hints`, `excluded_paths`, and `target_language`.
- Place individual agents in `agents/`.
- Place tools in `tools/`.

## Maintenance & Process

- **TODO List**: Do not remove items from the TODO list unless they are explicitly abandoned. Mark completed items with an `[x]` instead of deleting them.

## Tool Integration Strategy: Source Analysis

To enhance vulnerability discovery, VPOC integrates industry-standard static analysis tools as ADK-compatible tools orchestrated by the **Source Review Agent**.

### 1. Semgrep Integration (`tools/semgrep.py`)
- **Purpose**: Fast, pattern-based scanning for security anti-patterns and known vulnerabilities.
- **Workflow**: Runs `semgrep scan --json` on the target source and parses findings into the VPOC internal schema.
- **Strength**: High speed and broad coverage for multi-language configurations.

### 2. CodeQL Integration (`tools/codeql.py`)
- **Purpose**: Deep semantic analysis and data-flow tracing to find complex vulnerabilities (e.g., untrusted source to dangerous sink).
- **Workflow**:
    1. **Database Creation**: Uses build hints from the kickoff phase to generate a CodeQL database.
    2. **Analysis**: Executes standard security query suites (`codeql database analyze`).
    3. **Parsing**: Converts SARIF output into the VPOC internal schema.
- **Strength**: Precision in identifying reachability and complex logic flaws.

### 3. Joern Integration (`tools/joern.py`)
- **Purpose**: Graph-based code analysis via Code Property Graphs (CPG).
- **Workflow**: Generates a CPG and allows the **Source Review Agent** to perform complex reachability queries (e.g., source-to-sink analysis for C/C++ and Go).
- **Strength**: Unrivaled for mapping structural relationships and data flow in compiled languages.

### 4. Language-Specific Tools
- **PHP**: **Psalm** with `--taint-analysis` for fast, PHP-specialized vulnerability discovery.
- **Go**: **govulncheck** for finding reachable vulnerabilities in dependencies.
- **Rust**: **cargo-audit** to identify known security advisories in the crate graph.

### 5. Orchestration Logic
The **Source Review Agent** acts as the synthesis layer:
- **Selection**: Auto-detects project language and invokes the relevant tool(s).
- **Deduplication**: Merges overlapping findings from different tools.
- **LLM Pre-screening**: Uses an LLM to validate the context of findings before promoting them to the PoC Agent, reducing false positives.

## Parallel Analysis Architecture

To achieve high-performance scanning, VPOC employs a **Fan-Out / Fan-In** pattern for source analysis:

### 1. The Source Review Agent (`agents/source_review_agent.py`)
- Manages an asynchronous task queue for tool execution.
- Dynamically scales workers based on available system resources and project size using `asyncio.Semaphore`.

### 2. Tool Parallelization (Fan-Out)
- Executes multiple static analysis tools (Semgrep, CodeQL, Joern) concurrently using `asyncio` and the agent's internal task runner.
- Isolates tool-specific dependencies by running them within specialized Docker containers where appropriate.

### 3. Codebase Sharding
- For pattern-based tools, the **Source Review Agent** shards the codebase into logical directories/packages to analyze them in parallel.
- Deep-analysis tools (CodeQL/Joern) maintain global context while running in parallel with other tools.

### 4. Result Synthesis (Fan-In)
- A central aggregation engine collects findings from all workers.
- **Deduplication**: Merges overlapping findings from different shards or tools.
- **Correlation**: Cross-references findings (e.g., a Semgrep pattern match confirmed by a Joern data-flow path) to increase confidence scores.

## Building Features

When asked to build a feature, only build out what's been requested and the
appropriate tests. Ask before continuing on.

### Validation Requirements
Every change **must** be validated using the following tools before completion:
1. **Linting**: Use `flake8` for style violations and `mypy` for static type checking.
2. **Testing**: Use `pytest` for unit and integration tests.
3. **Mise Integration**: Prefer running `mise run check` to execute all validation steps (linting + testing) concurrently.

**Available Mise Tasks:**
- `mise run lint`: Runs `flake8` and `mypy`.
- `mise run test`: Runs `pytest`.
- `mise run fix`: Auto-formats code (using `black`).
- `mise run check`: Combined lint and test.
