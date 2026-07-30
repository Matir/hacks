# Technical Research: Background LLM Processing Service

## Overview & Technical Choices

### 1. Unix Domain Socket Protocol & Path Resolution
- **Decision**: Use Go `net.Listen("unix", socketPath)` with NDJSON (Newline-Delimited JSON) over stream connections.
- **Path Resolution Order**:
  1. `$SHELPER_SOCK` (if non-empty)
  2. `${XDG_RUNTIME_DIR}/shelper.sock` (if `XDG_RUNTIME_DIR` is set)
  3. `${TMPDIR}/shelper.${UID}.sock` (if `TMPDIR` is set, defaulting to `/tmp/shelper.${UID}.sock` if `TMPDIR` is unset; `UID` retrieved via `os.Getuid()`).
- **Rationale**: Unix domain sockets provide fast, secure local IPC without network port collisions. NDJSON allows streaming or simple framed request/response handling over standard TCP-like stream sockets.
- **Alternatives Considered**:
  - gRPC over IPC: Higher dependency weight and codegen requirements; simple JSON over socket meets requirements lighter and simpler.
  - HTTP over TCP: Port conflicts and local port exposure security risks; Unix domain sockets enforce OS file-permission security.

### 2. LLM Provider Interface Architecture
- **Decision**: Define a Go interface `Provider` in `llm`:
  ```go
  type Provider interface {
      Name() string
      Generate(ctx context.Context, req *GenerateRequest) (*GenerateResponse, error)
  }
  ```
- **Implementations**:
  - `GoogleGenAIProvider`: Wraps `google.golang.org/genai` client. Reads `GEMINI_API_KEY` or GCP credentials.
  - `OpenAIProvider`: Wraps `github.com/openai/openai-go` client. Reads `OPENAI_API_KEY` or custom endpoint settings.
- **Factory Pattern**: A provider registry instantiates the appropriate `Provider` based on request field `provider` (defaulting to `google` or `openai` if specified).
- **Rationale**: Decouples request handling from specific LLM vendors; easily extensible for future providers (e.g. Anthropic, Ollama).

### 3. Prompt Template Loading & Resolution
- **Decision**: Use Go `text/template` package with standard template variables (e.g. `{{.Input}}`, `{{.SystemInstruction}}`, `{{.Variables.shell}}`).
- **Resolution Strategy**:
  1. Check `$HOME/.config/shelper/prompt.md`. If file exists and is readable, load and parse it.
  2. If missing, fallback to bundled default prompt template embedded via Go `//go:embed prompt.md`.
  3. If request contains an inline template override (`req.Template`), use the inline template.
- **Rationale**: Empowers users to customize system prompt behavior globally without recompiling, while ensuring zero-config out-of-the-box operation via embedded fallback.

### 4. Interactive Shell Line Editor Integration (Bash & Zsh)
- **Decision**: Provide shell integration scripts `shell/shelper.bash` and `shell/shelper.zsh`.
- **Bash Readline Mechanism**:
  - Shell widget function binds to key via `bind -x '"\C-xe": _shelper_cmd_widget'`.
  - Inside function:
    - Reads line from `$READLINE_LINE`.
    - Detects shell name (`bash`).
    - Constructs NDJSON payload: `{"input":"$READLINE_LINE","variables":{"shell":"bash"}}`.
    - Dispatches to socket via `socat`, `nc -U`, or Go helper client binary if available (`shelper-cli`).
    - Parses JSON output field using `jq` or `python3 -c` / `grep` parsing fallback.
    - Replaces `$READLINE_LINE` with generated command output and sets `$READLINE_POINT=${#READLINE_LINE}`.
- **Zsh ZLE Mechanism**:
  - Defines widget function `_shelper_cmd_widget` and registers with `zle -N _shelper_cmd_widget`.
  - Binds to key: `bindkey '^X^E' _shelper_cmd_widget`.
  - Reads line from `$BUFFER`.
  - Replaces `$BUFFER` with generated command output and sets `$CURSOR=${#BUFFER}`.
  - Calls `zle redisplay`.
- **Rationale**: Native line editor integration allows instant command insertion into the active prompt line without copying & pasting or leaving the shell.

### 5. Concurrency & Daemon Lifecycle Management
- **Decision**: Use standard Go concurrency patterns (`sync.WaitGroup`, `context.Context` for cancellation, signal handling for `SIGTERM`/`SIGINT`).
- **Socket File Cleanup**: Implement `os.Remove(socketPath)` on startup (if stale socket exists) and on graceful shutdown.
- **Rationale**: Prevents "address already in use" errors on daemon restarts and ensures graceful termination of ongoing LLM calls.
