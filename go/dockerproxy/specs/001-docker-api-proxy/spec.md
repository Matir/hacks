# Feature Specification: Docker API Proxy with Semantic Ruleset Evaluation & Recording

**Feature Branch**: `001-docker-api-proxy`

**Created**: 2026-07-01
**Amended**: 2026-07-01

**Status**: Draft

**Input**: User description: "I want to replace the rules engine with one that understands docker semantics. With the exception of large streaming bodies, deserialize the body into docker's native data structures. Then we can do semantic matching, i.e., per-operation. Initially, I'd like to be able to do the following: Reject various docker create operations (Privileged containers, Mount points outside an allowlist, Allowlist of ports that can be forwarded, Allowlist of image names and/or labels, Allowlist of container names as regexes); Filter container and image lists returned to client based on allowlist; Filter exec commands (Regex allowlist of commands to be executed, Regex of container names); Allow/deny entire command types (i.e. build). Design it such that it is easy to add new conditions. For each ruleset, all criteria must match for the rule to match."

## Clarifications

### Session 2026-07-01

- Q: When an incoming Docker API request does not match any specific rule defined in the policy ruleset, what should be the default evaluation behavior? → A: Configurable default action (`allow` or `deny`) specified in the ruleset file, defaulting to `allow` if omitted.
- Q: How should the traffic recorder handle request/response body payloads, especially regarding large streaming payloads and sensitive data? → A: Record full raw headers and body snippets bounded by a configurable size limit (e.g., max 64KB per payload), without automatic data redaction.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Transparent Docker API Proxying over Unix and TCP Sockets (Priority: P1)

A user or containerized tool connects to the proxy listening on either a Unix domain socket or a TCP network socket. The proxy connects upstream to a target Docker daemon socket (Unix or TCP) and transparently forwards bidirectional API requests and responses. Standard Docker client commands operate seamlessly through the proxy without modification or traffic corruption.

**Why this priority**: Transparent proxying across socket types is the foundational core mechanism required before inspection, filtering, or recording can take place.

**Independent Test**: Can be fully tested by configuring the proxy to listen on a local socket (Unix or TCP) connected to an upstream Docker daemon socket, running standard client commands (such as listing or inspecting containers) against the proxy endpoint, and verifying that responses match direct daemon communication exactly.

**Acceptance Scenarios**:

1. **Given** the proxy is configured to listen on a Unix socket and forward to a Unix Docker daemon socket, **When** a client issues an API request via the proxy socket, **Then** the request is forwarded to the daemon and the valid response is returned to the client.
2. **Given** the proxy is configured to listen on a TCP socket and forward to a TCP Docker daemon endpoint, **When** a client issues an API request via the TCP proxy endpoint, **Then** the communication completes successfully with full streaming and chunked transfer support.

---

### User Story 2 - Semantic Policy-Based Request Denial and Response Filtering (Priority: P2)

An administrator supplies a semantic ruleset defining access policies based on native Docker operations and structured payload inspection. Instead of simple text regex matching, non-streaming request and response payloads are deserialized into native Docker data structures. Rules evaluate semantic conditions (where all criteria within a rule must match for the rule to apply). When a client sends a prohibited request, the proxy blocks it with an HTTP 403 status. When a client queries container or image lists, response rules transparently filter out non-allowlisted items before returning the list to the client.

**Why this priority**: Semantic awareness prevents obfuscation or bypasses inherent in raw regex matching and allows granular enforcement of container security guards (such as blocking root/privileged mode, unauthorized volume mounts, or unauthorized port forwards) while isolating multi-tenant view access.

**Independent Test**: Can be fully tested by loading a semantic ruleset file containing container creation rules, exec inspection rules, command type restrictions, and list filtering rules, sending a suite of client commands, and verifying 403 denial on prohibited calls and sanitized list outputs on queries.

**Acceptance Scenarios**:

1. **Given** a semantic ruleset denying container creation if privileged mode is requested or mounts fall outside an allowlist regex, **When** a client sends a container create call requesting privileged execution or an unlisted mount, **Then** the proxy deserializes the payload, detects the policy violation, and denies the call with HTTP 403 Forbidden.
2. **Given** a semantic ruleset restricting container and image list responses to items matching specific label or naming criteria, **When** a client queries container or image lists, **Then** the proxy intercepts the daemon response, deserializes the JSON array, removes items outside the allowlist, and returns the filtered array with HTTP 200 OK.
3. **Given** a semantic ruleset restricting exec operations to specific allowed command regexes or container names, **When** a client attempts an exec command violating the criteria, **Then** the call is intercepted and rejected with HTTP 403 Forbidden.
4. **Given** a semantic ruleset denying entire command operation types (such as image build operations), **When** a client submits a request of that command type, **Then** the proxy denies the request immediately before deserializing payloads.

---

### User Story 3 - API Traffic Recording and Inspection (Priority: P3)

An administrator or auditor enables request and response recording. As clients interact with the Docker daemon through the proxy, complete transaction records—including request methods, paths, headers, payload structures, response status codes, timestamps, and semantic rule evaluation outcomes—are recorded in a structured format for auditing, debugging, and ruleset authoring.

**Why this priority**: Recording API exchanges provides critical observability into container operations and enables administrators to analyze real-world traffic when designing fine-grained semantic security policies.

