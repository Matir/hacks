# SHelper Bash Readline Integration
# Binds Ctrl+X Ctrl+E to query shelperd and replace the line buffer with the response.

_shelper_cmd_widget() {
    local input="$READLINE_LINE"
    [[ -z "$input" ]] && return

    # Resolve socket path following resolution rules
    local sock="${SHELPER_SOCK:-${XDG_RUNTIME_DIR:+"$XDG_RUNTIME_DIR/shelper.sock"}}"
    sock="${sock:-${TMPDIR:-/tmp}/shelper.$(id -u).sock}"

    if [[ ! -S "$sock" ]]; then
        echo -e "\n[shelper] Error: Daemon socket not found at $sock"
        return 1
    fi

    # Escape JSON input string safely using python3 json dump
    local escaped_input
    escaped_input=$(python3 -c "import json, sys; print(json.dumps(sys.argv[1]))" "$input")

    # Construct request payload
    local payload
    payload=$(printf '{"input":%s,"variables":{"shell":"bash"}}' "$escaped_input")

    # Dispatch via socat
    local response
    response=$(echo "$payload" | socat -t 15 - "UNIX-CONNECT:$sock" 2>/dev/null)

    if [[ -z "$response" ]]; then
        return 1
    fi

    # Extract output using python3
    local output
    output=$(echo "$response" | python3 -c "
import json, sys
try:
    res = json.load(sys.stdin)
    if res.get('status') == 'success':
        print(res.get('output', ''))
    else:
        err = res.get('error', {})
        print(f\"Error: {err.get('message')}: {err.get('details')}\", file=sys.stderr)
except Exception as e:
    print(f\"Parse failed: {e}\", file=sys.stderr)
" 2>/dev/null)

    if [[ -n "$output" ]]; then
        READLINE_LINE="$output"
        READLINE_POINT=${#READLINE_LINE}
    fi
}

# Bind to Ctrl+X Ctrl+E
bind -x '"\C-xe": _shelper_cmd_widget'
