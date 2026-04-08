# GitHub App Token Broker: Design Requirements and Implementation Recommendations

## Purpose

This document describes the design requirements for a token broker that issues short-lived GitHub App installation tokens to AI agents. The broker exists to let agents clone repositories, push to non-protected branches, open pull requests, and comment on pull requests or issues **without** exposing a personal access token or giving agents broad, long-lived GitHub credentials.

The broker is a policy enforcement point, not just a relay. Its job is to:

- hold or access the GitHub App private key indirectly
- authenticate calling agents
- authorize which repositories and permissions each agent may request
- mint narrowly scoped, short-lived installation tokens
- return tokens only when the request matches policy
- provide auditability for every token issued

## Goals

The broker should enable the following:

- agents can read code from allowed repositories
- selected agents can push commits to feature branches
- selected agents can open pull requests
- selected agents can comment on pull requests and issues
- no agent can push directly to `main` or any protected branch by policy or GitHub enforcement
- no agent can change repository settings, branch protection, rulesets, or app installation settings
- no personal GitHub token is stored on the agent host
- no long-lived GitHub credential is exposed to ordinary agent runtime containers

## Non-Goals

The broker should **not**:

- act as a general-purpose GitHub proxy for arbitrary requests
- expose the GitHub App private key to agent containers
- decide repository protection strategy inside GitHub itself
- replace GitHub branch protection or rulesets
- provide broad org-wide credentials to all agents

## Security Model

### Core principle

The broker must be treated as a high-trust component. If it can mint installation tokens, it effectively controls the blast radius of every connected agent. Because of that, it must enforce authorization rules for each caller.

A separate Docker container is not, by itself, a meaningful authorization boundary. If any container that can reach the broker can request any repo and any permission, then the broker is only a token vending machine.

### Required defense layers

The design should assume three layers of control:

1. **GitHub App maximum permissions**
   - The app defines the outer bound of what is ever possible.
2. **Broker authorization policy**
   - The broker decides what each agent is actually allowed to request.
3. **GitHub branch protection / rulesets**
   - GitHub enforces that protected branches cannot be pushed directly, even by agents that have `contents: write`.

## Functional Requirements

### 1. Agent authentication

The broker must authenticate the calling agent before issuing a token.

Minimum acceptable options:

- per-agent API key
- signed JWT per agent
- mTLS between agent and broker
- workload identity if running in Kubernetes or a service mesh

Recommended progression:

- small setup: per-agent API key over an internal-only network
- medium setup: signed workload identity or mTLS
- larger setup: service identity backed by platform-native workload identity

### 2. Agent authorization

The broker must maintain policy that maps each agent identity to:

- allowed repositories
- allowed operations
- maximum GitHub permissions it may request
- optional environment restrictions such as dev/staging/prod

Example policy:

```yaml
agents:
  reviewer-agent:
    allowed_repos:
      - org/repo1
      - org/repo2
    max_permissions:
      contents: read
      pull_requests: write
      issues: write
      metadata: read

  coder-agent:
    allowed_repos:
      - org/repo1
    max_permissions:
      contents: write
      pull_requests: write
      issues: write
      metadata: read
```

The broker must deny requests for:

- repositories not explicitly allowed for that agent
- permissions above the agent’s policy
- permissions above the GitHub App installation’s grant
- repositories not installed for the GitHub App

### 3. Repository-scoped token issuance

The broker must mint tokens scoped to the smallest practical set of repositories.

Recommended default:

- one token per task
- one repository per token

Do **not** mint one broad token covering all repositories the app can access unless there is a compelling, documented reason.

### 4. Permission downscoping

The broker must request only the minimum permissions needed for the specific task.

Examples:

- comment-only task:
  - `issues: write`
  - `pull_requests: write`
  - `metadata: read`
  - no `contents: write`
- code change task:
  - `contents: write`
  - `pull_requests: write`
  - `issues: write`
  - `metadata: read`
- read-only analysis task:
  - `contents: read`
  - `metadata: read`

### 5. Short-lived credentials

The broker must issue only short-lived installation tokens and should never transform them into longer-lived local credentials.

Operational guidance:

- mint tokens on demand
- return them only to the authenticated caller
- avoid persisting tokens to disk
- keep tokens in memory only where practical
- let agents refresh by requesting a new token rather than reusing stale credentials

### 6. Audit logging

The broker must log every token request and issuance decision.

At minimum, log:

