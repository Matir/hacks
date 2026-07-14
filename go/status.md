# Go Projects Status Summary

| Project | Status | Summary |
| :--- | :--- | :--- |
| [asmsh](file:///usr/local/google/home/davidtomaschik/Personal/hacks/go/asmsh) | `minimally functional` | Interactive CLI/REPL for assembling and disassembling machine code across CPU architectures via Keystone & Capstone. |
| [badns](file:///usr/local/google/home/davidtomaschik/Personal/hacks/go/badns) | `minimally functional` | Custom DNS server that dynamically resolves subdomains containing hex/hyphenated IP addresses or reflects the requester's IP. |
| [benchmarking](file:///usr/local/google/home/davidtomaschik/Personal/hacks/go/benchmarking) | `finished` | Benchmark suite comparing performance across Go implementations of byte operations, map sets, queues, and sliding windows. |
| [bitflipper](file:///usr/local/google/home/davidtomaschik/Personal/hacks/go/bitflipper) | `minimally functional` | Utility generating single-bit-flipped domain permutations (bitsquatting) and concurrently querying their DNS records. |
| [cyberwaiter](file:///usr/local/google/home/davidtomaschik/Personal/hacks/go/cyberwaiter) | `finished` | HTTP server that automatically fetches, caches, updates, and serves GCHQ CyberChef directly from release ZIP archives. |
| [demoserver](file:///usr/local/google/home/davidtomaschik/Personal/hacks/go/demoserver) | `minimally functional` | Modular HTTP server framework for dynamically registering mock endpoint handlers for security recon testing. |
| [dhcproute](file:///usr/local/google/home/davidtomaschik/Personal/hacks/go/dhcproute) | `finished` | CLI tool to encode IP route specs into RFC 3442 DHCP Option 121 hex payloads and decode hex options back to routes. |
| [flashcap](file:///usr/local/google/home/davidtomaschik/Personal/hacks/go/flashcap) | `finished` | Drive testing utility using direct I/O to overwrite and verify location-derived patterns for true flash drive capacity. |
| [ghtokenbroker](file:///usr/local/google/home/davidtomaschik/Personal/hacks/go/ghtokenbroker) | `finished` | Policy server and CLI (`ghtok`) for minting short-lived, permission-scoped GitHub App installation tokens for agents. |
| [glesspipe](file:///usr/local/google/home/davidtomaschik/Personal/hacks/go/glesspipe) | `finished` | Go implementation of `lesspipe` preprocessor for inspecting and decompressing archives (gzip, bzip2) for `less`. |
| [gopot](file:///usr/local/google/home/davidtomaschik/Personal/hacks/go/gopot) | `finished` | SSH honeypot daemon logging incoming authentication attempts, credentials, and client metadata to SQLite. |
| [gpgcheck](file:///usr/local/google/home/davidtomaschik/Personal/hacks/go/gpgcheck) | `minimally functional` | Multi-threaded utility generating GPG RSA keys and validating the primality of private key factors. |
| [mboxexplore](file:///usr/local/google/home/davidtomaschik/Personal/hacks/go/mboxexplore) | `finished` | Parser for MBOX email archives, storing message metadata in SQLite and extracted attachments in content-addressed storage. |
| [mdtool](file:///usr/local/google/home/davidtomaschik/Personal/hacks/go/mdtool) | `finished` | CLI Markdown viewer and web live-reload server supporting Chroma syntax highlighting and Mermaid diagram rendering. |
| [onwatch](file:///usr/local/google/home/davidtomaschik/Personal/hacks/go/onwatch) | `some work` | Recursive filesystem monitoring library and CLI wrapper built on `fsnotify`. |
| [pathcount](file:///usr/local/google/home/davidtomaschik/Personal/hacks/go/pathcount) | `finished` | Command-line utility that calculates and reports component frequencies across line-delimited file paths. |
| [sorkin](file:///usr/local/google/home/davidtomaschik/Personal/hacks/go/sorkin) | `finished` | Web scraper and analyzer for IMDb cast lists of Aaron Sorkin TV shows to track actor cross-appearances. |
| [spicysizer](file:///usr/local/google/home/davidtomaschik/Personal/hacks/go/spicysizer) | `finished` | X11 RANDR daemon auto-resizing SPICE virtual machine display resolution upon window resize. |
| [sshkeymgr](file:///usr/local/google/home/davidtomaschik/Personal/hacks/go/sshkeymgr) | `some work` | Management tool for SSH `authorized_keys` files with parser libraries completed but CLI subcommands missing. |
| [sshscan](file:///usr/local/google/home/davidtomaschik/Personal/hacks/go/sshscan) | `finished` | Concurrent SSH host key and service banner scanner saving fingerprints and host details into SQLite. |
| [telegroups](file:///usr/local/google/home/davidtomaschik/Personal/hacks/go/telegroups) | `finished` | Telegram group scraper and member analyzer using TDLib and SQLite with membership intersection queries. |
| [tracer](file:///usr/local/google/home/davidtomaschik/Personal/hacks/go/tracer) | `finished` | Linux process syscall tracing utility using `ptrace` and `libseccomp` to log and decode syscall arguments. |
| [txtscan](file:///usr/local/google/home/davidtomaschik/Personal/hacks/go/txtscan) | `finished` | Search tool checking if input files or standard input contain all specified substring patterns. |
| [udptoy](file:///usr/local/google/home/davidtomaschik/Personal/hacks/go/udptoy) | `finished` | Configurable UDP network proxy simulating packet loss, reordering, and artificial delays for network testing. |
| [webtpl](file:///usr/local/google/home/davidtomaschik/Personal/hacks/go/webtpl) | `finished` | Minimal boilerplate starter template for Go web applications with HTML template parsing and static asset routing. |
| [wgvanity](file:///usr/local/google/home/davidtomaschik/Personal/hacks/go/wgvanity) | `finished` | Multi-threaded WireGuard vanity public key search generator for X25519 keypairs matching base64 prefixes. |
| [xbt2dds](file:///usr/local/google/home/davidtomaschik/Personal/hacks/go/xbt2dds) | `finished` | Utility stripping Ubisoft XBT texture container headers to extract embedded DirectDraw Surface (DDS) textures. |

---

## Standalone Repository Promotion Recommendations

The following projects are recommended for promotion from the "hacks" repository to dedicated standalone repositories, categorized by architectural maturity and potential utility.

### Tier 1: Prime Candidates (Production-Grade Codebase Structure)
Projects with multi-package layouts (`cmd/`, `internal/`), test coverage, and documentation (`README.md`, `AGENTS.md`).

1. **[ghtokenbroker](file:///usr/local/google/home/davidtomaschik/Personal/hacks/go/ghtokenbroker)**
   - **Architecture**: Complete client/server model (`ghtok` and `ghtokenbroker`) with modular packages (`policy`, `secrets`, `cache`, `audit`, `config`, `server`) and unit test suites across all packages.
   - **Value**: High-value security infrastructure for minting short-lived, permission-scoped GitHub App installation tokens for automation pipelines and AI agents.

2. **[asmsh](file:///usr/local/google/home/davidtomaschik/Personal/hacks/go/asmsh)**
   - **Architecture**: Modular design (`internal/arch`, `internal/engine`, `internal/repl`, `internal/session`, `internal/formatter`), unit test mocks, build scripts, and CLI integration.
   - **Value**: Multi-architecture interactive assembly and disassembly REPL shell leveraging Keystone and Capstone engines. Useful for reverse engineering and exploit development.

3. **[mdtool](file:///usr/local/google/home/davidtomaschik/Personal/hacks/go/mdtool)**
   - **Architecture**: Cleanly partitioned into `converter`, `server`, and `cmd/mdtool` with tests and embedded static assets (`mermaid.min.js`, `default.css`).
   - **Value**: Full developer utility providing local CLI Markdown rendering as well as a live-reloading HTTP preview server with Chroma syntax highlighting and Mermaid diagram rendering.

### Tier 2: Strong Utilities with Distinct Standalone Value
Finished single-purpose security and systems tools with clear application beyond quick personal scripts.

4. **[gopot](file:///usr/local/google/home/davidtomaschik/Personal/hacks/go/gopot)**
   - SQLite-backed SSH honeypot logging authentication credentials and metrics. Includes custom embedded SQLite C extension components (`sqlite3-inet`) for IPv4 analytics.

5. **[cyberwaiter](file:///usr/local/google/home/davidtomaschik/Personal/hacks/go/cyberwaiter)**
   - Standalone caching web server for GCHQ CyberChef. Automatically downloads, extracts, updates, and serves CyberChef for air-gapped security operations labs.

6. **[tracer](file:///usr/local/google/home/davidtomaschik/Personal/hacks/go/tracer)**
   - Linux process syscall tracing utility using `ptrace` and `libseccomp` with architecture-specific argument stringification (`amd64`/`386`).

### Tier 3: Focused Micro-Tools & Libraries
Finished single-file utilities ideal for micro-repositories or publishing as standalone Go modules:
- **[dhcproute](file:///usr/local/google/home/davidtomaschik/Personal/hacks/go/dhcproute)**: RFC 3442 DHCP Option 121 route payload encoder/decoder CLI and Go library.
- **[spicysizer](file:///usr/local/google/home/davidtomaschik/Personal/hacks/go/spicysizer)**: X11 RANDR daemon for dynamic resolution resizing of SPICE desktop virtual machines.
- **[udptoy](file:///usr/local/google/home/davidtomaschik/Personal/hacks/go/udptoy)**: UDP fault-injection network proxy for testing packet loss, reordering, and artificial delays.

---

## Open Source Tool Re-implementations & Equivalents

The following projects duplicate or closely re-implement established open-source software:

| Project | Well-Known Open Source Equivalent(s) | Function |
| :--- | :--- | :--- |
| [glesspipe](file:///usr/local/google/home/davidtomaschik/Personal/hacks/go/glesspipe) | `lesspipe` / `lesspipe.sh` | Decompresses and formats archives for the `less` pager on the fly. |
| [flashcap](file:///usr/local/google/home/davidtomaschik/Personal/hacks/go/flashcap) | `f3` (Fight Flash Fraud) / `H2testw` | Overwrites drive blocks using direct I/O to test and detect fake-capacity storage devices. |
| [spicysizer](file:///usr/local/google/home/davidtomaschik/Personal/hacks/go/spicysizer) | `spice-vdagent` (resolution module) | Listens for SPICE VM window resize events and adjusts X11 screen dimensions via RANDR. |
| [bitflipper](file:///usr/local/google/home/davidtomaschik/Personal/hacks/go/bitflipper) | `dnstwist` / `urlcrazy` | Generates single-bit-flip domain permutations (bitsquatting) and checks their live DNS resolutions. |
| [mdtool](file:///usr/local/google/home/davidtomaschik/Personal/hacks/go/mdtool) | `grip` / `glow` | Renders Markdown in CLI and provides live-reloading HTTP preview server with Mermaid support. |
| [wgvanity](file:///usr/local/google/home/davidtomaschik/Personal/hacks/go/wgvanity) | `vanity-wg` / `wireguard-vanity-address` | Brute-forces multi-threaded X25519 keypairs matching desired WireGuard base64 public key prefixes. |
| [badns](file:///usr/local/google/home/davidtomaschik/Personal/hacks/go/badns) | `sslip.io` / `nip.io` / `xip.io` / `dnschef` | Wildcard DNS server extracting hex/dash IP addresses from subdomains or reflecting caller IPs. |
| [onwatch](file:///usr/local/google/home/davidtomaschik/Personal/hacks/go/onwatch) | `entr` / `reflex` / `modd` | Recursive directory watcher triggering command execution on file changes via `fsnotify`. |
| [udptoy](file:///usr/local/google/home/davidtomaschik/Personal/hacks/go/udptoy) | `Toxiproxy` / `clumsy` / Linux `tc (netem)` | UDP network proxy introducing artificial latency, packet drops, and out-of-order delivery. |
| [gopot](file:///usr/local/google/home/davidtomaschik/Personal/hacks/go/gopot) | `Cowrie` / `Endlessh` | Low-interaction SSH honeypot logging authentication credentials and banners to SQLite. |
| [tracer](file:///usr/local/google/home/davidtomaschik/Personal/hacks/go/tracer) | `strace` | Traces system calls of Linux processes using `ptrace` and `libseccomp`. |
