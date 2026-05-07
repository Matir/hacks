# TODO: ASM Shell

## Phase 1: Scaffolding
- [x] Initialize `go.mod` and directory structure.
- [x] Implement Cobra CLI with `assemble` and `disassemble` subcommands.
- [x] Implement `liner` REPL loop.
- [x] Implement Makefile with smart dependency detection.

## Phase 2: Core Engines
- [x] Implement architecture/mode configuration (case-insensitive).
- [x] Implement Mock Engine for testing.
- [x] Implement modular engine architecture (`internal/engine/{keystone,capstone,factory}.go`).
- [ ] Setup Keystone Go bindings and wrapper (Requires libkeystone).
- [ ] Setup Capstone Go bindings and wrapper (Requires libcapstone).

## Phase 3: Session Management
- [x] Implement symbol table and offset tracking.
- [x] Implement meta-command parsing (`.arch`, `.offset`, `.symbols`, `.clear`, `.output`).
- [x] Implement `.clear` command.
- [ ] Implement `SourceLine` buffer for multi-pass assembly.

## Phase 4: Features
- [ ] Implement label parsing (e.g., `label:`) in assembly mode.
- [ ] Implement forward-reference resolution (re-assembling pending lines when labels are defined).
- [x] Implement comment stripping and hex parsing in disassembly mode.
- [x] Implement output formatters (Pretty, C, Python).
- [ ] Implement File I/O (`.load`, `.save`).

## Phase 5: Refinement
- [x] Implement unit tests for core packages (arch, formatter, session, repl utils).
- [ ] Add integration tests for real engines.
- [ ] Add tab-completion for architectures and meta-commands.