- timestamp
- caller identity
- requested repository or repositories
- requested permissions
- granted permissions
- allow or deny decision
- reason for denial, if applicable
- task ID, job ID, or correlation ID if available

Logs should not contain the token value itself.

### 7. Safe failure behavior

The broker must fail closed.

If any of the following are unknown or unavailable, it should deny the request:

- caller identity
- policy lookup result
- target repository mapping
- GitHub installation mapping
- secret retrieval for the app private key

## GitHub App Requirements

The broker design assumes the use of a GitHub App rather than a personal access token.

### Recommended app permissions

For a code-writing agent that opens pull requests and comments:

- `Contents`: read or write depending on task type
- `Pull requests`: write
- `Issues`: write
- `Metadata`: read

### Permissions to avoid by default

Do not grant these unless there is a clear, reviewed requirement:

- `Administration`
- `Members`
- `Secrets`
- `Actions` administrative permissions
- `Workflows` unless agents genuinely need to modify GitHub Actions workflows

### Installation strategy

Install the app on **selected repositories only**, not all repositories in the organization, unless there is a strong operational reason to do otherwise.

## GitHub Enforcement Requirements

The broker alone is not enough to prevent direct pushes to `main`.

Repositories must also enforce:

- branch protection or rulesets on `main` and other critical branches
- required pull requests before merging
- required status checks as needed
- no bypass permission for the GitHub App unless intentionally reviewed

This matters because an installation token with `contents: write` can push anywhere that repository rules permit.

## API Design Requirements

A minimal broker API can stay very small.

### Example request

```json
{
  "agent_id": "coder-agent",
  "repo": "org/repo1",
  "requested_permissions": {
    "contents": "write",
    "pull_requests": "write",
    "issues": "write",
    "metadata": "read"
  },
  "task_id": "job-12345",
  "purpose": "apply patch and open PR"
}
```

### Example response

```json
{
  "token": "<installation_token>",
  "expires_at": "2026-04-07T20:15:00Z",
  "repo": "org/repo1",
  "granted_permissions": {
    "contents": "write",
    "pull_requests": "write",
    "issues": "write",
    "metadata": "read"
  }
}
```

### API rules

The API should:

- accept exactly one repo by default
- validate repo name against a canonical allowlist
- validate requested permissions against agent policy
- include a correlation ID in both request handling and logs
- avoid returning unnecessary GitHub metadata

## Secret Management Requirements

The GitHub App private key should not be baked into agent images or normal runtime environment variables.

Recommended order of preference:

1. secret manager or vault-backed retrieval
2. mounted secret with strict file permissions
3. environment variable only for small local development setups

Best practice:

- the broker accesses the private key
- agents never access the private key
- only the broker can mint installation tokens

## Network and Deployment Requirements

### Minimum

- broker reachable only on an internal network
- broker reachable via unix domain socket
- no direct public exposure
- firewall or Docker network rules limiting which containers can call it
- health check endpoint separated from token issuance endpoint

### Better

- broker on a dedicated private network segment
- mTLS or service identity between callers and broker
- rate limiting per agent identity
- request size limits and timeouts

### Container guidance

Running the broker in a different Docker container is useful for separation of concerns, but it is not enough by itself. The network path to the broker must be restricted, and the broker must still authenticate and authorize callers.

## Git Operations Recommendations

Do not embed short-lived tokens permanently in the remote URL for long-running workspaces.

Preferred approaches:

- inject a fresh token through a Git credential helper
- inject a fresh token per command via headers or askpass
- keep repository remotes clean, for example:

```text
https://github.com/org/repo.git
```

Recommended pattern:

1. agent requests token for one repo
2. broker returns short-lived installation token
3. agent performs clone/fetch/push for that task
4. token is discarded
5. later operations request a new token

## Operational Recommendations

### Start simple, but with policy

A good staged rollout looks like this:

#### Phase 1

- one broker container
- internal-only access
- per-agent API key
- static YAML policy file
- repo-scoped tokens
- minimal audit logs

#### Phase 2

- secret manager for GitHub App private key
- policy stored in a database or config service
- structured logs shipped centrally
- rate limiting
- mTLS or stronger workload identity

#### Phase 3

- policy by environment and task type
- approval workflow for privileged repos
- anomaly detection or alerting on unusual token requests
- ephemeral execution environments per task

### Keep task types explicit

It is useful to classify requests so the broker can apply narrower defaults:

