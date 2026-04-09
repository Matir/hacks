# VPOC - Vulnerability Scanner

- See @README.md for an overview of the goals and purpose of the project.
- See @TODOs.md for a list of standing TODOs.

## Framework

This application should use the Google Agent Development Kit (ADK) as its foundation.
This package is published as `google-adk` on PyPi.

The [source is on Github](https://github.com/google/adk-python) and there is
[documentation for agentic development by LLMs](https://github.com/google/adk-python/blob/main/llms.txt).

## Agent Roles

- **Orchestrator Agent**: The central controller that manages the workflow, state, and budget. It maintains a findings database and coordinates the other agents.
- **Source Review Agent**: Responsible for static source code analysis. It should prioritize high-value targets (as defined during kickoff) and generate "potential finding" entries.
- **PoC Agent**: Takes a potential finding and attempts to generate an exploit script (PoC). It specializes Docker base containers by generating dynamic Dockerfiles to install dependencies.
- **Validation Agent**: Executes the PoC in a hardened Docker sandbox. It monitors the application's response (e.g., crashes, unauthorized access) to confirm the finding's impact.
- **Reporting Agent**: Compiles findings, logs, and PoC results into a final security report for human review.

## Project Initialization (Kickoff)

Every review session must start with a human-guided kickoff phase. This is handled via a wizard in the web interface and captures:
- **Target Description**: Free-text context about the application's purpose and threat model.
- **Source Retrieval**: Supports git URLs, download URLs (e.g., zip/tarball), or direct file uploads.
- **High-Value Targets**: Specific files, directories, or endpoints to prioritize.
- **Build/Environment Hints**: Custom commands for dependency installation or build steps.
- **Exclusions**: Paths or vulnerability types to ignore.

## Coding Style

- All code should conform to PEP-8.
- All public functions and methods should have pydoc-ready docstrings.
- Private functions and methods should begin with `_`.
- Use classes wherever it makes sense to encapsulate things. Build as if it is
  object-oriented whenever it makes sense.
- Build unit tests for any complex code.
- Always stub out calls to real LLMs in Unit Tests.
- Use python typing. (PEP 484, etc.)
- Place individual agents in `agents/`.
- Place tools in `tools/`.

## Building Features

When asked to build a feature, only build out what's been requested and the
appropriate tests. Ask before continuing on.