**Independent Test**: Can be fully tested by enabling traffic recording, executing a series of client requests through the proxy, and inspecting the resulting structured record outputs to verify that all request/response details and semantic policy outcomes are captured accurately.

**Acceptance Scenarios**:

1. **Given** traffic recording is enabled, **When** a client sends a request that is permitted and answered by the daemon, **Then** a structured record is produced capturing both the client request details and the upstream response payload.
2. **Given** traffic recording is enabled, **When** a client sends a request that is intercepted and denied or filtered by a semantic ruleset, **Then** a structured record is produced capturing the transaction along with the semantic rule ID that triggered the action.

### Edge Cases

- What happens when non-streaming request or response payloads contain malformed JSON that cannot be deserialized into native Docker structures? The proxy rejects malformed request payloads with HTTP 400 Bad Request if a semantic evaluation rule applies to that operation type, preventing malformed payload bypasses.
- How does the system handle large streaming bodies (e.g., image push/pull streams, container attach streams, or build contexts)? Large streaming bodies bypass full payload deserialization; rules targeting those operations evaluate operation-level metadata (command type, URI parameters, and headers) without buffering the live stream.
- What happens when a rule defines multiple conflicting criteria? All criteria defined inside a single rule must match simultaneously (logical AND) for the rule to trigger its enforcement action (`allow`, `deny`, or `filter`).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST listen for incoming client connections on configurable Unix domain sockets and TCP network endpoints.
- **FR-002**: System MUST establish outbound connections to upstream Docker daemon instances via configurable Unix domain sockets or TCP network endpoints.
- **FR-003**: System MUST transparently relay bidirectional HTTP/REST API exchanges, including long-lived streaming responses and upgraded connection channels, between clients and the daemon.
- **FR-004**: System MUST evaluate incoming API requests and responses against a configurable semantic policy ruleset. Rulesets MUST support a configurable default action (`allow` or `deny`) applied when no specific rules match, defaulting to `allow` if unspecified.
- **FR-005**: System MUST deserialize non-streaming HTTP request and response operational payloads directly into official canonical Docker message types published in the upstream package (`github.com/moby/moby/api/types`) to ensure accurate semantic interpretation and long-term protocol compatibility.
- **FR-006**: System MUST support semantic request evaluation rules targeting:
  - Container creation operations: evaluating privileged execution flags, mount destination/source allowlists (regex-based), port forwarding allowlists, image name/label allowlists, and container name regex allowlists.
  - Exec creation operations: evaluating command argument allowlists (regex-based) and target container name/ID regexes.
  - Operation type rules: permitting or denying entire Docker API command categories (e.g., `build`, `create`, `exec`).
- **FR-007**: System MUST support semantic response filtering rules that intercept container list and image list responses from the daemon, deserialize the item arrays, and omit items failing configured allowlist criteria before returning the response to the client.
- **FR-008**: System MUST require that all criteria defined within a single rule match simultaneously (logical AND) for that rule's action (`allow`, `deny`, or `filter`) to apply.
- **FR-009**: System MUST enforce an extensible architectural design where semantic criteria evaluators are decoupled and standardized, allowing straightforward addition of new inspection criteria.
- **FR-010**: System MUST deny requests violating policy rules by returning HTTP 403 Forbidden with a descriptive explanation.
- **FR-011**: System MUST record structured transaction logs capturing headers, bounded body snippets, status codes, and semantic evaluation outcomes when recording mode is enabled.
- **FR-012**: System MUST enforce strict architectural boundary decoupling between interface/presentation layers (`cmd/dockerproxy`, `config`, `listener`) and core proxy/evaluation layers (`proxy`, `rules`, `recorder`). The application entrypoint (`main.go`) MUST reside inside `cmd/dockerproxy` as the main package. Internal packages MUST NOT use `pkg` as a directory prefix, and unit tests MUST be placed within the same package directory as the code under test.

### Key Entities *(include if feature involves data)*

- **ProxySession**: Represents an active transaction exchange between a client and the target daemon, maintaining state, protocol upgrade status, and timing metadata.
- **SemanticRule**: Represents a structured access control directive evaluating native Docker operation attributes (command type, container create constraints, exec constraints, or list filter criteria) and enforcing an action (`allow`, `deny`, or `filter`). All non-empty criteria fields within a rule must match for the rule to apply.
- **Ruleset**: A structured collection of semantic rules evaluated sequentially against requests and responses, including a configurable default action (`allow` or `deny`).
- **TrafficRecord**: A structured audit record capturing transaction timestamps, headers, bounded payload snippets, and semantic evaluation outcomes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of standard client API commands execute successfully through the proxy when no denial or filter rules match.
- **SC-002**: Semantic deserialization and policy evaluation introduce less than 10 milliseconds of latency overhead per non-streaming request under standard operational load.
- **SC-003**: 100% of requests matching configured semantic denial criteria (such as privileged container creation or unauthorized mounts) are intercepted and blocked before reaching the Docker daemon socket.
- **SC-004**: 100% of container and image list queries matching filter rules return sanitized item lists containing only allowlisted entries.
- **SC-005**: The system sustains concurrent client sessions and streaming connections without memory leaks, socket exhaustion, or dropped connections.

## Assumptions

- Target environments provide access to standard network socket creation for Unix domain and TCP sockets.
- Policy rulesets are provided via declarative configuration files at initialization time.
- Large streaming bodies (e.g. tarballs during `docker build` or image pulls) do not undergo full payload JSON deserialization.
