# HandHolder

HandHolder is a Go-based service to manage and launch OpenHands workspace containers. It provides a simple web interface to switch between different pre-configured workspaces, ensuring that only one workspace is active per port.

## Features
- **Docker SDK Integration:** Uses the official Docker Go SDK for robust container management.
- **Mutual Exclusion per Port:** Automatically stops any running container on the target port before launching a new one.
- **Prioritized Environment Variables:** 
  1. Default `RUNTIME=docker`
  2. Global/Default explicit settings (`sandbox_user_id`, `sandbox_base_image`, `llm_model`, `llm_provider`, `llm_api_key`)
  3. Global/Default `env_file`
  4. Global/Default `env` map
  5. Workspace-specific explicit settings
  6. Workspace-specific `env_file`
  7. Workspace-specific `env` map
- **Automatic Sandbox UID Mapping:** Defaults to the current user's UID to prevent permission issues.
- **Provider-Aware LLM Configuration:** Automatically prefixes `llm_model` with `llm_provider` if specified.
- **Web UI:** A basic HTML interface (embedded in the binary) with real-time status polling.
- **Port Mapping:** Host workspaces are mounted to `/opt/workspace_base` in the container.

## Configuration (handholder.toml)

```toml
[handholder]
bind_address = "127.0.0.1" # Optional: IP address to bind to
port = 3001      # Port for the HandHolder service
logging = "stderr" # "stdout", "stderr", or a file path
logformat = "json" # Currently supports standard log output
docker_socket = "unix:///var/run/docker.sock" # Optional: Custom Docker socket path
trusted_proxies = ["127.0.0.1", "::1"] # Optional: List of trusted proxy IPs or CIDRs

[defaults]
port = 3000      # Default port for OpenHands instances
image = "ghcr.io/all-hands-ai/openhands:0.21.0"
sandbox_base_image = "debian" # Optional: Passed as SANDBOX_BASE_CONTAINER_IMAGE (default tag :latest)
llm_model = "claude-3-5-sonnet-20240620"
llm_provider = "anthropic"
llm_api_key = "sk-..." # Optional: Passed as LLM_API_KEY
env_file = "/path/to/global.env"

[workspace.alpha]
name = "Alpha Project"
workspace = "/absolute/host/path/to/alpha"
port = 3000      # Optional override
llm_model = "gpt-4o"
llm_provider = "openai"
sandbox_base_image = "ubuntu:22.04" # Workspace override
env_file = "/path/to/alpha.env"
[workspace.alpha.env]
CUSTOM_SETTING = "value"
```

## Running
1. Ensure Docker is running.
2. Build: `go build -o handholder ./cmd/handholder`
3. Run: `./handholder -config handholder.toml`
4. Visit `http://localhost:3001` to manage workspaces.

### Command-line Overrides
You can override settings in the `[handholder]` block using flags:
- `-bind-address <ip>`: IP address to bind to.
- `-port <port>`: Port for the HandHolder service.
- `-logging <path>`: Logging output destination (stdout, stderr, or file).
- `-logformat <text|json>`: Logging format.
- `-docker-socket <path>`: Docker socket path.
- `-trusted-proxies <ips>`: Comma-separated list of trusted proxy IPs/CIDRs.
