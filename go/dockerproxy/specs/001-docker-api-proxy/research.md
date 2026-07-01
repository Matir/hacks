# Technical Research: Docker API Proxy & Ruleset Recording

**Feature Branch**: `001-docker-api-proxy`
**Date**: 2026-07-01
**Amended**: 2026-07-01

## 1. Socket Listener & Upstream Dialing Strategy

- **Decision**: Use Go's standard `net.Listen("unix", path)` and `net.Listen("tcp", addr)` for interface listening, and custom `http.Transport` with `net.Dialer` for connecting upstream to Unix or TCP Docker daemon endpoints.
- **Rationale**: Standard Go `net` and `net/http` packages natively support both Unix domain sockets and TCP network connections without requiring external CGO or third-party socket libraries. Configuring an `http.Transport` with a custom `DialContext` function allows standard HTTP reverse proxying over Unix domain sockets transparently.
- **Alternatives considered**:
  - Raw TCP/Unix socket forwarding at the transport layer (`io.Copy` bidirectional pipe without HTTP parsing): Rejected because raw transport proxying cannot inspect HTTP request paths, methods, or headers required for ruleset evaluation and structured recording.
  - Third-party proxy frameworks (e.g., Envoy/Traefik bindings): Rejected as overly complex and heavyweight for a standalone, forwardable CLI proxy utility.

---

## 2. HTTP Reverse Proxying & Connection Upgrades (`docker exec` / streaming logs)

- **Decision**: Implement core proxy routing using a customized `httputil.ReverseProxy` supplemented with explicit handling for HTTP connection upgrades (`Connection: Upgrade` / `docker exec` Hijacking) and chunked streaming.
- **Rationale**: `httputil.ReverseProxy` handles standard REST requests, chunked transfer encoding, and response streaming robustly. For hijacked connections (such as interactive `docker exec -it` terminals), custom upgrade interception using `http.Hijacker` allows switching from HTTP proxying to bidirectional raw socket copying (`io.Copy`) after initial ruleset authorization.
- **Alternatives considered**:
  - Writing a from-scratch HTTP/1.1 and HTTP/2 proxy server: Rejected due to high implementation complexity and bug risk around edge-case chunked encoding and keep-alive headers.

---

## 3. Ruleset Evaluation Engine & Matching Grammar

- **Decision**: Use declarative YAML configuration parsing via `gopkg.in/yaml.v3` defining ordered lists of semantic rules (`SemanticRule`). Implement evaluation sequentially against incoming requests with configurable default action (`allow` or `deny`). Within any single rule, all configured criteria must match simultaneously (logical AND) for the rule action (`allow`, `deny`, or `filter`) to apply.
- **Rationale**: YAML is human-readable and standard in Docker/Kubernetes ecosystems. Sequential rule evaluation provides predictable precedence (first match wins) with minimal CPU overhead (<10ms latency goal). Mandating logical AND within a rule allows fine-grained security assertions (e.g. method + operation + privileged condition).
- **Alternatives considered**:
  - Rego / OpenPolicyAgent (OPA) embedded engine: Rejected because embedding OPA adds massive binary bloat and latency overhead unnecessary for straightforward Docker API endpoint control.

---

## 4. Bounded Traffic Recording Architecture

- **Decision**: Implement a middleware interceptor (`Recorder`) that wraps `http.ResponseWriter` and inspects `http.Request.Body` using a bounded buffer (`bytes.Buffer` capped at 64KB per payload via `io.LimitReader`). Write structured transaction records in JSON Lines format (`jsonl`) to a configured output sink (file or stdout).
- **Rationale**: Bounding payload capture at 64KB prevents out-of-memory crashes when large container images or multi-gigabyte log streams pass through the proxy. JSON Lines format allows easy ingestion into jq or SIEM auditing tools.
- **Alternatives considered**:
  - Full unbounded payload recording to disk: Rejected as high risk for disk exhaustion and memory leaks during streaming operations.

---

## 5. Architectural Decoupling (Interface vs. Proxy Core)

- **Decision**: Enforce strict package boundary separation using root-level packages (no `pkg` directory prefix):
  - `cmd/dockerproxy`: Entrypoint CLI parsing flags, signals, and initializing components.
  - `config`: Declarative configuration and ruleset file loading/validation.
  - `listener`: Interface layer managing Unix/TCP socket creation, lifecycle, and graceful shutdown.
  - `proxy`: Core HTTP reverse proxy engine and session management.
  - `rules`: Core semantic policy evaluation engine, struct deserialization, and rule matching algorithms.
  - `recorder`: Core traffic recording and audit sink formatting.
- **Rationale**: This package structure strictly isolates interface components from core business logic. Unit tests are placed directly inside each package directory per idiomatic Go testing standards.

---

## 6. Semantic Docker API Deserialization via Official Moby API Types

- **Decision**: Adopt the canonical published Docker engine API message types from `github.com/moby/moby/api/types/container` (`container.CreateRequest`, `container.ExecCreateRequest`, `container.Summary`) and `github.com/moby/moby/api/types/image` (`image.Summary`) for deserializing operational HTTP request and response payloads.
- **Rationale**: Using official published Moby API types prevents schema drift between the proxy and upstream Docker daemon releases, eliminating maintenance overhead for custom ad-hoc struct definitions while ensuring 100% accurate field tags, nested types (`container.HostConfig`, `mount.Mount`, `nat.PortMap`), and boolean flag inspection.
- **Alternatives considered**:
  - Custom ad-hoc struct definitions: Rejected because maintaining manual duplicates of Docker's complex API types (`HostConfig`, `Mount`, `PortBindings`) risks subtle JSON tag drift or missing fields as new Docker Engine API versions are released.
  - Raw regex matching across JSON text strings: Rejected because regex matching on JSON is prone to false positives/negatives.

---

## 7. Response List Filtering Architecture

- **Decision**: For response filtering rules targeting container lists (`GET /containers/json`) or image lists (`GET /images/json`), create an intercepting `http.ResponseWriter` buffer inside the reverse proxy middleware. When the upstream daemon responds with HTTP 200 OK, unmarshal the JSON response array into a slice of native summary structures (`[]ContainerSummary` or `[]ImageSummary`), evaluate each item against the allowlist criteria (labels, image names, container names), filter out non-matching items, re-marshal the sanitized array to JSON, set the updated `Content-Length`, and write it to the client.
- **Rationale**: Intercepting and filtering response JSON arrays ensures multi-tenant view isolation and prevents clients from discovering unlisted containers or images without breaking standard Docker CLI list commands (`docker ps`, `docker images`).
- **Alternatives considered**:
  - Denying list requests entirely if any non-allowlisted container exists: Rejected because it breaks standard developer workflows (`docker ps` would fail whenever an admin or other process runs a private container).
