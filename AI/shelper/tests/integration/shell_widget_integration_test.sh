#!/bin/bash
# Test script for shelper bash widget integration function.

set -euo pipefail

# 1. Start the daemon in the background with a custom socket path
tmpdir=$(mktemp -d)
defer_cleanup() {
    rm -rf "$tmpdir"
}
trap defer_cleanup EXIT

sock_path="$tmpdir/shelper.sock"

# Build daemon if not already built
go build -o "$tmpdir/shelperd" ./cmd/shelperd

# Start python background unix domain socket listener
python3 -c '
import socket, sys
sock_path = sys.argv[1]
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.bind(sock_path)
s.listen(1)
while True:
    try:
        conn, addr = s.accept()
        data = conn.recv(1024)
        if data:
            conn.sendall(b"{\"id\":\"\",\"status\":\"success\",\"output\":\"ls -la\",\"metadata\":{\"provider\":\"mock\",\"model\":\"mock\",\"latency_ms\":10,\"template_source\":\"bundled\"}}\n")
        conn.close()
    except Exception:
        break
' "$sock_path" &

bg_pid=$!
defer_cleanup_all() {
    kill $bg_pid 2>/dev/null || true
    rm -rf "$tmpdir"
}
trap defer_cleanup_all EXIT

# Give the Go listener a moment to start
sleep 0.5

# 2. Source the widget script
# We will simulate the readline line value
export SHELPER_SOCK="$sock_path"
source ./shell/shelper.bash

# 3. Initialize simulated readline state
READLINE_LINE="list files in detailed format"
READLINE_POINT=0

# 4. Call the widget function manually
_shelper_cmd_widget

# 5. Assert the buffer was replaced by the mock response
expected="ls -la"
if [[ "$READLINE_LINE" != "$expected" ]]; then
    echo "FAIL: expected buffer to be '$expected', got '$READLINE_LINE'"
    exit 1
fi

echo "PASS: shell widget integration test passed successfully."
exit 0
