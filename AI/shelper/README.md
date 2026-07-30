# SHelper (Shell Helper Daemon)

SHelper is a lightweight background service daemon that runs on your local machine, accepts Unix Domain Socket requests, formats prompts using custom or bundled templates, routes them to an LLM provider (Google Gemini or OpenAI), and returns command-line suggestion responses directly to your shell line editor buffer.

## Features

- **Background Daemon**: Fast IPC Unix Socket communication with NDJSON (Newline Delimited JSON) framing.
- **Provider Extensible**: Out of the box support for Google Gen AI Go SDK (`gemini-2.5-flash` default) and OpenAI Go SDK (`gpt-4o` default).
- **Resilient**: Automatic request retries with exponential backoff on transient upstream provider errors.
- **Flexible Templates**: Load custom templates from `$HOME/.config/shelper/prompt.md` or fallback to compile-time embedded templates.
- **Interactive Shell Widget**: Sources Bash/Zsh widgets that bind `Ctrl+X Ctrl+E` to query the daemon and instantly replace your terminal buffer with executable suggestions.

---

## Installation & Setup

### 1. Build the Daemon

Build the background binary:

```bash
go build -o bin/shelperd ./cmd/shelperd
```

### 2. Configure Environment Variables

Before starting the daemon, configure the API keys depending on the provider you want to use.

```bash
# For Google Gemini
export GEMINI_API_KEY="your-gemini-api-key"

# For OpenAI
export OPENAI_API_KEY="your-openai-key"
```

### 3. Run the Daemon

Start the service in the background:

```bash
./bin/shelperd &
```

The daemon automatically resolves the socket location following this priority order:
1. Environment variable `$SHELPER_SOCK`
2. `${XDG_RUNTIME_DIR}/shelper.sock`
3. `/tmp/shelper.${UID}.sock`

---

## Configuration

shelperd supports multiple layers of configuration with the following priority order (highest to lowest):
1. **Command Line Flags** (e.g. `--llm-provider`)
2. **TOML Configuration File** at `~/.config/shelper/shelper.toml`
3. **Environment Variables** (e.g. `GEMINI_API_KEY`)
4. **Compiled Defaults**

### Configuration Options

| Option | TOML Key | CLI Flag | Default | Description |
|--------|----------|----------|---------|-------------|
| Provider | `llm_provider` | `--llm-provider` | `gemini` | `gemini` or `openai` |
| Model | `llm_model` | `--llm-model` | `gemini-2.5-flash` | LLM Model ID |
| Gemini Key | `gemini_api_key` | `--gemini-api-key` | N/A | Google Gemini API Key |
| OpenAI Key | `openai_api_key` | `--openai-api-key` | N/A | OpenAI API Key |
| Log File | `logfile` | `--logfile` | N/A | Path to log file (writes to stdout/stderr if unset) |
| Log Level | `loglevel` | `--loglevel` | `info` | Logging granularity: `info`, `warning`, `error` |

### TOML Configuration File Example
Create the file at `~/.config/shelper/shelper.toml`:

```toml
llm_provider = "gemini"
llm_model = "gemini-2.5-flash"
logfile = "/home/user/.config/shelper/shelper.log"
loglevel = "info"
```

---

## Shell Widget Integration

To enable interactive suggest widgets in your shell line editor, source the appropriate script in your rc profile.

### Bash Setup

Add the following to your `~/.bashrc`:

```bash
source /path/to/shelper/shell/shelper.bash
```

Press `Ctrl+X Ctrl+E` (or standard readline bindings) after typing a command description prompt on the line buffer.

### Zsh Setup

Add the following to your `~/.zshrc`:

```bash
source /path/to/shelper/shell/shelper.zsh
```

Press `Ctrl+X Ctrl+E` after typing a prompt on the line buffer.

---

## Telemetry & Health Checks

Query the daemon health metrics by sending a status request to the socket:

```bash
echo '{"type":"status"}' | socat - UNIX-CONNECT:/tmp/shelper.$(id -u).sock
```

Response structure:
```json
{
  "id": "",
  "status": "success",
  "output": "{\"active_workers\":0,\"status\":\"active\",\"total_requests\":1,\"uptime\":12.34}",
  "metadata": {
    "provider": "internal",
    "model": "none",
    "template_source": "none"
  }
}
```
