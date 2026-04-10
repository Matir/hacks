# VPOC TODO List (MVP Prioritized)

- [ ] **P0: Core Workflow Engine**
  - [ ] [P0] Bootstrap ADK Framework (Orchestrator base)
  - [ ] [P0] Build Agents:
    - [ ] [P0] **Source Review Agent**
      - [x] Implement `AnalysisRunner` for parallel tool execution
      - [ ] [P0] Implement `SemgrepTool` integration (Easiest P0 tool)
      - [ ] [P1] Implement `CodeQLTool` integration
      - [ ] [P2] Implement `JoernTool` integration
      - [ ] [P2] Implement language-specific tools (Psalm, govulncheck, cargo-audit)
    - [ ] [P0] **PoC Agent** (Dynamic Dockerfile generation, exploit scripting)
    - [ ] [P0] **Validation Agent** (Sandboxed execution, result monitoring)
  - [ ] [P0] Build Orchestrator & State Management:
    - [x] Implement `StorageManager` and database schema
    - [ ] [P0] Lifecycle management for findings (POTENTIAL -> POC -> VALIDATED)
    - [ ] [P0] **Priority-Weighted Queue** (Stream findings from discovery to PoC)
    - [ ] [P0] **Sandbox Hardening Profile** (Implement gVisor/seccomp/resource constraints)
    - [ ] [P1] Findings database/JSON schema (Refine based on agent output)

- [ ] **P1: Usability & Configuration**
  - [ ] [P1] Build TUI Mode (Single-Project Focused):
    - [ ] [P1] Status Screen (Activity monitoring)
    - [ ] [P1] Chat Screen (Interactive guidance)
    - [ ] [P1] Findings Screen (Triage)
    - [ ] [P1] Log Screen (Execution logs)
  - [ ] [P1] Build Web Interface:
    - [ ] [P1] Project Initialization Wizard (git/URL/upload, hints)
    - [ ] [P1] Real-time Interactive Dashboard (Basic view of findings)
  - [ ] [P1] Provide configuration interface for vpoc:
    - [ ] [P1] Base workspace directory
    - [ ] [P1] Model providers configuration
    - [ ] [P1] Registry of Docker base containers for supported languages
    - [ ] [P2] Listening port for web interface
    - [ ] [P2] Per-agent model assignment

- [ ] **P2: Management & Reporting**
  - [ ] [P2] State Persistence & Resumption:
    - [ ] [P2] Implement checkpointing for agents
    - [ ] [P2] Implement stateless re-entry for the Orchestrator
  - [ ] [P2] Build Web Interface:
    - [ ] [P2] Finding triage (Approve/Reject, Provide hints)
    - [ ] [P2] Show running/paused status
  - [ ] [P2] **Reporting Agent** (Final report generation)
  - [ ] [P2] Token usage tracking and budget enforcement

- [ ] **P3: Advanced Features**
  - [ ] [P3] Deterministic daily budget cap (Hard limit)
  - [ ] [P3] Separate secret storage for API keys
  - [ ] [P3] Budget alerts in dashboard

- [x] **Completed Tasks**
  - [x] Initialize project environment with `uv` and `virtualenv`
  - [x] Add `sqlmodel` dependency
  - [x] Add code quality tools (flake8, mypy, black) and `mise` tasks
