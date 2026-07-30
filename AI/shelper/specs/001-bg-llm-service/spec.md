# Feature Specification: Background LLM Processing Service

**Feature Branch**: `001-bg-llm-service`

**Created**: 2026-07-30

**Status**: Draft

**Input**: User description: "Build an application that runs in the background and accepts requests. When a request comes in, it should format a prompt, send the prompt to an LLM, then return the response. We also need a shell function that will take a line from the shell and send it to the socket, along with the name of the current shell. The function should then read the response from that and insert it into the shell's line editor as a potential command to be executed."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Process Background Request with Prompt Formatting (Priority: P1)

As a client application or service, I want to submit raw request data to a background daemon so that it formats the input into a structured prompt, interacts with the LLM service, and returns the response asynchronously or synchronously without delaying client initialization.

**Why this priority**: Core value of the service. Without background request acceptance, prompt formatting, and LLM communication, the application has no MVP utility.

**Independent Test**: Can be fully tested by starting the background service, sending a sample payload via client request, and verifying that formatted prompt generation occurs, LLM call succeeds, and structured response is returned.

**Acceptance Scenarios**:

1. **Given** the background daemon is running and idle, **When** a valid request with template parameters and input variables is submitted, **Then** the daemon formats the prompt, transmits it to the LLM backend, and returns the completed text response to the client within the defined SLA.
2. **Given** a request specifying a customized prompt template, **When** the daemon processes the request, **Then** the input variables are substituted accurately into the template before invoking the LLM.

---

### User Story 2 - Interactive Shell Line Editor Integration (Priority: P2)

As an interactive terminal user, I want to trigger a key binding in my shell (Bash/Zsh) that captures my current command buffer line, sends it alongside my shell environment identifier (`bash`/`zsh`) to the `shelperd` daemon via Unix socket, and replaces my buffer line with the AI-suggested command so I can inspect and execute it directly.

**Why this priority**: High-value interactive capability enabling seamless terminal assistant workflows directly within shell command prompts.

**Independent Test**: Can be tested by invoking the shell widget function in an interactive shell session with a prompt string in the line buffer, verifying that the socket receives the request containing shell metadata, and confirming the line buffer is updated with the returned command string.

**Acceptance Scenarios**:

1. **Given** a user types a natural language prompt in the shell line buffer and presses the configured key shortcut, **When** the shell widget executes, **Then** the current buffer line and shell identifier (`bash` or `zsh`) are transmitted over the Unix domain socket.
2. **Given** the daemon returns a generated command string, **When** the shell widget receives the successful response, **Then** the shell line buffer is updated with the returned command text and cursor position is moved to the end of the line.

---

### User Story 3 - Health and Status Monitoring of Background Daemon (Priority: P2)

As a system administrator or operating environment, I want to query the status and health of the background service so that I can ensure it is active, responsive, and processing requests properly.

**Why this priority**: Crucial for background applications to support operation, observability, and lifecycle management.

**Independent Test**: Can be tested independently by issuing a health status check to the background process and asserting active status, request count metrics, and operational readiness.

**Acceptance Scenarios**:

1. **Given** the background service is running, **When** a status request is issued, **Then** the service returns operational status, active worker thread counts, and uptime metadata.
2. **Given** the service is undergoing graceful shutdown, **When** a new request arrives, **Then** the service rejects new requests with a designated maintenance status while completing active requests.

---

### User Story 4 - Error Handling & Resilient Recovery (Priority: P3)

As a client application, I want to receive clear, structured error responses when LLM backends fail or requests are malformed, so that client applications can handle failures gracefully without crashing.

**Why this priority**: Important for robust production operation and client error resilience.

**Independent Test**: Can be tested by sending malformed payloads or simulating LLM API timeouts/failures, asserting that structured actionable error responses are returned.

**Acceptance Scenarios**:

1. **Given** an upstream LLM API timeout or error, **When** the daemon attempts to process a request, **Then** the daemon retries according to configured policy and returns a structured diagnostic error response if retries are exhausted.
2. **Given** a request payload missing mandatory fields, **When** submitted to the daemon, **Then** the daemon immediately returns a clear validation error without invoking the LLM backend.

---

### Edge Cases

- What happens when an incoming request exceeds maximum payload size or token limits?
- How does the shell function handle line editor buffer updates if the background daemon is not running or the socket connection fails?
- How does the prompt template handle differences between Bash and Zsh syntax when generating shell commands?
- What occurs if the daemon process receives a termination signal (`SIGTERM`/`SIGINT`) while requests are mid-invalidation or mid-LLM generation?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST run as a background daemon process that continuously listens for incoming client processing requests over Unix Domain Socket.
- **FR-002**: System MUST accept client requests containing prompt template identifiers, input variables, shell name metadata, and processing configuration.
- **FR-003**: System MUST format the final prompt by combining system instructions, selected template patterns, shell context, and submitted input parameters.
- **FR-004**: System MUST communicate with the target LLM provider interface, transmitting the formatted prompt payload.
- **FR-005**: System MUST parse the LLM provider response payload and return the resulting text output and metadata back to the requesting client.
- **FR-006**: System MUST enforce request payload validation prior to prompt construction and LLM dispatch.
- **FR-007**: System MUST log request processing events, execution latencies, and error conditions in a structured format without logging sensitive credentials.
- **FR-008**: System MUST provide shell integration scripts (`shell/shelper.bash` and `shell/shelper.zsh`) containing widget functions for shell line editor integration.
- **FR-009**: The shell widget function MUST capture the current editor buffer (`READLINE_LINE` for Bash, `$BUFFER` for Zsh), identify the current shell name, send an NDJSON request to the resolved Unix socket, and replace the editor buffer with the generated command string upon success.

### Key Entities

- **ClientRequest**: Represents an incoming request payload, containing request ID, target template ID, variable key-value map (including shell name `bash`/`zsh`), and input text.
- **PromptTemplate**: Defines the structural prompt format with placeholder tags, system instruction boundaries, and shell context parameters.
- **LLMResponsePayload**: Represents the structured result returned to the client, including output text, token consumption metrics, execution status, and error details if applicable.
- **ShellWidget**: Shell integration function bound to line editor shortcuts (Bash readline / Zsh ZLE) managing socket payload transmission and buffer manipulation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Background process accepts and acknowledges incoming requests within 50ms of connection receipt.
- **SC-002**: Prompt formatting and payload validation complete within 10ms prior to LLM network dispatch.
- **SC-003**: Service handles up to 50 concurrent request processing workers without memory leaks or process crashes.
- **SC-004**: 99% of valid client requests receive structured success or diagnostic error responses without connection drops or hanging background processes.
- **SC-005**: Shell widget function completes line buffer capture, socket roundtrip, and buffer insertion in under 1 second (excluding LLM network generation time).

## Assumptions

- Background application communicates with clients via standard IPC mechanism or local API port.
- LLM API authentication tokens and provider endpoints are supplied through secure background environment configuration.
- Default prompt templates are loaded at process start and can be dynamically selected via request parameters.
- Shell integration scripts target standard Bash (4.0+) with `bind -x` / readline and Zsh with ZLE (`zle -N`).
