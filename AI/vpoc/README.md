# VPOC

VPOC is an autonomous security analysis tool for Application Security, built on the Google Agent Development Kit (ADK).

It focuses on source-available security analysis, combining LLM-driven vulnerability discovery with automated Proof-of-Concept (PoC) validation.

## Architecture

VPOC employs a single-process, multi-agent orchestration pattern, where each agent combines **deterministic tool-driven logic** with **LLM-driven reasoning**:
- **Orchestrator Agent**: Manages the lifecycle of findings, project-wide state, and budget transitions.
- **Attack Surface Mapper (Recon Agent)**: Maps the target's entry points and reasons about the semantic value of endpoints.
- **Environment Architect (Build Agent)**: Automates and troubleshoots the build environment by interpreting error logs.
- **Source Review Agent**: Performs deep static analysis and pre-screens tool findings for false positives.
- **PoC Agent**: Dynamically generates specialized exploit scripts and Docker environments.
- **Validation Agent**: Executes PoCs in a sandboxed environment and analyzes the security impact of results.
- **Reporting Agent**: Aggregates findings and synthesizes logs into human-readable security reports.

## Features

- **Multi-Language Support**: PHP, C/C++, Go, Rust, Lua.
- **Autonomous Validation**: 
  - Findings are validated by running the application in a **hardened Docker sandbox** (using gVisor/seccomp, strict resource limits, and no-egress networking).
  - **Pipelined Analysis**: Findings are streamed from discovery to validation in real-time, using a priority-weighted queue.
  - **Hybrid Environment**: Uses pre-configured base containers specialized at runtime based on source analysis.
- **Interactive Human-in-the-Loop**:
  - **TUI Mode**: Terminal User Interface for single-project analysis, featuring dedicated screens for Chat, Status, and Findings.
  - **Web Dashboard**: Web-based interface for real-time monitoring and multi-project triage.
  - **Project Initialization Wizard**: Kickoff reviews with high-level descriptions, git URLs, or file uploads.
  - **Human Guidance**: Users can provide hints, approve/reject findings, and define strategic priorities.
- **State Persistence & Resumption**:
  - **Checkpointing**: All runs record granular state to allow stopping and resuming without significant loss of analysis quality.
  - **Project Isolation**: Each project maintains its own isolated state and findings database.
- **Resource Management**:
  - **Deterministic Budgeting**: Hard daily budget caps enforced across all projects.
  - **Per-Agent Model Assignment**: Optimize cost and performance by assigning specific models (e.g., Gemini 1.5 Pro vs. Flash) to different agents.

## Supported AI Platforms

- VertexAI
- OpenRouter
- Any OpenAI-Compatible

## Feedback

- Provide a log of the full LLM conversations in the findings.
- Generate a clear report of the finding for human review.

## Author

- David Tomaschik <matir@pm.me>

With assistance from Claude and Gemini. :)
