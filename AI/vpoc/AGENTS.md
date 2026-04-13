# VPOC - Vulnerability Scanner

- See @README.md for an overview of the goals and purpose of the project.
- See @adk-doc-llms.txt for information on using the Google ADK for building
  graph-based LLM-driven workflows.
- See @TODOs.md for a list of standing TODOs.

## Framework & Environment

- This application uses the Google Agent Development Kit (ADK) as its foundation.
- **Dependency Management**: Use `uv` for all package management and virtual environment creation.
- **Virtual Environment**: All development and execution should occur within a `uv`-managed virtualenv.
- **Persistence**: Use **SQLModel** (SQLAlchemy + Pydantic) for ORM and data validation, with **SQLite** as the storage engine.
- **LLM Access**: Use **LiteLlm** uniformly for all LLM calls. Model strings encode the provider (e.g. `gemini/gemini-1.5-pro`, `vertex_ai/gemini-1.5-pro`, `openrouter/anthropic/claude-3-opus`).
- **Web Stack**: **FastAPI** + **Uvicorn** for the web dashboard. **HTMX** + **Jinja2** templates for the frontend (no SPA build pipeline). **Server-Sent Events (SSE)** for real-time browser push; standard POST requests for user actions.
- **TUI Stack**: **Textual** for the terminal interface.

