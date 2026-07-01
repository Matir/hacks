# Quickstart & Validation Guide: Docker API Proxy

**Feature Branch**: `001-docker-api-proxy`

This guide outlines step-by-step verification scenarios to test the Docker API proxy across Unix and TCP sockets, semantic policy evaluation, response list filtering, and traffic recording.

---

## 1. Prerequisites

- Go 1.22+ installed (`go version`).
- Docker daemon running locally or accessible socket (default Unix socket: `/var/run/docker.sock`).
- `curl` CLI or `docker` CLI for sending test API commands.

---

## 2. Build the Proxy Binary

Build the CLI utility from the repository root:

```bash
go build -o bin/dockerproxy ./cmd/dockerproxy
```

---

## 3. Validation Scenario 1: Transparent Proxying (Unix Socket)

Verify that the proxy transparently forwards requests between a local Unix listening socket and the upstream Docker daemon Unix socket.

### Step 1: Start the proxy listening on a local Unix socket
```bash
./bin/dockerproxy \
  --listen="unix:///tmp/dockerproxy.sock" \
  --upstream="unix:///var/run/docker.sock"
```

### Step 2: Send a request through the proxy socket via `curl`
```bash
curl --unix-socket /tmp/dockerproxy.sock http://localhost/v1.43/containers/json
```

**Expected Outcome**: A valid JSON array listing active containers is returned, identical to querying `/var/run/docker.sock` directly.

---

## 4. Validation Scenario 2: Semantic Policy Denial Enforcement

Verify that semantic policy rulesets intercept and deny forbidden container operations (such as `--privileged` containers) with an HTTP 403 status.

### Step 1: Create a semantic policy ruleset file (`rules.yaml`)
Use the format specified in [contracts/ruleset.schema.yaml](file:///Users/davidtomaschik/Personal/hacks/go/dockerproxy/specs/001-docker-api-proxy/contracts/ruleset.schema.yaml):
```yaml
version: "1.0"
default_action: allow
rules:
  - id: block-privileged-containers
    action: deny
    methods: ["POST"]
    command_types: ["create"]
    path_pattern: "^/v[\\d\\.]+/containers/create.*"
    container_create:
      privileged: true
    message: "Security violation: Privileged containers are strictly prohibited."
```

### Step 2: Start the proxy with the ruleset loaded
```bash
./bin/dockerproxy \
  --listen="tcp://127.0.0.1:8080" \
  --upstream="unix:///var/run/docker.sock" \
  --rules="rules.yaml"
```

### Step 3: Test an unprivileged container create (Allowed)
```bash
curl -i -X POST -H "Content-Type: application/json" \
  -d '{"Image":"ubuntu","HostConfig":{"Privileged":false}}' \
  http://127.0.0.1:8080/v1.43/containers/create?name=safe_container
```
**Expected Outcome**: HTTP 201 Created (or 404 image not found from daemon, but NOT 403 Forbidden).

### Step 4: Test a privileged container create (Denied)
```bash
curl -i -X POST -H "Content-Type: application/json" \
  -d '{"Image":"ubuntu","HostConfig":{"Privileged":true}}' \
  http://127.0.0.1:8080/v1.43/containers/create?name=root_container
```
**Expected Outcome**: HTTP 403 Forbidden with payload containing `"Security violation: Privileged containers are strictly prohibited."`

---

## 5. Validation Scenario 3: Response List Filtering

Verify that semantic response filter rules sanitize container and image lists returned to multi-tenant clients.

### Step 1: Create a filter ruleset (`filter.yaml`)
```yaml
version: "1.0"
default_action: allow
rules:
  - id: filter-containers
    action: filter
    methods: ["GET"]
    command_types: ["list"]
    path_pattern: "^/v[\\d\\.]+/containers/json.*"
    response_filter:
      allowed_names:
        - "^allowed-.*"
```

### Step 2: Start proxy and query container lists
```bash
./bin/dockerproxy \
  --listen="unix:///tmp/dockerproxy.sock" \
  --upstream="unix:///var/run/docker.sock" \
  --rules="filter.yaml"
```
**Expected Outcome**: Querying `curl --unix-socket /tmp/dockerproxy.sock http://localhost/v1.43/containers/json` returns an array containing only container objects whose names match `^allowed-.*`.

---

## 6. Validation Scenario 4: Traffic Recording & Inspection

Verify structured JSON Lines recording for auditing.

### Step 1: Start proxy with recording enabled
```bash
./bin/dockerproxy \
  --listen="unix:///tmp/dockerproxy.sock" \
  --upstream="unix:///var/run/docker.sock" \
  --record="/tmp/traffic.jsonl"
```

### Step 2: Send requests through proxy socket
```bash
curl --unix-socket /tmp/dockerproxy.sock http://localhost/v1.43/version
```

### Step 3: Inspect recorded audit log
```bash
cat /tmp/traffic.jsonl
```
**Expected Outcome**: Each line is a valid JSON object matching [contracts/traffic-record.schema.json](file:///Users/davidtomaschik/Personal/hacks/go/dockerproxy/specs/001-docker-api-proxy/contracts/traffic-record.schema.json), capturing timestamps, methods, URIs, response status codes, and semantic evaluation outcomes.
