# AI Agent Guidelines for telegroups

This project is a Go CLI tool for enumerating Telegram group membership via TDLib and storing results in SQLite.

## Technical Stack

- **Language:** Go 1.24+
- **Telegram Client:** `github.com/zelenin/go-tdlib` (CGO bindings to TDLib)
- **Database:** SQLite via `github.com/mattn/go-sqlite3` (CGO)
- **Interactive TUI:** `github.com/AlecAivazis/survey/v2` (multi-select group picker)
- **TDLib:** vendored under `vendor/tdlib/`; built by `make` via CMake

## Project Structure

- `main.go` — CLI entry point; subcommand dispatch, flag parsing, Telegram auth, top-level orchestration
- `groups.go` — core member enumeration for basic groups and supergroups/channels; member resolution via `GetUser`
- `db.go` — SQLite schema, migrations, and all database read/write operations
- `list.go` — `list` subcommand: display stored groups
- `members.go` — `members` subcommand: dump stored members for a single group
- `intersect.go` — `intersect` subcommand: find users in multiple groups
- `select.go` — chat filtering (by ID or title substring) and interactive TUI selection
- `retry.go` — Telegram flood-wait (429) error detection and retry-after sleep
- `logger.go` — output control via `isQuiet` / `isSilent` globals
- `cgo.go` — CGO flags pointing to `vendor/tdlib/`
- `Makefile` — builds TDLib (CMake) and then the Go binary

## Coding Standards

- Follow idiomatic Go (Effective Go). Use `gofmt` before committing.
- All database mutations must use transactions; mark `members_fetched_at` only after a successful commit.
- Do not update `joined_at` on subsequent fetches — it records the user's first observed join date.
- Errors inside group enumeration should be logged but must not abort processing of other groups.
- Use `logInfo` / `logError` from `logger.go`; never write to stdout/stderr directly.
- Run `go mod tidy` when changing dependencies.

## Build System

`make` performs two steps:
1. Clones TDLib and builds it with CMake into `vendor/tdlib/` (skipped if already present).
2. Compiles the Go binary with CGO flags referencing the vendored library.

Do not commit the `vendor/tdlib/` directory or the compiled binary.

## Key Architectural Notes

### Subcommand Dispatch
Subcommands (`list`, `intersect`) are dispatched manually in `main()` before `flag.Parse()`, so each subcommand owns its own `flag.FlagSet`. New subcommands should follow the same pattern: a `runXxxCmd(args []string)` function called from `main()`.

### Pagination
Supergroup member fetching uses batches of 200 (`membersPerPage` in `groups.go`). Maintain this pattern for any additional paginated API calls to avoid hitting Telegram limits.

### Flood-Wait Handling
All TDLib calls that may be rate-limited must be wrapped with `withFloodWait()` from `retry.go`. Do not add raw `time.Sleep` calls elsewhere for rate limiting.

### Group Resolution (intersect / members)
`resolveGroupID` and `resolveGroupIDs` in `intersect.go` map group references (IDs or title substrings) to exact IDs. When adding new subcommands that accept group arguments, reuse this logic rather than duplicating it.

### intersect Status Filter
`printIntersection` excludes users with `status IN ('left', 'banned')`. Only currently active members are counted toward the intersection threshold. `printMembers` intentionally shows all statuses so callers can see the full picture.

### Supergroup Enumeration Passes
`fetchMembersWithFilter` in `groups.go` paginates a single TDLib filter to completion. `listSupergroup` calls it five times: once with `nil` (recent/default members) and then separately for administrators, bots, restricted, and banned members. Because `upsertMember` uses `ON CONFLICT DO UPDATE`, duplicate hits across passes are safe and simply refresh `last_seen_at`.

### CGO Dependency
Both `go-tdlib` and `go-sqlite3` require CGO. Do not attempt to disable CGO. Cross-compilation requires a matching TDLib build for the target platform.