The [source is on Github](https://github.com/google/adk-python) and there is
[documentation for agentic development by LLMs](https://github.com/google/adk-python/blob/main/llms.txt).

## Agent Base Class & Mixin

Rather than a mandatory `VPOCAgent` base class, VPOC uses a **`VPOCMixin`** so each agent can extend the appropriate ADK type directly:

```python
class VPOCMixin:
    project_id: Optional[str] = Field(default=None)
    storage_manager: Optional[StorageManager] = Field(default=None)
    event_bus: Optional[EventBus] = Field(default=None)

class OrchestratorAgent(VPOCMixin, LlmAgent): ...
class SourceReviewAgent(VPOCMixin, BaseAgent): ...
```

`agents/base.py` contains only `VPOCMixin`.

## Agent Dispatch & Communication

- **Dispatch**: The Orchestrator manages sub-agents using **ADK Workflow Agents** (e.g., `SequentialAgent`, `ParallelAgent`). Each sub-agent is a proper ADK agent instance managed by a dedicated runner.
- **Inter-Agent Communication**: Agents communicate through ADK's built-in **Session Service** (e.g., `InMemorySessionService`) and **State** (Session Scratchpad) to maintain context.
- **UI Fanout**: The **EventBus** (`core/events.py`) is supplemented or replaced by **ADK Callbacks** for broadcasting state to UI subscribers (TUI, Web). Agents publish events to the bus; they do not subscribe to it for operational signals.

## Agent Roles & Intelligence Profiles

Each agent combines **Deterministic Logic** (for reliability and speed) with **LLM-Driven Intelligence** (for reasoning and complex synthesis), extending the most appropriate ADK base class.

### 1. Orchestrator Agent (`SequentialAgent`)
- **Deterministic**: An ADK `SequentialAgent` that manages the project lifecycle (Recon → Build → Review → PoC → Validation → Reporting). Handles `CommandEvent` (quick actions) deterministically.
- **LLM-Driven**: Inherits `LlmAgent` capabilities to interpret broad user `HintEvent` messages and adjust project-wide strategy.

### 2. Attack Surface Mapper / Recon Agent (`BaseAgent`)
- **Tool-Driven**: A `BaseAgent` performing static analysis of routing files (e.g., `routes.rb`, `urls.py`) and configuration manifests.
- **LLM-Driven**: Invokes LLM-driven reasoning via ADK's model integration to identify high-value targets (HVTs).

### 3. Environment Architect / Build Agent (`BaseAgent`)
- **Tool-Driven**: A `BaseAgent` executing build commands and capturing output.
- **LLM-Driven**: Interprets compiler/linker errors to suggest fixes.

### 4. Source Review Agent (`ParallelAgent`)
- **Tool-Driven**: An ADK `ParallelAgent` orchestrating concurrent static analysis tools (Semgrep, CodeQL, Joern).
- **LLM-Driven**: Pre-screens findings to filter false positives and assign confidence scores.

### 5. PoC Agent (`LlmAgent`)
- **Tool-Driven**: Staging artifacts and triggering Docker builds.
- **LLM-Driven**: An ADK `LlmAgent` generating exploit scripts and Dockerfiles based on finding context.
- **Artifact Structure** per finding:
  ```
  artifacts/<finding_id>/
    exploit.py          # or exploit.sh
    Dockerfile          # environment for the exploit
    metadata.json       # vuln_type, target_language, exploit hints
    llm_transcript.jsonl  # append-only log of all LLM calls (not in report)
  ```

### 6. Validation Agent (`BaseAgent`)
- **Tool-Driven**: A `BaseAgent` managing the hardened sandbox and monitoring resource usage.
- **LLM-Driven**: Analyzes PoC execution outcomes to determine success.

### 7. Reporting Agent (`LlmAgent`)
- **Tool-Driven**: Template rendering and finding aggregation.
- **LLM-Driven**: An ADK `LlmAgent` synthesizing technical logs into executive summaries and remediation advice.
- **Output**: Markdown only (`workspace/artifacts/report.md`). Full LLM transcripts are saved per-finding in `llm_transcript.jsonl` but are not included in the report.

## Finding Lifecycle & Streaming

VPOC employs a **pipelined analysis** model rather than a batch process.

### Finding States

```
POTENTIAL        # Discovered by a static analysis tool
SCREENED         # LLM pre-screening passed; queued for PoC generation
REJECTED         # LLM pre-screening failed (false positive)
POC_GENERATING   # PoC Agent is writing exploit + Dockerfile
POC_READY        # Artifacts staged; queued for validation
POC_FAILED       # Exploit generation or Docker build failed
VALIDATING       # Running in the hardened sandbox
VALIDATED        # Confirmed exploitable
INCONCLUSIVE     # Sandbox ran but result was ambiguous
AWAITING_HUMAN   # Flagged for human review (e.g. requires network egress exception)
```

Defined as a `FindingStatus` enum in `core/models.py`.

### Priority Scoring

Each finding receives a numeric **priority score** computed at promotion from `POTENTIAL` to `SCREENED`:

```
priority_score = impact_weight[vuln_type] * llm_confidence + recency_bonus
```

- `impact_weight`: Fixed table in `core/models.py` (e.g. RCE=100, SQLi=80, SSRF=70, AuthBypass=70, XSS=40, InfoDisclosure=20).
- `llm_confidence`: Float 0.0–1.0 set by the Source Review Agent's LLM pre-screening step.
- `recency_bonus`: Small constant (+5) to favor freshly discovered findings.
- `cvss_score`: Best-effort CVSS 3.1 base score (float) estimated by the LLM pre-screening step.
- `cvss_vector`: Corresponding CVSS 3.1 vector string.

All four fields (`priority_score`, `llm_confidence`, `cvss_score`, `cvss_vector`) are stored on the `Finding` model.

### Streaming Handoff
- As soon as a finding is promoted to `SCREENED`, it enters the **priority-weighted queue**.
- The PoC Agent and Validation Agent work concurrently on queued findings without waiting for Source Review to complete.

## Source Retrieval

Source retrieval is handled by `SourceFetcher` in `core/source_fetcher.py` — not an agent. The Orchestrator calls it during kickoff.

- **Git**: `git clone --depth=1` (shallow) into `workspace/source/`. **Public repositories only** for MVP. Token-based auth is not supported.
- **Download URL**: `httpx` async download → unpack with `tarfile`/`zipfile` into `workspace/source/`. **Maximum 100MB**.
- **File Upload**: TUI accepts a local path; web interface accepts a multipart POST. Both copy/unpack into `workspace/source/`. **Maximum 100MB**.

## Language Detection

`LanguageDetector` in `core/utils.py` auto-detects project language(s) by counting file extensions, excluding `vendor/`, `node_modules/`, `.git/`, and similar third-party directories.

- A language is included if its files exceed **5% of the total non-vendored file count**.
- Returns a ranked list; **all detected languages** receive their full tool suite concurrently.
- Kickoff config's `target_language` overrides auto-detection if set.

| Extensions | Language | Tools |
|---|---|---|
| `.php` | PHP | Semgrep + Psalm (`--taint-analysis`) |
| `.c`, `.cpp`, `.h` | C/C++ | Semgrep + Joern + CodeQL |
| `.go` | Go | Semgrep + govulncheck |
| `.rs` | Rust | Semgrep + cargo-audit |
| `.lua` | Lua | Semgrep |

## Sandbox Hardening

PoC execution uses `SandboxRunner` in `core/sandbox.py` — a dedicated class separate from `ContainerTool`. It enforces:

1. **Runtime Isolation**: gVisor (`runsc`) by default. Whether gVisor is required is controlled by `[sandbox] require_gvisor` in `config.toml` (default: `true`). If `require_gvisor = true` and gVisor is absent, VPOC exits with a hard error at startup. If `require_gvisor = false` and gVisor is absent, VPOC falls back to seccomp-only with a prominent warning.
2. **Network Isolation**:
    - **Build Phase**: Containers MAY have restricted external network access for official package registries.
    - **PoC/Validation Phase**: `--network none` strictly enforced. Multi-container targets use a transient isolated private bridge with no external egress/ingress. Network exceptions require explicit human approval (`AWAITING_HUMAN` state).
3. **Privilege Reduction**:
    - Non-root user only.
    - `--cap-drop ALL`.
    - `--read-only` root filesystem with `tmpfs` mounts for required writable paths.
4. **Resource Constraints**:
    - **CPU**: Hard limit (default: 0.5 cores).
    - **RAM**: Hard limit (default: 512MB).
    - **PIDs**: Hard limit to prevent fork bombs.

`ContainerTool` (a subclass of `AsyncTool`) is used **only** for static analysis tools (Semgrep, CodeQL, Joern). It mounts `workspace/source/` read-only and does not apply sandbox hardening.

## Human Interaction & Hints

Users communicate with the Orchestrator mid-run via two channels:

- **Free-form hints** (Chat screen / web chat): Published as `HintEvent` on the EventBus (topic: `orchestrator.hint`, payload: `{project_id, text}`). The Orchestrator feeds these into its LLM context on the next reasoning cycle without interrupting in-flight work.
- **Quick actions** (buttons in TUI/Web): Published as `CommandEvent` (topic: `orchestrator.command`, payload: `{project_id, command, args}`). Handled deterministically. Available commands: `PAUSE`, `RESUME`, `SKIP_FINDING`, `PRIORITIZE_RCE`, `MARK_FALSE_POSITIVE`.

Both event types are persisted to a `HintLog` table in `project.db` for inclusion in the audit trail and resumption context.

## Project Initialization (Kickoff)

Every review session starts with a human-guided kickoff wizard, available in both the TUI and web interface. It captures:

- **Project Name**: Human-readable label.
- **Target Description**: Free-text context about the application's purpose and threat model.
- **Source Retrieval**: Public git URL, download URL (zip/tarball, max 100MB), or local file path/web upload (max 100MB).
- **High-Value Targets**: Specific files, directories, or endpoints to prioritize.
- **Build/Environment Hints**: Custom commands for dependency installation or build steps.
- **Target Language Override**: Optional; overrides `LanguageDetector` auto-detection.
- **Exclusions**: Paths or vulnerability types to ignore.

On completion, kickoff:
1. Creates a `Project` record in `~/.vpoc/global.db`.
2. Writes `workspace/<project_id>/config.toml` from wizard inputs (validated as `ProjectConfig`).
3. Calls `SourceFetcher` to populate `workspace/<project_id>/source/`.
4. Instantiates and starts an `OrchestratorAgent` runner for the project.

## TUI Mode

Built with **Textual**. Supports the same kickoff wizard as the web interface (TUI is first-class, not read-only). Screens:

- **Kickoff Screen**: Project initialization wizard.
- **Status Screen**: `DataTable` of agents with current stage and progress indicators; budget status.
- **Chat Screen**: `Input` widget for free-form hints + quick-action buttons. Publishes `HintEvent`/`CommandEvent` to EventBus.
- **Findings Screen**: Filterable `DataTable` of findings with detail panel (CVSS score, priority score, LLM rationale summary, state). Supports Mark False Positive, Skip actions.
- **Log Screen**: `RichLog` widget scrolling raw event bus messages in real time.

## Global Server Configuration (`config.toml`)

Validated by `ServerConfig` Pydantic model in `core/models.py`. The `config.toml` at the repo root sets global defaults; per-project kickoff config is stored in `workspace/<project_id>/config.toml` as `ProjectConfig`.

### Configuration Schema

- **[server]**:
    - `host`: Web dashboard bind interface (default: `127.0.0.1`).
    - `port`: Web dashboard port (default: `8080`).
    - `debug`: Boolean; enables verbose logs.
    - `enable_validation`: Boolean; globally enable/disable PoC and validation (default: `true`).
- **[storage]**:
    - `workspaces_dir`: Base path for all project workspaces (default: `~/.vpoc/workspaces/`).
    - `global_db`: Path to the global database (default: `~/.vpoc/global.db`).
- **[llm]**:
    - `default_model`: Default LiteLlm model string (e.g. `gemini/gemini-1.5-flash`). Provider is encoded in the string.
    - `model_mapping`: Table mapping agent names to LiteLlm model strings (e.g. `SourceReviewAgent = "gemini/gemini-1.5-pro"`).
    - `daily_budget_limit`: Initial default daily token budget (numeric). The live limit is stored in `global.db` and can be updated via any UI without editing this file.
- **[sandbox]**:
    - `require_gvisor`: Boolean; hard-error at startup if gVisor is absent (default: `true`).
    - `runtime`: Container runtime to use (default: `runsc`).
    - `max_concurrent_containers`: Global limit on concurrent validation sandboxes.
    - `default_cpu_limit`: Default CPU cores for validation containers (default: `0.5`).
    - `default_memory_limit`: Default RAM for validation containers (default: `512m`).
- **[logging]**:
    - `level`: Minimum log level (e.g. `INFO`, `DEBUG`).
    - `format`: Log format (`text` or `json`).

## System Architecture & Interfaces

VPOC operates as a **single unified process**. Multiple projects can be architecturally supported (no global singletons, all state scoped to `project_id`); MVP runs one project at a time in practice.

### Interface Activation
- `--tui`: Launches the Textual TUI.
- `--web`: Starts the FastAPI/Uvicorn web dashboard.
- Both can be active simultaneously, synchronized via the EventBus.

### Pub/Sub Event Bus (`core/events.py`)
- **Fan-Out**: Every UI subscriber gets its own `asyncio.Queue`.
- **Async-First**: Native asyncio with thread-safe publishing.
- **Scope**: UI fanout only. Not used for agent-to-agent signaling.
- **Event Schema**: Pydantic `Event` model (topic, payload, timestamp, event_id).
- **Key Topics**: `orchestrator.hint`, `orchestrator.command`, `finding.updated`, `agent.status`, `log.line`, `budget.alert`.

### Web Real-Time Updates
- **Server-Sent Events (SSE)**: FastAPI SSE endpoint subscribes to the EventBus and streams filtered events to each connected browser. HTMX `hx-ext="sse"` handles client-side updates.
- **User Actions**: Standard HTMX POST requests (hints, quick actions, budget updates).

## Data Storage & Persistence

### Global Storage (`~/.vpoc/global.db`) — `GlobalStorageManager`
Shared across all projects. Contains:
- **`Project`**: Project ID, name, status (`INITIALIZING`, `RUNNING`, `PAUSED`, `COMPLETE`, `FAILED`), created/updated timestamps.
- **`TokenUsage`**: Per-call token records with `project_id`, `agent_name`, `model`, `tokens_in`, `tokens_out`, `timestamp`. Queried by date for daily budget totals.
- **`BudgetConfig`**: Live daily limit (updated via UI without config file edits). Resets at midnight UTC.

### Project Storage (`workspace/<project_id>/project.db`) — `StorageManager`
Isolated per project. Contains:
- **`Finding`**: Full finding record including `FindingStatus`, `priority_score`, `llm_confidence`, `cvss_score`, `cvss_vector`, evidence, and summarized LLM rationale.
- **`ExecutionLog`**: PoC generation and validation attempts with container IDs, exit codes, and output logs.
- **`AgentCheckpoint`**: Resumption state per agent. Fields: `agent_name`, `finding_id` (nullable), `stage`, `state_json`, `updated_at`. Source Review uses per-file granularity (`stage="FILE_COMPLETE"`, `state_json={"file": "...", "tool": "...", "finding_ids": [...]}`).
- **`HintLog`**: All `HintEvent` and `CommandEvent` records for audit trail and resumption.

### Workspace Structure
```text
~/.vpoc/
  global.db                   # Global storage (projects, budget, token usage)
  workspaces/
    <project_id>/
      source/                 # Target source code
      artifacts/
        report.md             # Final Markdown report
        <finding_id>/
          exploit.py          # Generated exploit script
          Dockerfile          # Exploit environment
          metadata.json       # vuln_type, hints (not success criteria)
          llm_transcript.jsonl  # Append-only LLM call log
      project.db              # Per-project SQLite database
      config.toml             # ProjectConfig (kickoff inputs)
```

### Concurrency
SQLite configured in **WAL mode** for all databases. Orchestrator is instanced per-project with no global singletons.

## Budget Enforcement

`BudgetManager` in `core/budget.py`:
- Loads today's token spend from `global.db` on init.
- `check_budget(estimated_tokens) -> bool` called before each LLM invocation.
- Raises `BudgetExhaustedError` if the cap would be exceeded.
- When exhausted: in-flight LLM calls complete, then all agents stop cleanly. All connected UIs display a budget prompt with a field to set a new daily limit.
- Token counts sourced from LiteLlm response metadata; written to `global.db` after each call.

## Prompt Management

`PromptLoader` in `core/utils.py`:
- Loads prompts from `prompts/<agent_name>.md` or `prompts/<agent_name>/<prompt_name>.md`.
- Uses `{placeholder}` Python string formatting.
- **Strict validation**: Raises `PromptRenderError` (listing all missing variables) if any placeholder is unsatisfied.
- Caches file reads in memory after first load.

## Coding Style

- All code must conform to PEP-8.
- All public functions and methods must have pydoc-ready docstrings.
- Private functions and methods begin with `_`.
- Use classes to encapsulate state and behavior; prefer OOP.
- Prefer importing modules over individual names (e.g. `import os` not `from os import path`).
- Granular exception handling — no broad `except Exception` blocks.
- Unit tests for all complex logic. Stub all LLM calls in tests.
- Type hints required on all functions, methods, and class variables (PEP 484).
- All imports should be at the top of the file unless there's an architectural reason why it cannot be.
- Prompts loaded from `.md` files via `PromptLoader`; never inlined.
- Tools placed in `tools/`; agents placed in `agents/`.

### Tool Execution Strategy
- `AsyncTool` (base): Abstract base for all tools.
- `ContainerTool` (subclass of `AsyncTool`): For static analysis tools only (Semgrep, CodeQL, Joern). Mounts `workspace/source/` read-only. No sandbox hardening.
- `SandboxRunner` (`core/sandbox.py`): For PoC execution only. Applies full sandbox hardening profile.

### Error Handling & Tool Failures
- Tools MUST NOT fail silently. Use the standardized `ToolError` schema.
- `ToolError` includes: `tool_name`, `error_type` (`BUILD_FAILURE`, `RUNTIME_ERROR`, `TIMEOUT`), `stderr_tail`, `suggested_fix` (optional, LLM-provided).

### Configuration Management
- `ServerConfig` (in `core/models.py`): Validates global `config.toml`.
- `ProjectConfig` (in `core/models.py`): Validates per-project kickoff `config.toml`. Single source of truth for `build_hints`, `excluded_paths`, `target_language`, `high_value_targets`.

## Maintenance & Process

- **TODO List**: Do not remove items from the TODO list unless they are explicitly abandoned. Mark completed items with an `[x]` instead of deleting them.

## Tool Integration Strategy: Source Analysis

### 1. Semgrep Integration (`tools/semgrep.py`)
- **Purpose**: Fast, pattern-based scanning for security anti-patterns and known vulnerabilities.
- **Workflow**: Runs `semgrep scan --json` with language-appropriate rulesets; parses findings into VPOC internal schema.
- **Execution**: Via `ContainerTool` (Docker-isolated).

### 2. CodeQL Integration (`tools/codeql.py`)
- **Purpose**: Deep semantic analysis and data-flow tracing.
- **Workflow**: Database creation (using kickoff build hints) → `codeql database analyze` → SARIF → VPOC schema.
- **Execution**: Via `ContainerTool`.

### 3. Joern Integration (`tools/joern.py`)
- **Purpose**: Graph-based Code Property Graph analysis for C/C++ and Go.
- **Workflow**: CPG generation → reachability queries (source-to-sink).
- **Execution**: Via `ContainerTool`.

### 4. Language-Specific Tools
- **PHP**: Psalm `--taint-analysis`.
- **Go**: govulncheck.
- **Rust**: cargo-audit.

### 5. Orchestration Logic (`LanguageDetector` + Source Review Agent)
- `LanguageDetector` selects applicable tools based on detected language(s).
- All applicable tools run concurrently (Fan-Out).
- Results are deduplicated, correlated, and LLM-pre-screened (Fan-In).

## Parallel Analysis Architecture

### Fan-Out
- Source Review Agent runs all applicable tools concurrently via `asyncio.Semaphore`.
- Pattern tools (Semgrep, Psalm) additionally shard the codebase by file for parallelism.
- Deep-analysis tools (CodeQL, Joern) maintain global context while running in parallel.

### Fan-In
- Central aggregation deduplicates findings across tools and shards.
- Correlation cross-references findings (e.g. Semgrep pattern + Joern data-flow path → higher confidence).
- LLM pre-screening assigns `llm_confidence` and `cvss_score` before promotion to `SCREENED`.

## Building Features

When asked to build a feature, only build out what has been requested and the appropriate tests. Ask before continuing.

### Validation Requirements
Every change **must** be validated before completion:
1. **Linting**: `flake8` + `mypy`.
2. **Testing**: `pytest`.
3. **Preferred**: `mise run check` (lint + test concurrently).

**Available Mise Tasks:**
- `mise run lint`: Runs `flake8` and `mypy`.
- `mise run test`: Runs `pytest`.
- `mise run fix`: Auto-formats with `black`.
- `mise run check`: Combined lint and test.
