# Data Model: Docker API Proxy & Ruleset Recording

**Feature Branch**: `001-docker-api-proxy`

## Overview

The data model defines the core domain entities used for configuring proxy listeners, evaluating semantic access rules, and recording API transaction logs. All entities operate cleanly within Go domain packages (`rules`, `proxy`, `recorder`).

---

## 1. Ruleset & Semantic Rule Entities (`rules`)

### `Ruleset`
Represents the top-level semantic security policy evaluated against incoming Docker API requests and responses.

| Field | Type | Description | Validation Rules |
| :--- | :--- | :--- | :--- |
| `Version` | `string` | Schema version identifier | Must be `"1.0"` or `"v1"` |
| `DefaultAction` | `Action` (`string`) | Default evaluation action when no explicit rule matches (`allow` or `deny`) | Must be `"allow"` or `"deny"` (defaults to `"allow"`) |
| `Rules` | `[]SemanticRule` | Ordered list of semantic policy evaluation rules | Evaluated sequentially in list order |

### `SemanticRule`
Represents an individual access control or filtering directive within a ruleset. All non-empty criteria fields within a rule must match simultaneously (logical AND) for the rule action to trigger.

| Field | Type | Description | Validation Rules |
| :--- | :--- | :--- | :--- |
| `ID` | `string` | Unique rule identifier or name | Optional, non-empty if provided |
| `Action` | `Action` (`string`) | Enforcement action applied if matched (`allow`, `deny`, or `filter`) | Required; `"allow"`, `"deny"`, or `"filter"` |
| `Message` | `string` | Custom error message returned to client when denied | Optional; defaults to standard denial message |
| `Methods` | `[]string` | HTTP methods matched by this rule (e.g., `["POST", "GET"]`) | Uppercase HTTP methods or `["*"]` for all |
| `PathPattern` | `string` | Regular expression matching request URI path | Valid compiled Go regex pattern |
| `CommandTypes` | `[]string` | Docker command operation categories matched (e.g., `["build", "create", "exec", "list"]`) | Valid Docker command categories |
| `ContainerCreate` | `*ContainerCreateRule` | Semantic constraints evaluated against deserialized `/containers/create` payloads | Evaluated if non-nil and request is container create |
| `ExecCreate` | `*ExecCreateRule` | Semantic constraints evaluated against deserialized `/containers/{id}/exec` payloads | Evaluated if non-nil and request is exec create |
| `ResponseFilter` | `*ResponseFilterRule` | Allowlist constraints evaluated against deserialized container/image list responses | Evaluated if non-nil on list response |

### `ContainerCreateRule`
Defines semantic assertions evaluated against deserialized container creation requests (`container.Config` and `container.HostConfig` from `github.com/moby/moby/api/types/container`).

| Field | Type | Description | Validation Rules |
| :--- | :--- | :--- | :--- |
| `Privileged` | `*bool` | Asserts exact match on `HostConfig.Privileged` (e.g., `true` matches privileged create calls) | Optional boolean pointer |
| `AllowedMounts` | `[]string` | Regex allowlist of permitted mount destination/source paths in `HostConfig.Binds` / `Mounts` | All request mounts must match at least one regex |
| `AllowedPorts` | `[]string` | Allowlist of permitted published port specifications (e.g. `["80/tcp", "443/tcp"]`) | All request ports must exist in allowlist |
| `AllowedImages` | `[]string` | Regex allowlist of permitted image names/tags (`Config.Image`) | Image must match at least one regex |
| `AllowedNames` | `[]string` | Regex allowlist of permitted container names (query parameter `?name=...`) | Container name must match at least one regex |

### `ExecCreateRule`
Defines semantic assertions evaluated against deserialized exec creation requests (`container.ExecCreateRequest` from `github.com/moby/moby/api/types/container`).

| Field | Type | Description | Validation Rules |
| :--- | :--- | :--- | :--- |
| `AllowedCommands` | `[]string` | Regex allowlist of permitted execution command arguments (`Cmd`) | Command line must match at least one regex |
| `AllowedContainers` | `[]string` | Regex allowlist of permitted target container IDs or names | Target container must match at least one regex |

### `ResponseFilterRule`
Defines allowlist criteria applied to filter container lists (`GET /containers/json`) or image lists (`GET /images/json`).

| Field | Type | Description | Validation Rules |
| :--- | :--- | :--- | :--- |
| `AllowedNames` | `[]string` | Regex allowlist of permitted container names or image tags | Item retained only if name/tag matches allowlist |
| `AllowedLabels` | `map[string]string` | Key-value label pairs that an item must possess to be retained | Item retained only if all specified labels match |

---

## 2. Session Entity (`proxy`)

### `ProxySession`
Represents an active connection transaction between a Docker client and upstream daemon.

| Field | Type | Description | Validation Rules |
| :--- | :--- | :--- | :--- |
| `ID` | `string` | Unique UUID or sequence number for the session | Required, unique across running instance |
| `ClientAddr` | `string` | Client remote address (Unix socket path or TCP `ip:port`) | Non-empty |
| `UpstreamAddr` | `string` | Upstream daemon endpoint | Non-empty |
| `StartTime` | `time.Time` | UTC timestamp when request processing began | Required |
| `IsUpgraded` | `bool` | Indicates if connection upgraded to raw stream (e.g. `exec`) | Defaults to `false` |

---

## 3. Recording Entity (`recorder`)

### `TrafficRecord`
Represents a structured audit log entry output in JSON Lines format (`jsonl`) for an intercepted transaction.

| Field | Type | Description | Validation Rules |
| :--- | :--- | :--- | :--- |
| `SessionID` | `string` | Correlation ID from `ProxySession` | Non-empty |
| `Timestamp` | `string` | ISO 8601 UTC timestamp of request completion | Required |
| `Method` | `string` | HTTP request method | Required |
| `URI` | `string` | Full request URI target | Required |
| `ClientHeaders` | `map[string][]string` | HTTP request headers | Sanitized/bounded map |
| `RequestBody` | `string` | Bounded snippet of raw request body (up to 64KB) | Max 65536 bytes |
| `StatusCode` | `int` | HTTP response status code (or `403` if denied by policy) | Valid HTTP status integer |
| `ResponseHeaders` | `map[string][]string` | HTTP response headers | Sanitized/bounded map |
| `ResponseBody` | `string` | Bounded snippet of raw response body (up to 64KB) | Max 65536 bytes |
| `Outcome` | `string` | Policy evaluation outcome (`allowed`, `denied`, or `filtered`) | `"allowed"`, `"denied"`, or `"filtered"` |
| `MatchedRuleID` | `string` | ID of the rule that triggered decision (or `"default"`) | Required |
