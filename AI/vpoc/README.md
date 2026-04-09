# VPOC

VPOC is an autonomous security analysis tool for Application Security, built on the Google Agent Development Kit (ADK).

It focuses on source-available security analysis, combining LLM-driven vulnerability discovery with automated Proof-of-Concept (PoC) validation.

## Architecture

VPOC employs a multi-agent orchestration pattern:
- **Orchestrator Agent**: Manages the lifecycle of findings and coordinates specialized agents.
- **Source Review Agent**: Performs deep static analysis to identify potential vulnerabilities.
- **PoC Agent**: Dynamically generates exploit scripts and specialized Docker environments.
- **Validation Agent**: Executes PoCs in a sandboxed environment to confirm reachability and impact.
- **Reporting Agent**: Aggregates findings and logs into human-readable security reports.

## Features

- **Multi-Language Support**: PHP, C/C++, Go, Rust, Lua.
- **Autonomous Validation**: 
  - Findings are validated by running the application in a hardened Docker container.
  - **Sandboxed Execution**: Strict resource limits (CPU/RAM) and default **no network access** (or isolated private networks).
  - **Hybrid Environment**: Uses pre-configured base containers specialized at runtime based on source analysis.
- **Interactive Human-in-the-Loop**:
  - Web-based dashboard for real-time monitoring and finding triage.
  - **Project Initialization Wizard**: Kickoff reviews with high-level descriptions, git URLs, or file uploads.
  - **Human Guidance**: Users can provide hints, approve/reject findings, and define strategic priorities.
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
