# telegroups

A CLI tool for enumerating and analyzing Telegram group, supergroup, and channel membership. It connects to Telegram via TDLib, fetches member lists from groups you belong to, stores them in a SQLite database, and lets you query membership patterns across multiple groups.

## Prerequisites

- Telegram API credentials: register an application at https://my.telegram.org to obtain an API ID and hash.
- TDLib shared library (built automatically by `make`).
- CGO-capable Go toolchain and CMake (for building TDLib).

## Build

```bash
make
```

This clones and builds TDLib into `vendor/tdlib/`, then compiles the binary.

## Configuration

Set the following environment variables before running:

```bash
export TELEGRAM_API_ID=<your api id>
export TELEGRAM_API_HASH=<your api hash>
```

TDLib session state is stored under `.tdlib/` in the working directory. On first run you will be prompted interactively to authenticate (phone number, auth code, 2FA password if applicable).

## Usage

### Fetch members

```
telegroups [flags] [group-filter ...]
```

Authenticates with Telegram, loads all groups you are a member of, and fetches/stores their member lists.

**Flags:**

| Flag | Default | Description |
|------|---------|-------------|
| `-db <path>` | `telegroups.db` | Path to the SQLite database |
| `-since <duration>` | `0` | Skip groups fetched within this duration (e.g. `24h`) |
| `-select-groups` | false | Interactively pick groups via a TUI multi-select |
| `-quiet` | false | Suppress info messages; errors still shown |
| `-silent` | false | Suppress all output except fatal errors |

**Group filters** (positional arguments): filter by exact numeric group ID or case-insensitive title substring. Multiple filters are OR'd.

Examples:

```bash
# Fetch all groups
telegroups

# Fetch only groups matching "security" in the title, skip those fetched in last 24h
telegroups -since 24h security

# Interactively pick which groups to fetch
telegroups -select-groups
```

### List stored groups

```
telegroups list [-db <path>]
```

Displays all groups in the database with their ID, title, type, reported member count, and when members were last fetched.

### List members of a group

```
telegroups members [-db <path>] <group>
```

Dumps all stored members for a single group from the database (no Telegram connection needed). Groups are identified by numeric ID or unique title substring. Outputs user ID, name, username, and membership status.

```bash
telegroups members "security research"
```

### Find members in multiple groups

```
telegroups intersect [-db <path>] <group> <group> [group ...]
```

Finds users who are **currently active** members of **all** specified groups (excludes users with `left` or `banned` status). Groups are identified by numeric ID or unique title substring. Outputs user ID, name, and username.

```bash
telegroups intersect "security research" "ctf players"
```

## Database Schema

The SQLite database (`telegroups.db` by default) contains three tables:

- **groups** — id, title, type (`basic_group` / `supergroup` / `channel`), reported member count, `members_fetched_at`
- **users** — id, first/last name, username, `is_bot`
- **members** — group\_id, user\_id, status (`owner` / `admin` / `member` / `restricted` / `left` / `banned`), `joined_at`, `last_seen_at`

## Notes

- Telegram rate-limits member enumeration. `telegroups` handles flood-wait (429) errors automatically by sleeping for the server-specified duration.
- Anonymous channel members (posts forwarded without a user identity) are silently skipped.
- Restricted supergroups may not expose their full member list; a warning is printed when enumeration is incomplete.
- `joined_at` is recorded on first fetch and not overwritten on subsequent fetches.
