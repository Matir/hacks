# VPOC

VPOC is a security analysis tool for Application Security.

At the moment, it focuses on source-available security analysis.

## Supported AI Platforms

- VertexAI
- OpenRouter
- Any OpenAI-Compatible

## Features

- Examine Source Code in a Variety of Languages
  - PHP
  - C/C++
  - Go
  - Rust
  - Lua
- Find security vulnerabilities
  - Categorize
- When possible, validate the finding by running the application in a Docker
  container and peforming a minimal PoC.

## Feedback

- Provide a log of the full LLM conversations in the findings.
- Generate a clear report of the finding for human review.

## Independence

- The tool operates mostly autonomously, though with a human console that can
  provide status monitoring and assistance.

## Author

- David Tomaschik <matir@pm.me>

With assistance from Claude and Gemini. :)
