# GitHub Token Broker — Agent Guide

See @README.md for a general description and @design_requirements.md for the full security model.

## Implementation Requirements

- Language: Go (module `github.com/matir/hacks/go/ghtokenbroker`)
- Unit tests for all packages; err on the side of more coverage.
- `go vet ./...` and `gofmt -l .` must produce no output before committing.
- Both TCP and Unix domain socket listeners are supported simultaneously.
- Use official client libraries: `google/go-github/v84`, `bradleyfalzon/ghinstallation/v2`.

## Package Layout

```
cmd/ghtokenbroker/   Entry point for the broker server (main package)
cmd/ghtok/           Client CLI for fetching tokens (main package)
config/              TOML config loading and PermissionSet type
secrets/             GitHub App private key loading (PEM file or GCP Secret Manager)
cache/               Generic in-memory TTL cache
audit/               Structured JSON audit logger (writes to io.Writer)
policy/              Agent authentication and authorization engine
github/              GitHub App client: installation ID lookup + token minting
server/              HTTP handlers, middleware, TCP + Unix socket listeners
```

## Configuration

Single TOML file (default `config.toml`, override with `-config <path>`).

```toml
[server]
tcp_addr    = ":8080"             # empty to disable
unix_socket = "/run/broker.sock" # empty to disable

[github_app]
app_id           = 12345
private_key_file = "/secrets/app.pem"
# gcp_secret_name = "projects/my-project/secrets/gh-key/versions/latest"

[cache]
installation_ttl = "5m"

[[agents]]
id            = "coder-agent"
api_key       = "..."
allowed_repos = ["org/repo1"]

[agents.max_permissions]
contents      = "write"
pull_requests = "write"
issues        = "write"
metadata      = "read"
```

Exactly one of `private_key_file` or `gcp_secret_name` must be set. At least one of `tcp_addr` or `unix_socket` must be set.

## API

### POST /v1/token

Authentication: `Authorization: Bearer <api_key>`

Request:
```json
{
  "repo":                  "org/repo1",
  "requested_permissions": {"contents": "write", "pull_requests": "write"},
  "task_id":               "job-123",
  "purpose":               "apply patch and open PR"
}
```

Response `200`:
```json
{
  "token":               "<installation_token>",
  "expires_at":          "2026-04-07T20:15:00Z",
  "repo":                "org/repo1",
  "granted_permissions": {"contents": "write", "pull_requests": "write"}
}
```

Error responses: `{"error": "<reason>"}` with HTTP status `400`, `401`, `403`, or `503`.

Pass `X-Request-ID` in the request to correlate audit log entries; if absent, one is generated.

### GET /healthz

Returns `{"status":"ok"}` with HTTP `200`.

## Agent Authentication and Authorization

- Agents identify via `Authorization: Bearer <api_key>`.
- API keys are configured per-agent in the TOML file and must be kept secret.
- The broker denies requests for repos not in `allowed_repos` or permissions exceeding `max_permissions`.
- Permission levels: `"read"` < `"write"`. Requesting `"write"` when the max is `"read"` is denied.
- Recognized permission names: `contents`, `pull_requests`, `issues`, `metadata`, `actions`, `checks`, `deployments`, `environments`, `pages`, `statuses`.

## Fail-Closed Behavior

The broker returns an error (never a token) when:

- `Authorization` header is absent or the key is unknown → `401`
- Repo not in agent's allowlist → `403`
- Requested permission exceeds maximum → `403`
- Request body is malformed → `400`
- GitHub installation lookup fails → `503`
- Installation token minting fails → `503`

## Audit Logging

Every request — allowed and denied — produces a JSON line on stdout:

```json
{
  "timestamp": "2026-04-07T18:00:00Z",
  "correlation_id": "...",
  "caller_id": "coder-agent",
  "repo": "org/repo1",
  "task_id": "job-123",
  "requested_permissions": {"contents": "write"},
  "granted_permissions": {"contents": "write"},
  "decision": "allow"
}
```

Token values never appear in audit logs.

## Using ghtok

`ghtok` is the purpose-built client for the token broker. Build it alongside the server:

```sh
go build -o ghtok ./cmd/ghtok
```

### Configuration

Create `~/.ghtok` (TOML) with your agent credentials:

```toml
api_key = "<your-agent-api-key>"
server  = "unix:///run/ghtokenbroker.sock"
# or: server = "tcp://127.0.0.1:8080"
default_permissions = ["contents:write", "metadata:read"]
```

Configuration is also accepted via environment variables (`GHTOK_API_KEY`,
`GHTOK_SERVER`) or flags (`--api-key`, `--server`), each overriding the
previous source.

### Fetching a token

```sh
# Print the raw token to stdout — useful in scripts
TOKEN=$(ghtok --repo myorg/myrepo --permissions contents:write,metadata:read)
```

### Transparent gh wrapper

Place `ghtok` earlier in `PATH` than the real `gh`, or symlink it as `gh`.
It detects the current repository from `git remote origin`, fetches a token,
and execs the real `gh` binary with `GH_TOKEN` set. All arguments pass through
unchanged.

```sh
ln -s /usr/local/bin/ghtok /usr/local/bin/gh
gh pr create --title "automated change"   # token injected automatically
```

Alternatively, prefix any `gh` invocation explicitly:

```sh
ghtok gh issue list --repo myorg/myrepo
```

### Git credential helper

Configure `ghtok` as a git credential helper so `git push`/`git pull`
authenticate automatically:

```sh
git config --global credential.helper ghtok
# Scope to github.com only:
git config --global credential.https://github.com.helper ghtok
```

When git requests credentials, `ghtok` returns:
```
username=x-access-token
password=<installation_token>
```

The repo is derived from the credential `path` field supplied by git, or falls
back to `git remote get-url origin` in the current directory.