# 💎 TrashDig: AI-Powered Vulnerability Research Assistant

TrashDig is a multi-agent, language-agnostic vulnerability scanner and security research assistant. It uses LLMs (like Gemini) to map complex project structures, trace data flows, and automatically identify security vulnerabilities that traditional tools often miss.

---

## 🚀 Key Features

*   **Multi-Agent Intelligence**: Built on the Google Agent Development Kit (ADK), featuring specialized agents:
    *   **Archaeologist**: Maps project structure and detects high-value targets (entry points, sensitive configs).
    *   **Hunter**: Performs autonomous, hypothesis-driven depth-first analysis on prioritized files.
    *   **Validator**: Attempts to generate Proof-of-Concept (PoC) code to verify findings.
*   **Human-in-the-Loop TUI**: A beautiful terminal interface (built with `Textual`) for reviewing maps, starring high-interest areas, and steering the "Hunt."
*   **Language Agnostic**: Uses `tree-sitter` and `semgrep` to understand and trace patterns across any codebase (Python, JavaScript, Go, C#, and more).
*   **Automated Findings**: Generates detailed Markdown reports for each vulnerability in a `findings/` directory.

---

## 🏁 Getting Started

### Prerequisites

*   [mise](https://mise.jdx.dev/) (for task orchestration and tool management)
*   [uv](https://github.com/astral-sh/uv) (for ultra-fast Python dependency management)
*   A Gemini API Key (or access to an LLM provider supported by ADK)

### Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/yourusername/trashdig.git
    cd trashdig
    ```

2.  **Install dependencies**:
    ```bash
    mise install  # Installs python and required tools
    uv sync       # Syncs the virtual environment
    ```

---

## ⚙️ Configuration

TrashDig is configured via `config.toml`. Create one in the root directory:

```toml
[ui]
interface = "textual"

[agents.archaeologist]
model = "gemini-2.0-flash"
provider = "google"

[agents.hunter]
model = "gemini-2.0-flash"
provider = "google"

[providers.google]
# API keys are best provided via environment variables (e.g., GOOGLE_API_KEY)
```

---

## 🛠 Usage

1.  **Launch the TUI**:
    ```bash
    mise run run
    ```
    *(Alternatively: `uv run python src/trashdig/main.py`)*

2.  **Scan**: The Archaeologist will automatically begin mapping the current directory.
3.  **Prioritize**: Use the TUI to review the project map. Use the `Space` or `S` keys to "Star" files or directories that look suspicious (e.g., controllers, routes, auth logic).
4.  **Hunt**: Once prioritized, trigger the "Hunt" mode. The Hunter agent will begin an autonomous loop to find vulnerabilities in the starred targets.

---

## 📜 Development & Contribution

We use `mise` for common developer tasks:

*   **Run Tests**: `mise run test`
*   **Linting**: `mise run lint`
*   **Format**: `mise run format`
*   **Coverage**: `mise run coverage`

### Engineering Standards
Please refer to [AGENTS.md](./AGENTS.md) for architectural details and contribution rules.

---

## 🛡 Security Disclaimer

TrashDig is a security research tool. It is designed to find vulnerabilities in code you own or have explicit permission to test. **Never use this tool on unauthorized targets.** The authors are not responsible for any misuse or damage caused by this tool.

---

## 📝 License

Apache 2.0. See [LICENSE](LICENSE) for details.
