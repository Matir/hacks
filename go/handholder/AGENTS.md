# Agent Guidelines: HandHolder

For general information on this project, see [README.md](README.md).

## Technical Principles

- **Docker SDK:** Always use `github.com/docker/docker/client` for Docker interactions. Avoid the `docker` CLI. Support custom Docker socket paths via `handholder.docker_socket`.
- **Port-Specific Mutex:** HandHolder manages multiple OpenHands instances on different ports. When starting a container on a port, ensure any existing container named `handholder-openhands-<port>` is stopped and removed first.
- **Container Labels:** All containers launched by HandHolder MUST have the label `managed-by=handholder`. Use this label to identify and clean up containers.
- **Environment Variables:** Strictly follow the merge priority:
    1. Global/Default `env_file`
    2. Global/Default `env` map
    3. Workspace-specific `env_file`
    4. Workspace-specific `env` map
- **Web UI:** Use Go's `embed` package to bundle HTML/CSS/JS. Keep the frontend simple and reactive via polling.
- **Path Mapping:** Always map the workspace host path to `/opt/workspace_base` inside the container.
- **Graceful Shutdown:** Use a 5-second timeout for `docker stop` to allow OpenHands to save its state.

- **Testing & Validation:** Always ensure that any changes are verified by running both `go vet ./...` (for static analysis) and `go test ./...` (to run all unit and integration tests). A change is only complete when both commands pass successfully.
- `config/config.go`: Configuration parsing and environment variable resolution.
- `docker/manager.go`: Docker SDK operations.
- `web/server.go`: Web handlers and API.
- `web/templates/`: Embedded HTML templates.
- `cmd/handholder/main.go`: Entry point and logging initialization.
