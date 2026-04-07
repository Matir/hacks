# HandHolder

HandHolder is a Go-based service to manage and launch OpenHands workspace containers. It provides a simple web interface to switch between different pre-configured workspaces, ensuring that only one workspace is active per port.

## Features
- **Docker SDK Integration:** Uses the official Docker Go SDK for robust container management.
- **Mutual Exclusion per Port:** Automatically stops any running container on the target port before launching a new one.
- **Prioritized Environment Variables:** 
  1. Global `env_file`
  2. Global `env` map
  3. Workspace `env_file`
  4. Workspace `env` map
- **Automatic Image Pulling:** Automatically pulls the required OpenHands image if it's missing locally.
- **Web UI:** A basic HTML interface (embedded in the binary) with real-time status polling.
- **Port Mapping:** Host workspaces are mounted to `/opt/workspace_base` in the container.

## Configuration (handholder.toml)

```toml
[handholder]
port = 3001      # Port for the HandHolder service
logging = "stderr" # "stdout", "stderr", or a file path
logformat = "json" # Currently supports standard log output
docker_socket = "unix:///var/run/docker.sock" # Optional: Custom Docker socket path

[defaults]
port = 3000      # Default port for OpenHands instances
image = "ghcr.io/all-hands-ai/openhands:0.21.0"
env_file = "/path/to/global.env"
[defaults.env]
LLM_MODEL = "openai/gpt-4o"

[workspace.alpha]
name = "Alpha Project"
workspace = "/absolute/host/path/to/alpha"
port = 3000      # Optional override
env_file = "/path/to/alpha.env"
[workspace.alpha.env]
LLM_API_KEY = "sk-..."
```

## Running
1. Ensure Docker is running.
2. Build: `go build -o handholder ./cmd/handholder`
3. Run: `./handholder -config handholder.toml`
4. Visit `http://localhost:3001` to manage workspaces.
