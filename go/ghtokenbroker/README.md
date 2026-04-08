# GitHub Token Broker

A policy enforcement point that issues short-lived GitHub App installation tokens to AI agents or other automated processes. The broker holds the GitHub App private key and enforces per-agent authorization — agents never see the key and can only obtain tokens for the repositories and permissions they are explicitly permitted.

## What it does

- Authenticates callers via per-agent API keys
- Enforces a per-agent allowlist of repositories and maximum permission levels
- Mints narrowly scoped, short-lived GitHub installation tokens on demand
- Writes structured audit logs (JSON, stdout) for every allow/deny decision
- Fails closed: any unknown caller, disallowed repo, or upstream failure returns an error

## Quick start

### 1. Create a GitHub App

In your GitHub organization or account:

1. Go to **Settings → Developer settings → GitHub Apps → New GitHub App**.
2. Set permissions to the minimum needed (e.g. `Contents: Read`, `Pull requests: Write`, `Issues: Write`, `Metadata: Read`).
3. Install the app on **selected repositories only**.
4. Generate and download a private key (PEM file).
5. Note the **App ID**.

### 2. Write a config file

```toml
[server]
tcp_addr    = "127.0.0.1:8080"
unix_socket = "/run/ghtokenbroker.sock"

[github_app]
app_id           = 12345
private_key_file = "/secrets/github-app.pem"

[cache]
installation_ttl = "5m"

[[agents]]
id            = "coder-agent"
api_key       = "change-me-use-a-random-secret"
allowed_repos = ["myorg/myrepo"]

[agents.max_permissions]
contents      = "write"
pull_requests = "write"
issues        = "write"
metadata      = "read"
```

Restrict the config file to `600` permissions — it contains the agent API keys.

### 3. Build and run

```sh
go build -o ghtokenbroker ./cmd/ghtokenbroker
./ghtokenbroker -config config.toml
```

### 4. Request a token

```sh
curl -s -X POST http://127.0.0.1:8080/v1/token \
  -H "Authorization: Bearer change-me-use-a-random-secret" \
  -H "Content-Type: application/json" \
  -d '{
    "repo": "myorg/myrepo",
    "requested_permissions": {"contents": "write", "metadata": "read"},
    "task_id": "job-001",
    "purpose": "apply patch"
  }'
```

Response:

```json
{
  "token": "ghs_...",
  "expires_at": "2026-04-07T19:00:00Z",
  "repo": "myorg/myrepo",
  "granted_permissions": {"contents": "write", "metadata": "read"}
}
```

Use the token as a Git credential or as a `GITHUB_TOKEN` environment variable for `gh` CLI calls. Tokens are short-lived (~1 hour); request a new one for each task rather than caching them.

## Security notes

- The broker is an internal service. Do not expose it to the public internet.
- GitHub branch protection or rulesets on `main` are still required — a token with `contents: write` can push to any unprotected branch.
- API keys in the config file must be treated as secrets. Use a secrets manager or mounted secret volume in production; do not bake them into container images.
- For production deployments, prefer GCP Secret Manager for the GitHub App private key (`gcp_secret_name` in `[github_app]`) over a file on disk.
- See [design_requirements.md](design_requirements.md) for the full security model and threat analysis.

## Configuration reference

| Field | Description |
|---|---|
| `server.tcp_addr` | TCP listen address (e.g. `":8080"`). Empty to disable. |
| `server.unix_socket` | Unix socket path. Empty to disable. At least one listener required. |
| `github_app.app_id` | GitHub App ID (integer). |
| `github_app.private_key_file` | Path to PEM private key. Mutually exclusive with `gcp_secret_name`. |
| `github_app.gcp_secret_name` | GCP Secret Manager resource name. Mutually exclusive with `private_key_file`. |
| `cache.installation_ttl` | How long to cache GitHub installation ID lookups (Go duration, e.g. `"5m"`). |
| `agents[].id` | Human-readable agent identifier (appears in audit logs). |
| `agents[].api_key` | Secret bearer token the agent presents. |
| `agents[].allowed_repos` | List of `owner/repo` strings the agent may request tokens for. |
| `agents[].max_permissions` | Map of permission name → max level (`"read"` or `"write"`). |

## Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/v1/token` | Request an installation token. |
| `GET` | `/healthz` | Health check — returns `{"status":"ok"}`. |