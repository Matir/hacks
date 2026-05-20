# mdtool

mdtool is a tool for rendering markdown files as HTML.

## Usage

mdtool supports two primary modes: batch conversion and a live server.

### Conversion Mode

Batch convert one or more Markdown files to HTML.

```bash
mdtool convert [flags] <inpath> [outpath]
```

- **inpath**: A single `.md` file or a directory containing Markdown files.
- **outpath** (optional):
  - If omitted:
    - For a file, `outpath` is `inpath` with `.html` extension.
    - For a directory, `.html` files are created alongside `.md` files in the same directory.
  - If specified:
    - For a file, it writes to `outpath`.
    - For a directory, `outpath` must be a directory. It replicates the source directory structure within `outpath`.

**Flags:**
- `-w, --watch`: Watch for changes and re-convert automatically.
- `--css <path>`: Path to a custom CSS file to inline in the output.
- `--no-highlight`: Disable syntax highlighting.
- `--no-mermaid`: Disable Mermaid.js diagrams.

### Server Mode

Run a local webserver to serve and render Markdown files on the fly.

```bash
mdtool serve [flags] [directory]
```

By default, it serves the current directory and binds to `127.0.0.1:7768`.

**Flags:**
- `-w, --watch`: Enable live auto-reload in the browser when files change.
- `-l, --listen <addr>`: Change the listen address (default `127.0.0.1:7768`).
- `--only-md`: Only serve `.md` files; hide or deny access to other file types.
- `--css <path>`, `--no-highlight`, `--no-mermaid`: Same as conversion mode.

## Supported Markdown Features

- **Syntax Highlighting**: Fenced code blocks are highlighted via Chroma.
- **Diagrams**: Mermaid.js support for `mermaid` code blocks.
- **GFM**: GitHub-Flavored Markdown (Checklists, Tables, etc.).
- **Dark Mode**: Automatically respects system preferences via media queries.
- **Live Reload**: Browser automatically refreshes when files are saved (requires `-w` in server mode).
