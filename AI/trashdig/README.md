# 💎 TrashDig: AI-Powered Vulnerability Research Assistant

TrashDig is a multi-agent, language-agnostic vulnerability scanner and security research assistant. It uses LLMs (like Gemini) to map complex project structures, trace data flows, and automatically identify security vulnerabilities that traditional tools often miss.

---

## 🚀 Key Features

*   **Multi-Agent Intelligence**: Built on the Google Agent Development Kit (ADK), featuring specialized agents:
    *   **StackScout**: Hybrid environment detection (deterministic + LLM inference).
    *   **WebRouteMapper**: Deep attack surface mapping for web applications.
    *   **Hunter**: Autonomous, hypothesis-driven depth-first analysis with cross-file taint tracing.
    *   **Skeptic**: Adversarial reviewer that critques findings to reduce false positives.
    *   **Validator**: Containerized Proof-of-Concept (PoC) generation and verification.
*   **Context Compaction**: Automated history pruning and summarization to handle long-running research sessions without exceeding model token limits.
*   **Parallel Execution**: Asynchronous task processing with a worker-pool pattern to scan projects faster.
*   **Safety Middleware**: Logic-level permission management and tool sandboxing (Docker/Minijail).
*   **Persistent Intelligence**: SQLite-backed **ProjectDatabase** for findings, symbols, and session persistence.

---

## 🤖 Agent Architecture

TrashDig uses a pipeline of specialized agents coordinated by a central **Coordinator**.

### Recon Suite
*   **StackScout**: Builds a project profile by combining file-signature detection with LLM analysis.
*   **WebRouteMapper**: (Conditional) Deep-dives into entry points if a web stack is detected.

### Hunter
Performs deep-dive analysis on prioritized targets. It uses **semgrep** for patterns and **tree-sitter** for semantic taint analysis, following data flows across module boundaries until it identifies a vulnerable sink.

### Verification Pipeline
*   **Skeptic**: Acts as a "Socratic Debunker," attempting to find logic flaws or mitigations in the Hunter's findings.
*   **Validator**: For findings that survive the Skeptic, it generates a Python/Bash PoC and executes it in an isolated **Docker** container to prove exploitability.

### Agent Relationship Diagram

```mermaid
flowchart TD
    User([User / TUI]) -->|scan path| C[Coordinator]
    User -->|star targets| C
    User -->|verify finding| C

    C -->|SCAN task| SS[StackScout]
    SS -->|Project Profile| C
    C -.->|If WebApp| WRM[WebRouteMapper]
    WRM -->|Attack Surface Map| C

    C -->|HUNT task| H[Hunter]
    H -->|Findings + Hypotheses| C
    C -->|Recursively Spawn| H

    C -->|VERIFY task| S[Skeptic]
    S -->|Debunked / Validated| C
    C -.->|If Validated| V[Validator]
    V -->|Verified / False Positive| C

    C -->|Persist| DB[(SQLite DB)]
    C -->|Stats Hook| UI([TUI / UI])
    E -->|Record Usage| CT[Cost Tracker]
    cb[Callbacks] -->|Record Usage| CT
    cb -->|Log| DB

    subgraph Infrastructure
        direction LR
        E[Engine]
        PM[Permission Manager]
        SB[Sandboxing]
    end

    SS -.->|uses| E
    H -.->|uses| E
    S -.->|uses| E
    V -.->|uses| SB
```

---

## 🏁 Getting Started

### Prerequisites

*   [mise](https://mise.jdx.dev/)
*   [uv](https://github.com/astral-sh/uv)
*   A Gemini API Key (set via `GOOGLE_API_KEY`)

### Installation & Usage

1.  **Sync Environment**: `uv sync`
2.  **Launch TUI**: `mise run run`
3.  **Run Tests**: `mise run test`

---

## 📜 Development

Refer to [AGENTS.md](./AGENTS.md) for the full architectural mandate and contribution guidelines.

---

## 🛡 Security Disclaimer

TrashDig is for authorized security research only. Authors are not responsible for misuse.

---

## 📝 License

Apache 2.0.