- `read_code`
- `comment_issue`
- `comment_pr`
- `create_branch`
- `push_branch`
- `open_pr`

Then map each task type to a default permission template.

## Suggested Internal Architecture

A minimal implementation can have these components:

1. **API layer**
   - authenticates caller
   - validates request schema
2. **Policy engine**
   - resolves agent policy
   - compares requested repo and permissions to allowed scope
3. **GitHub App client**
   - signs JWT
   - requests installation token from GitHub
4. **Secrets layer**
   - retrieves private key from secure storage
5. **Audit logger**
   - records every decision

Simple flow:

```text
Agent -> Broker API -> AuthN/AuthZ -> GitHub App token mint -> Response
```

## Recommended Implementation Choices

### Language

Choose a language with strong HTTP, JSON, and GitHub SDK support.

Practical choices:

- Go
  - good for small static binaries
  - simple deployment
  - strong concurrency and networking primitives
- Node.js / TypeScript
  - excellent GitHub App support through Octokit
  - fast to implement

For a fast prototype, TypeScript is usually the shortest path. For a minimal production service with low operational overhead, Go is a strong choice.

### Data model

Use a simple data model first:

- `Agent`
- `AllowedRepo`
- `MaxPermissionSet`
- `TaskType`
- `AuditEvent`

Keep the first version human-editable. A YAML or JSON config file is usually enough until there are many agents.

### Caching

Use cautious, short-lived caching only where it reduces repeated GitHub API calls.

Safe candidates:

- repository name to repository ID mapping
- installation ID lookup

Avoid long-lived caching of installation tokens unless the cache is tightly bounded and memory-only.

## Example Policy Structure

```yaml
agents:
  coder-agent:
    auth:
      api_key_id: coder-agent-key
    repos:
      - name: org/repo1
        task_types:
          - read_code
          - create_branch
          - push_branch
          - open_pr
          - comment_pr
          - comment_issue
    default_permissions:
      contents: write
      pull_requests: write
      issues: write
      metadata: read

  reviewer-agent:
    auth:
      api_key_id: reviewer-agent-key
    repos:
      - name: org/repo1
        task_types:
          - read_code
          - comment_pr
          - comment_issue
      - name: org/repo2
        task_types:
          - read_code
          - comment_pr
    default_permissions:
      contents: read
      pull_requests: write
      issues: write
      metadata: read
```

## Testing Requirements

The broker should have tests for:

- valid request for allowed repo and permission set
- denied request for disallowed repo
- denied request for elevated permissions
- denied request with invalid caller identity
- denied request when secret retrieval fails
- denied request when GitHub installation lookup fails
- logging behavior for both allow and deny cases

Also test integration behavior with:

- a real GitHub App in a test repository
- protected branches to verify direct push prevention works as expected

## Risks and Failure Modes

### Risk: broker becomes a universal token vending machine

Mitigation:

- enforce per-agent authorization
- deny unknown callers
- log everything

### Risk: app has overly broad permissions

Mitigation:

- keep GitHub App permissions narrow
- avoid administrative permissions
- review installation scope regularly

### Risk: direct push to protected branches

Mitigation:

- enforce branch protection or rulesets in GitHub
- do not add app to bypass lists unless explicitly required

### Risk: leaked token in logs or shell history

Mitigation:

- never log token values
- avoid embedding tokens in persistent remote URLs
- use in-memory or per-command injection

### Risk: broker compromise

Mitigation:

- isolate broker
- protect secrets with a secret manager
- minimize network exposure
- monitor audit logs

## Final Recommendations

1. Build the broker as a **policy enforcement point**, not a pure proxy.
2. Use a **GitHub App**, not a personal access token.
3. Install the app on **selected repositories only**.
4. Mint **one short-lived, repo-scoped token per task**.
5. Downscope permissions to exactly what the task needs.
6. Enforce **branch protection or rulesets** in GitHub so write-capable agents still cannot push directly to `main`.
7. Keep the first implementation simple:
   - internal-only network
   - per-agent API key
   - static policy file
   - structured audit logs
8. Upgrade later to stronger workload identity, secret management, and centralized policy as the system grows.

## Minimal Viable Version

If the goal is to get something safe and usable quickly, the minimum viable broker should include:

- internal HTTP API
- per-agent authentication
- static allowlist policy by repo and permission
- GitHub App installation token minting
- repo-scoped token requests
- deny-by-default behavior
- structured audit logs

That is enough to deliver meaningful security value without turning the system into an infrastructure project.

