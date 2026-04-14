# AI Agent Guidelines for mdtool

This project is a Go-based CLI tool for rendering Markdown to HTML.

## Technical Stack
- **Language:** Go 1.24+
- **Markdown Parser:** `goldmark` (CommonMark and GFM compliant)
- **Syntax Highlighting:** `chroma` (Server-side rendering)
- **Diagrams:** `mermaid.js` (Client-side rendering via script injection)
- **Styling:** Embedded GitHub-like default stylesheet (`go:embed`). Support `-css <path>` override. All CSS is inlined in the final HTML for portability.

## Coding Standards
- Follow idiomatic Go (Effective Go).
- Use the standard library for CLI flags and HTTP serving where possible.
- Ensure all new features are accompanied by tests.

## Project Structure
- **Main Entry Point:** `cmd/mdtool/main.go`
- **Core Logic:** Root package or sub-packages (e.g., `converter/`).
- **Web Server:** `server/` package.
- **Strict Rule:** DO NOT use a `pkg/` directory.

## Architectural Patterns
- **Converter Engine:** Implement the converter as a struct (e.g., `mdtool.Converter`) to hold configuration options (flags, CSS settings, etc.).
- **Interfaces:** Provide methods that perform conversion from an `io.Reader` to an `io.Writer` to ensure the core logic is decoupled from the filesystem and transport layers.
- **Portability:** Maintain a clear separation between CLI flag parsing, file I/O, and the conversion process.

- **Server Mode:**
  - If a directory is requested, look for `index.md` then `README.md`.
  - Fall back to a directory listing if no index file is found.
  - If `-only-md` is set, hide non-Markdown files from the directory listing.
  - Bind to `127.0.0.1:7768` by default.

## Tool Usage
- Use `go fmt` before every commit.
- Use `go mod tidy` when adding dependencies.
