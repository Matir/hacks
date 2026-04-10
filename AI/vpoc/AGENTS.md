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

## Agent Roles

- **Orchestrator Agent**: The central controller that manages the workflow, state, and budget. It maintains a findings database and coordinates the other agents.
- **Source Review Agent**: Responsible for static source code analysis. It uses a parallel worker-pool architecture to execute multiple tools and analyze codebase shards concurrently.
- **PoC Agent**: Takes a potential finding and attempts to generate an exploit script (PoC). It specializes Docker base containers by generating dynamic Dockerfiles to install dependencies.
- **Validation Agent**: Executes the PoC in a hardened Docker sandbox. It monitors the application's response (e.g., crashes, unauthorized access) to confirm the finding's impact.
- **Reporting Agent**: Compiles findings, logs, and PoC results into a final security report for human review.

## Finding Lifecycle & Streaming

To maximize efficiency, VPOC employs a **pipelined analysis** model rather than a batch process.
- **Streaming Handoff**: The Orchestrator does not wait for the Source Review Agent to complete the entire project. As soon as a "Potential Finding" is promoted, it is placed in a **priority-weighted queue**.
- **Concurrent Processing**: The PoC Agent and Validation Agent begin working on findings as they arrive, allowing vulnerability discovery and PoC validation to occur in parallel.
- **Priority Scoring**: Findings are prioritized based on their projected impact (e.g., RCE > XSS) and confidence scores from the Source Review tools.

## Sandbox Hardening (The "Hardened Sandbox")

To safely execute autonomous PoCs, the **Validation Agent** enforces a strict security profile for all target containers:
1. **Runtime Isolation**: Prefer **gVisor (`runsc`)** or **Kata Containers** to provide a strong security boundary between the container and the host kernel. If unavailable, use a restrictive custom **seccomp** profile and **AppArmor/SELinux** policies.
2. **Network Isolation**: Default to `--network none`. If a multi-container target is required, the Orchestrator creates a transient, isolated private bridge with no external egress/ingress.
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

## System Architecture & Interfaces

VPOC operates as a **single unified process** that houses the Orchestrator, all active agents, and the user interfaces.

### 1. Interface Activation
The user controls which interfaces are active via command-line flags:
- `--tui`: Launches the Terminal User Interface for the current project.
- `--web`: Starts the Web Dashboard server.
- Both can be active simultaneously, synchronized via an internal **Pub/Sub Event Bus**.

### 2. Concurrency & Integrity
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
    config.json         # Kickoff configuration
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
- Use python typing. (PEP 484, etc.)
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

### 1. The Orchestrator (`AnalysisRunner`)
- Manages an asynchronous task queue for tool execution.
- Dynamically scales workers based on available system resources and project size.

### 2. Tool Parallelization (Fan-Out)
- Executes multiple static analysis tools (Semgrep, CodeQL, Joern) concurrently using `asyncio` and `ProcessPoolExecutor`.
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
