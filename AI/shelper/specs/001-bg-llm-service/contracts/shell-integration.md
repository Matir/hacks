# Contract Specification: Shell Line Editor Integration

This contract specifies the behavior, interface, and key bindings for shell line editor integration scripts in Bash and Zsh.

## Target Shells & Key Bindings

- **Default Key Binding**: `Ctrl+X Ctrl+E` (`\C-xe` in readline, `^X^E` in ZLE)
- **Supported Shells**:
  - Bash 4.0+ (`shell/shelper.bash`)
  - Zsh 5.0+ (`shell/shelper.zsh`)

---

## Behavior Specification

### 1. Line Editor Capture
- Upon pressing `Ctrl+X Ctrl+E`, the shell widget intercepts line editing.
- Captures active buffer text:
  - Bash: `$READLINE_LINE`
  - Zsh: `$BUFFER`
- If line buffer is empty, no action is taken or prompt message is displayed.

### 2. Socket Resolution & Payload Construction
- Resolves target socket path in shell script matching daemon logic:
  1. `$SHELPER_SOCK`
  2. `${XDG_RUNTIME_DIR}/shelper.sock`
  3. `${TMPDIR:-/tmp}/shelper.$(id -u).sock`
- Constructs NDJSON payload:
  ```json
  {"input": "<contents of buffer>", "variables": {"shell": "bash"}}
  ```

### 3. Transmission & Response Extraction
- Transmits NDJSON line to target socket via `socat`, `nc -U`, or fallback helper binary.
- Extracts `output` string from `SocketResponse` JSON.

### 4. Buffer Insertion
- Replaces active buffer text with extracted `output` string:
  - Bash: `READLINE_LINE="$output"`, `READLINE_POINT=${#READLINE_LINE}`
  - Zsh: `BUFFER="$output"`, `CURSOR=${#BUFFER}`, followed by `zle redisplay`
- Buffer is now populated with the generated command string, ready for user review and press of `<Enter>` to execute.

---

## Example Shell Script Definitions

### Bash Integration (`shell/shelper.bash`)

```bash
_shelper_cmd_widget() {
    local input="$READLINE_LINE"
    [[ -z "$input" ]] && return

    local sock="${SHELPER_SOCK:-${XDG_RUNTIME_DIR:+"$XDG_RUNTIME_DIR/shelper.sock"}}"
    sock="${sock:-${TMPDIR:-/tmp}/shelper.$(id -u).sock}"

    if [[ ! -S "$sock" ]]; then
        return 1
    fi

    # Escape JSON string input
    local payload
    payload=$(printf '{"input":%s,"variables":{"shell":"bash"}}' "$(python3 -c "import json, sys; print(json.dumps(sys.argv[1]))" "$input")")

    local response
    response=$(echo "$payload" | socat - "UNIX-CONNECT:$sock" 2>/dev/null)

    local output
    output=$(echo "$response" | python3 -c "import json, sys; res=json.load(sys.stdin); print(res.get('output',''))" 2>/dev/null)

    if [[ -n "$output" ]]; then
        READLINE_LINE="$output"
        READLINE_POINT=${#READLINE_LINE}
    fi
}

bind -x '"\C-xe": _shelper_cmd_widget'
```

### Zsh Integration (`shell/shelper.zsh`)

```zsh
_shelper_cmd_widget() {
    local input="$BUFFER"
    [[ -z "$input" ]] && return

    local sock="${SHELPER_SOCK:-${XDG_RUNTIME_DIR:+"$XDG_RUNTIME_DIR/shelper.sock"}}"
    sock="${sock:-${TMPDIR:-/tmp}/shelper.$(id -u).sock}"

    if [[ ! -S "$sock" ]]; then
        return 1
    fi

    local payload
    payload=$(printf '{"input":%s,"variables":{"shell":"zsh"}}' "$(python3 -c "import json, sys; print(json.dumps(sys.argv[1]))" "$input")")

    local response
    response=$(echo "$payload" | socat - "UNIX-CONNECT:$sock" 2>/dev/null)

    local output
    output=$(echo "$response" | python3 -c "import json, sys; res=json.load(sys.stdin); print(res.get('output',''))" 2>/dev/null)

    if [[ -n "$output" ]]; then
        BUFFER="$output"
        CURSOR=${#BUFFER}
        zle redisplay
    fi
}

zle -N _shelper_cmd_widget
bindkey '^X^E' _shelper_cmd_widget
```
