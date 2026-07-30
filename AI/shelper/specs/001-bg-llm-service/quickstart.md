# Quickstart Validation Guide: Background LLM Processing Service

This guide provides end-to-end instructions for launching the background service daemon, sending processing requests over the Unix domain socket interface, and testing the interactive shell line editor integration.

## Prerequisites

- Go 1.22 or higher installed
- An API Key for Google Gen AI (`GEMINI_API_KEY`) or OpenAI (`OPENAI_API_KEY`)
- `socat` or `nc` utility installed for manual socket testing
- Bash (4.0+) or Zsh (5.0+)

## Setup & Environment

Set up your provider credentials:

```bash
export GEMINI_API_KEY="your-gemini-api-key"
# or
export OPENAI_API_KEY="your-openai-api-key"
```

## Socket Location Resolution Test

Verify which socket path your environment resolves to:

```bash
# 1. Default fallback (using TMPDIR or /tmp)
echo "Resolved socket: ${TMPDIR:-/tmp}/shelper.$(id -u).sock"

# 2. Custom environment override
export SHELPER_SOCK="/tmp/custom-shelper.sock"
echo "Custom socket: ${SHELPER_SOCK}"
```

## Running the Daemon

Start the background daemon process:

```bash
go run ./cmd/shelperd
```

Expected output:
```text
[INFO] SHelper daemon starting...
[INFO] Resolved socket path: /tmp/shelper.1000.sock
[INFO] Loaded prompt template source: bundled (default)
[INFO] Listening for connections...
```

## Custom Prompt Template Validation

Create a custom user prompt template at `$HOME/.config/shelper/prompt.md`:

```bash
mkdir -p ~/.config/shelper
cat << 'EOF' > ~/.config/shelper/prompt.md
You are a command-line assistant generating terminal commands for {{.Variables.shell}}.
Task: {{.Input}}

Return ONLY the raw executable command without markdown formatting or code blocks.
EOF
```

Restart `shelperd` to observe template resolution:
```text
[INFO] Loaded prompt template source: custom_file ($HOME/.config/shelper/prompt.md)
```

## Sending Socket Requests

In a separate terminal window, send a JSON request payload over the Unix socket using `socat`:

### Test 1: Socket Request with Shell Variable (`bash`)

```bash
echo '{"id":"req-001","provider":"google","input":"find all log files modified in the last 24 hours","variables":{"shell":"bash"}}' | socat - UNIX-CONNECT:/tmp/shelper.1000.sock
```

Expected Response:
```json
{
  "id": "req-001",
  "status": "success",
  "output": "find . -type f -name \"*.log\" -mtime -1",
  "metadata": {
    "provider": "google",
    "model": "gemini-2.5-flash",
    "latency_ms": 284,
    "template_source": "custom_file"
  }
}
```

---

## Interactive Shell Line Editor Integration Test

### 1. Test Bash Widget

Source the Bash integration script in an interactive Bash shell:

```bash
source ./shell/shelper.bash
```

Type a prompt in your prompt line (do NOT press Enter):

```bash
find disk space usage for all mounted filesystems
```

Now press `Ctrl+X Ctrl+E`.

**Expected Result**: The text line in your command buffer is replaced automatically by:
```bash
df -h
```
The cursor is positioned at the end of `df -h`, allowing you to inspect and press `<Enter>` to run it directly!

---

### 2. Test Zsh Widget

Source the Zsh integration script in an interactive Zsh shell:

```zsh
source ./shell/shelper.zsh
```

Type a prompt in your command line:

```zsh
list all listening TCP ports with process names
```

Press `Ctrl+X Ctrl+E`.

**Expected Result**: The command line buffer updates instantly to:
```zsh
sudo ss -tulpn
```
Ready for instant inspection and execution.
