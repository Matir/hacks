# Gemini CLI Agent Instructions for ASM Shell

This document provides guidance for AI agents working on the `asmsh` project.

## Architecture Overview
- **Cobra**: Used for CLI entry point and flags.
- **Liner**: Used for the interactive REPL.
- **Keystone/Capstone**: Core engines (linked via CGO).
- **Internal Packages**:
  - `internal/engine`: Wraps assembly/disassembly libraries. Uses build tags (`mock` vs `!mock`) to allow development without C libraries.
  - `internal/session`: Holds the state (symbol table, offset, current config).
  - `internal/repl`: Handles the interactive loop, input cleaning, and meta-commands.
  - `internal/arch`: Central architecture and mode configuration (case-insensitive).
  - `internal/formatter`: Output formatting logic (C, Python, Pretty).

## Coding Standards
- **Error Handling**: Always return errors from internal packages; handle them in the REPL or CLI layer.
- **State Isolation**: Ensure the `Session` object is the source of truth for the REPL state. Avoid global variables.
- **CGO Awareness**: Keystone and Capstone require C libraries. The `Makefile` handles auto-detection and local building via `scripts/build_keystone.sh`.
- **Testing**: **Mandatory**. All new code and bug fixes SHOULD be accompanied by unit tests. Mock engine interfaces where needed.

## Key Strategies

### Multi-pass Assembly & Labels
To support labels and forward references in a line-by-line REPL:
1. Maintain a `SourceLine` buffer in `Session`.
2. When a label is defined (`name:`), add it to the symbol table.
3. If assembly fails due to missing symbols, mark the line as "Pending".
4. Every time a new label is added, re-process all "Pending" lines in the buffer.

### Input Parsing
Use `internal/repl/util.go` for cleaning. Handle:
- Comments: `//`, `#`, `;`
- Hex formats: `0x90`, `\x90`, `90 90`, `90,90`

## Build System
The `Makefile` is the primary entry point. It:
1. Checks for system libraries.
2. Falls back to `third_party/`.
3. Triggers `./scripts/build_keystone.sh` if Keystone is missing.
4. Uses `-tags mock` if dependencies are completely unavailable.
