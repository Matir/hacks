# Developer AI Agents: Configuration & Persona Guide

This guide provides the configuration paths, instruction standards, and tool-integration methods for the four primary AI agents: **Claude Code**, **Gemini CLI**, **Kilo Code**, and **Open Code**.

---

## 1. Claude Code (Anthropic)
Claude Code is a high-autonomy agent that prioritizes the Model Context Protocol (MCP) for tool extension.

### Instructions & Personas
- **Global Persona:** Stored in `~/.claude/settings.json` (specifically the `userInstructions` or `persona` fields). You can also place a global instruction file at `~/.claude/CLAUDE.md`.
- **Per-Project Instructions:** Uses a `CLAUDE.md` file at the repository root. This is the source of truth for project-specific style guides, build commands, and testing patterns.

### MCP & Skills
- **User Level (Global):** Configured in `~/.claude.json`. Use the command `claude mcp add --user <name> <command>`.
- **Project Level:** Configured in a `.mcp.json` file at the repository root. This file should be checked into version control to share tools (like project-specific DB explorers) with the team.
- **Local Level (Private):** Stored in `~/.claude.json` but scoped to the project path. Use `claude mcp add --local` for tools you want to keep private to your machine.

### Configuration
- **Default Path:** `~/.claude/` for logs and settings; `~/.claude.json` for tool definitions.
- **Sub-Agents:** Does not use configurable sub-agents; instead, it uses an internal "Agentic Loop" that delegates tasks to tools.
- **Limitations:** Large numbers of MCP tools (50+) can significantly bloat the context window. Use the `Tool Search` feature (v2.1+) to mitigate token usage.

---

## 2. Gemini CLI (@google/gemini-cli)
The Gemini CLI is built for deep integration with Google Cloud and Vertex AI, emphasizing the "Gemini Code Assist" agent mode.

### Instructions & Personas
- **Global Persona:** `~/.gemini/GEMINI.md`. This file is appended to every request to define your persistent developer identity.
- **Per-Project Instructions:** `GEMINI.md` or `AGENTS.md` at the project root. If both exist, `GEMINI.md` typically takes precedence for the CLI.

### MCP & Skills
- **User Level (Global):** `~/.gemini/settings.json`.
- **Project Level:** `mcp.json` in the current working directory. The CLI automatically detects this file when started.

### Configuration
- **Default Path:** `~/.gemini/`.
- **Sub-Agents:** Accessed via "Agent Mode" (the `/agent` command). While not configurable as separate files, you can define different behaviors within `GEMINI.md` using headers (e.g., `# Architect Mode`).
- **Limitations:** Currently in Preview. Some MCP authentication flows (OAuth) must be handled via a browser, which can interrupt headless CLI workflows.

---

## 3. Kilo Code (Kilo Health / Kilo CLI)
Kilo Code is an open-source agent built for high-performance parallel tool execution, often used as a fork or wrapper for Open Code.

### Instructions & Personas
- **Global Persona:** Managed via the "Agent Manager" in the VS Code extension or `~/.kilo/AGENTS.md`.
- **Per-Project Instructions:** Standardizes on `AGENTS.md` at the repository root. It follows the Agentic AI Foundation (AAIF) spec.

### MCP & Skills
- **User Level (Global):** Configured in the `kilo-gateway` or `~/.kilo/config.json`.
- **Project Level:** Reads `mcp.json` from the root. Supports parallel tool execution (running multiple MCP calls simultaneously).

### Configuration
- **Default Path:** `~/.kilo/` and `packages/opencode/` (if running from source).
- **Sub-Agents:** Inherits the **Primary/Sub-agent** architecture from Open Code (see below).
- **Limitations:** Relies on `kilocode_change` markers for upstream syncs; manual configuration of these markers is required if you are modifying the core agent logic.

---

## 4. Open Code (OpenCode.ai / OpenHands)
Open Code is a highly modular agentic framework that explicitly supports specialized sub-agents.

### Instructions & Personas
- **Global Persona:** `~/.opencode/config.yaml`.
- **Per-Project Instructions:** `AGENTS.md` at the repo root.

### MCP & Skills
- **Global/Project:** Managed via a unified `mcp.json` structure or through the web UI / CLI settings.

### Configuration & Sub-Agents
- **Primary Agents:**
    - `Build`: Full tool access for active development.
    - `Plan`: Restricted mode for analysis and architectural suggestions (no file writes).
- **Sub-Agents:** Can be invoked via `@mention` in the chat:
    - `@general`: Multi-step task execution.
    - `@explore`: Fast, read-only codebase exploration.
- **Custom Sub-Agents:** Defined in `~/.opencode/agents/` as separate JSON/YAML files specifying their unique system prompts and tool subsets.

### Limitations
- **Context Fragmentation:** When sub-agents create child sessions, context "bleeding" can occur. Use the `session_parent` command (Up arrow) to navigate the session hierarchy effectively.

---

## Summary Table: Configuration Locations

| Feature | Claude Code | Gemini CLI | Kilo / Open Code |
| :--- | :--- | :--- | :--- |
| **Global Instr.** | `~/.claude/CLAUDE.md` | `~/.gemini/GEMINI.md` | `~/.kilo/AGENTS.md` |
| **Project Instr.** | `CLAUDE.md` | `GEMINI.md` | `AGENTS.md` |
| **User MCP** | `~/.claude.json` | `~/.gemini/settings.json`| `~/.kilo/config.json` |
| **Project MCP** | `.mcp.json` | `mcp.json` | `mcp.json` |
| **Sub-Agents** | Internal Only | Agent Mode (/agent) | @general, @explore |
