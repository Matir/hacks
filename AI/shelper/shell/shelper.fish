# SHelper Fish Command Line Integration
# Binds Ctrl+X Ctrl+E to query shelperd and replace the commandline buffer.
#
# To install, source this file in your ~/.config/fish/config.fish and configure bindings:
#
# source /path/to/shelper/shell/shelper.fish
# bind \cx\ce _shelper_cmd_widget

function _shelper_cmd_widget
    set -l input (commandline)
    if test -z "$input"
        return
    end

    # Resolve socket path following resolution rules
    set -l sock $SHELPER_SOCK
    if test -z "$sock"
        if set -q XDG_RUNTIME_DIR
            set sock "$XDG_RUNTIME_DIR/shelper.sock"
        else
            set -q TMPDIR; and set -l tmp "$TMPDIR"; or set -l tmp "/tmp"
            set sock "$tmp/shelper."(id -u)".sock"
        end
    end

    if not test -S "$sock"
        echo -e "\n[shelper] Error: Daemon socket not found at $sock"
        commandline -f repaint
        return 1
    end

    # Escape JSON input string safely using python3 json dump
    set -l escaped_input (python3 -c "import json, sys; print(json.dumps(sys.argv[1]))" "$input")

    # Construct request payload
    set -l payload (printf '{"input":%s,"variables":{"shell":"fish"}}' "$escaped_input")

    # Dispatch via socat
    set -l response (echo "$payload" | socat -t 60 - "UNIX-CONNECT:$sock" 2>/dev/null)

    if test -z "$response"
        return 1
    end

    # Extract output using python3
    set -l output (echo "$response" | python3 -c "
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

    if test -n "$output"
        commandline -r "$output"
        commandline -f repaint
    end
end
