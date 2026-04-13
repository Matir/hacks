# TrashDig

TrashDig is an AI-powered, language-agnostic vulnerability scanner and security research assistant. It leverages LLMs to identify complex vulnerability patterns by mapping project structures and tracing data flows from entry points to risky code smells.

## Goals & Architecture

TrashDig operates as a multi-agent system designed for deep security exploration:

1.  **Archaeologist Agent**: Maps the project structure, respects `.gitignore`, and generates brief summaries of each file to identify high-value targets (entry points, controllers, configuration, etc.).
2.  **Human-in-the-Loop TUI**: A terminal interface where researchers review the Archaeologist's map, star high-interest areas, and manually prioritize files for deep-dive analysis.
3.  **Hunter Agent (Auto-Pilot)**: An autonomous loop that performs depth-first analysis on prioritized targets, identifying risky code smells and attempting to connect user-controlled input to dangerous sinks.

## TrashDig MVP

- **TUI Interface**: For project mapping, file summarization, and interactive prioritization.
- **Language-Agnostic Scanning**: LLM-based analysis that adapts to any codebase structure.
- **Project Mapping**: Identification of key components, entry points, and high-value targets.
- **Automated Findings**: A `findings/` directory with a detailed markdown file for each identified issue, describing the impact and path.

## Configuration

TrashDig is configured via `config.toml`. You can specify model choices and provider settings for each agent.

```toml
[ui]
interface = "textual"

[agents.archaeologist]
model = "gemini-2.0-flash"
provider = "google"

[agents.hunter]
model = "gemini-2.0-flash"
provider = "google"
```

## Workflow

1.  **Scan**: The Archaeologist maps and summarizes the project.
2.  **Prioritize**: The researcher uses the TUI to "star" files or directories of interest.
3.  **Hunt**: The Hunter agent enters an autonomous loop to find and document vulnerabilities.
