# mdtool TODO

## Project Setup
- [x] Initialize project structure (`cmd/mdtool/`, `server/`).
- [x] Define the `Converter` struct and core conversion interface.
- [x] Implement CLI flag parsing in `cmd/mdtool/main.go`.

## Conversion Mode
- [x] Implement Markdown to HTML rendering for single files.
- [x] Implement directory traversal and batch conversion.
- [x] Implement logic for handling `outpath` as specified in README.

## Server Mode
- [x] Implement HTTP server to serve Markdown files as HTML.
- [x] Implement logic for `index.md` or `README.md` as directory entry points.
- [x] Implement directory listing fallback.
- [x] Implement `-only-md` flag logic (filter files in server and listing).
- [x] Implement static file serving for non-MD files.

## Markdown Features
- [x] Integrate Syntax Highlighting (Chroma).
- [x] Integrate Mermaid.js (client-side script injection).
- [x] Ensure GFM (Checklists, Tables) are enabled.

## Polish & Maintenance
- [x] Add basic CSS styling for the output HTML (GitHub-like).
- [x] Implement `go:embed` for default CSS and assets.
- [x] Implement CSS inlining logic for both default and custom CSS (-css flag).
- [x] Write unit tests for core conversion logic.
- [x] Write integration tests for server mode.
