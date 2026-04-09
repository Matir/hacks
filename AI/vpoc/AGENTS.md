# VPOC - Vulnerability Scanner

- See @README.md for an overview of the goals and purpose of the project.
- See @TODOs.md for a list of standing TODOs.

## Framework

This application should use the Google Agent Development Kit as its foundation.
This package is published as `google-adk` on PyPi.

The [source is on Github](https://github.com/google/adk-python) and there is
[documentation for agentic development by LLMs](https://github.com/google/adk-python/blob/main/llms.txt).

## Coding Style

- All code should conform to PEP-8.
- All public functions and methods should have pydoc-ready docstrings.
- Private functions and methods should begin with `_`.
- Use classes wherever it makes sense to encapsulate things. Build as if it is
  object-oriented whenever it makes sense.
- Build unit tests for any complex code.
- Always stub out calls to real LLMs in Unit Tests.
- Use python typing. (PEP 484, etc.)
- Place individual agents in agents/.
- Place tools in tools/.

## Building Features

When asked to build a feature, only build out what's been requested and the
appropriate tests. Ask before continuing on.
