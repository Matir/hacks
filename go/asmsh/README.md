# ASM Shell (asmsh)

An interactive CLI and REPL for assembling and disassembling machine code across multiple architectures, powered by **Keystone** and **Capstone**.

## Features

- **Interactive REPL**: Rich shell experience with history and tab completion (via `liner`).
- **Multi-Architecture**: Support for x86, x86_64, and more (extensible via `internal/arch`).
- **Flexible Formats**: Output results as Hex, C-style arrays, Python byte-strings, or pretty-printed tables.
- **Session Management**: Persistent virtual offsets, symbol tables (labels), and dynamic architecture/mode switching.
- **Smart Build System**: Automatically detects system-wide or local library installations.

## Quick Start

### 1. Build Dependencies
If you don't have Keystone installed globally, you can build it locally into the `third_party/` directory:

```bash
./scripts/build_keystone.sh
```

Ensure you have `libcapstone-dev` installed via your package manager (e.g., `sudo apt install libcapstone-dev`).

### 2. Compile
Use the provided `Makefile` to automatically detect your libraries and build the binary:

```bash
make
```

### 3. Run
```bash
./asmsh
```

## Usage

### Commands
- `asmsh assemble` (Default): Start the REPL in assembly mode.
- `asmsh disassemble`: Start the REPL in disassembly mode.

### REPL Meta-Commands
Lines starting with a dot (`.`) are meta-commands:
- `.arch <name>`: Switch architecture (e.g., `x86_64`, `x86`).
- `.mode <assemble|disassemble>`: Toggle engine mode.
- `.offset <addr>`: Set the current virtual address.
- `.symbols`: List currently defined labels.
- `.output <pretty|c|python>`: Change the output display format.
- `.clear`: Reset session state (offset and symbols).
- `.exit`: Quit the shell.

## Package Path
`github.com/Matir/hacks/go/asmsh`
