# Specification: Next-Gen Autonomous Vulnerability Research Agent

This document outlines the core architectural patterns and functional requirements for building a state-of-the-art autonomous security research agent.

## 1. Core Architectural Pattern: Hypothesis-Driven Orchestration

Move beyond linear scanning. Implement a multi-agent system where a "Coordinator" or "Spawner" manages specialized sub-agents through a recursive **Observe-Hypothesize-Verify** loop.

### **Key Agents:**
- **Project Analyzer:** Performs rapid, wide-breadth reconnaissance (languages, frameworks, entry points, dependencies). Outputs a "Project Profile" used to seed the knowledge of all subsequent agents.
- **Recon Agent:** Deep-dives into specific sub-components (e.g., a specific API module) to map data flows and identify "interesting" code patterns.
- **Spawner/Executor Agent:** Formulates concrete exploitation hypotheses (e.g., "The `id` parameter in `fetch_user` is concatenated directly into a SQL string"). It then spawns a targeted task to verify the hypothesis using a suite of dynamic tools.

---

## 2. AST-Aware Code Intelligence Layer

The agent must not "read" code as raw text. It must interact with the codebase through an **AST-aware navigation API**.

### **Functional Requirements:**
- **Tree-sitter Integration:** Support multi-language parsing (Python, C++, Go, JS, etc.) into Abstract Syntax Trees.
- **Semantic Navigation Tools:**
    - `FindDefinition(symbol)`: Jump to the implementation of a function or variable.
    - `FindReferences(symbol)`: Identify all call sites or usages across the entire project.
    - `GetScope(line_number)`: Understand the local context and available variables at any point.
- **Data Flow Tracing:** Implement primitive taint analysis capabilities where the agent can "follow" a variable from an untrusted source (e.g., `request.args`) to a sensitive sink (e.g., `db.execute()`).

---

## 3. The Dynamic Verification Loop (Ground Truth)

A vulnerability is only "found" once it is verified. The system must prioritize **empirical evidence over probabilistic reasoning**.

### **Workflow:**
1. **PoC Generation:** When a potential flaw is found, the agent must generate a standalone Proof-of-Concept (PoC) script (e.g., Python, Bash, or `curl` commands).
2. **Controlled Execution:** The agent runs the PoC against the target codebase/environment.
3. **Artifact Analysis:** The agent captures `stdout`, `stderr`, and exit codes to determine if the "exploit" was successful.
4. **Iterative Refinement:** If the PoC fails, the agent analyzes the failure logs and modifies its hypothesis or the PoC code and retries.

---

## 4. Tool-Augmented LLM Capabilities

Equip the agent with a "Utility Belt" of standardized tools, allowing it to interact with the environment like a human researcher.

### **Required Toolset:**
- **Structural Tools:** `grep` (regex search), `glob` (file listing), `read_range` (targeted file reading).
- **Static Analysis:** Integrated `semgrep` or `linter` support to rapidly flag known insecure patterns for the agent to investigate deeper.
- **Execution Tools:** A secure `bash_tool` for running arbitrary commands (compilers, debuggers, network scanners).
- **External Knowledge:** `web_search` and `web_fetch` to research library-specific CVEs or novel exploitation techniques.

---

## 5. Human-Agent Collaborative Steering

Implement a "Steerable Autonomy" model.

### **Features:**
- **Interrupt-to-Instruct:** Allow the user to pause the autonomous loop at any time to provide "direction hints" (e.g., "This project uses a custom ORM, look at `lib/db.py` for SQLi").
- **Permission Boundary:** A configurable gatekeeper that intercepts "write" or "exec" tool calls, requiring user confirmation for sensitive actions (unless in "Full Autonomy" mode).
- **Structured Questioning:** The agent can "ask" the user for clarification (e.g., "What is the expected entry point for this microservice?") to resolve ambiguity.

---

## 6. Compounding Contextual Memory

The agent's understanding of the project must grow over time.

- **Session Persistence:** Store all tool outputs, agent thoughts, and verified findings in a project-specific "Knowledge Graph" or "Findings Database."
- **Context Management:** Use sophisticated "compaction" or "summarization" techniques to keep the LLM's context window focused on the current task while maintaining high-level awareness of the global project state.
