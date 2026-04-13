# Context

- Read @README.md for the human-centric context.
- Read @adk-llms.txt for ADK documentation.

## Architecture

This project is built using Google's **Agent Development Kit (ADK)**. It implements a multi-agent system consisting of an **Archaeologist** agent for mapping/summarization and a **Hunter** agent for deep-dive vulnerability analysis.

### Model Flexibility & Provider Independence

TrashDig is designed to be provider-independent for its LLM backend. Each agent's model can be individually configured via `config.toml`, supporting:
- **Google/VertexAI**: Via direct ADK support.
- **OpenRouter**: Or other OpenAI-compatible providers.
- **Custom Providers**: Configured through base URLs and API keys in the configuration.

## Rules

- Always provide unit tests.
- Always use type hints.
- Use uv for managing a virtual environment and dependencies.
- Use mise for tasks and non-python dependencies.
- Ask before adding new imports.
- Add docstrings to all code.
- Keep prompts in separate .md files to be edited.
- Every sub-agent must have a configurable model choice in `config.toml`.
