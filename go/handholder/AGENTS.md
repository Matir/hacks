# Agent Guidelines: HandHolder

For general information on this project, see [README.md](README.md).

## Technical Principles

- **Docker SDK:** Always use `github.com/docker/docker/client` for Docker interactions. Avoid the `docker` CLI. Support custom Docker socket paths via `handholder.docker_socket`.
- **Port-Specific Mutex:** HandHolder manages multiple OpenHands instances on different ports. When starting a container on a port, ensure any existing container named `handholder-openhands-<port>` is stopped and removed first.
- **Container Labels:** All containers launched by HandHolder MUST have the label `managed-by=handholder`. Use this label to identify and clean up containers.
- **Environment Variables:** Strictly follow the merge priority:
    1. Default `RUNTIME=docker` (from `config.DefaultEnv`)
    2. Global/Default explicit settings (`sandbox_user_id` [UID], `sandbox_base_image` [tag], `llm_model`, `llm_provider`, `llm_api_key`)
    3. Global/Default `env_file`
    4. Global/Default `env` map
    5. Workspace-specific explicit settings
    6. Workspace-specific `env_file`
    7. Workspace-specific `env` map
- **Web UI:** Use Go's `embed` package to bundle HTML/CSS/JS. Keep the frontend simple and reactive via polling.
- **HTTP Method Enforcement:** State-changing endpoints (`/launch`, `/stop`) must only accept `POST`. Handlers must check `r.Method == http.MethodPost` and return `405 Method Not Allowed` otherwise.
- **CSRF Protection:** All non-GET/HEAD requests are protected by the `withCSRF` middleware, which validates the `X-CSRF-Token` request header against a server-wide token (32 random bytes, hex-encoded, generated at startup). Requests with a missing or incorrect token receive `403 Forbidden`. The token is embedded in the HTML page via the `{{.CSRFToken}}` template field and sent by JavaScript as an `X-CSRF-Token` header on every mutating `fetch` call. Never embed the CSRF token in URLs or cookies.
- **Path Mapping:** Always map the workspace host path to `/workspace` inside the container.
- **Graceful Shutdown:** Use a 5-second timeout for `docker stop` to allow OpenHands to save its state.

- **Structured Logging:** Use `log/slog` for all logging.
    - Follow context-aware logging by retrieving the logger from `context.Context` via `getLogger(ctx)`.
    - Ensure `workspace_id` is logged for all workspace operations.
    - POST and `/launch` requests should include a 32-bit hex `req_id` and `client_ip` (resolved via trusted proxies).

- **Mocking & Testing:** 
    - Use the `docker/mock` package for unit tests.
    - `docker_mock.FakeDockerClient` emulates the Docker SDK behavior in-memory.
    - `docker_mock.FakeManager` provides a high-level mock for the `DockerManager` interface.
    - Always maintain high test coverage (>75% for core logic).

- **Command-line Overrides:** All settings in the `[handholder]` block can be overridden via command-line flags (e.g., `-bind-address`, `-port`, `-logging`, `-logformat`, `-docker-socket`, `-trusted-proxies`). These flags take precedence over values in the TOML configuration file.

- **Testing & Validation:** Always ensure that any changes are verified by running:
    1. `gofmt -w .` to format all code.
    2. `go vet ./...` for static analysis.
    3. `go test ./...` to run all unit and integration tests.
    A change is only complete when all commands pass successfully.
- `config/config.go`: Configuration parsing and environment variable resolution.
- `docker/manager.go`: Docker SDK operations.
- `web/server.go`: Web handlers and API.
- `web/templates/`: Embedded HTML templates.
- `cmd/handholder/main.go`: Entry point and logging initialization.
