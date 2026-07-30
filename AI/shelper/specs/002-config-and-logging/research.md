# Research Notes: Configuration Merging & Observability Logging

## Precedence Resolution Strategy

When combining multiple configuration sources (CLI flags, TOML file, Environment variables, Defaults), we must prevent flag defaults from overriding explicit TOML settings.

### Dynamic Flag Defaults
- First, resolve defaults, environment variables, and TOML values into a temporary configuration struct.
- Register CLI flags using the fields of this temporary struct as their default values.
- Parse the CLI flags.

## Logging Strategy & Disabling Output

The user specified: "If no logfile is specified, do not print any log output at all."

### Discarding Logs
- Instead of defaulting log output to `os.Stdout`, we will default the logger output stream to `io.Discard` when `cfg.LogFile == ""`.
- This ensures all calls to `logger.Info`/`logger.Warning`/`logger.Error` are safely ignored without modifying the log execution paths.

### Fatal Startup Errors
- If no credentials (keys) are present, the provider registry will contain 0 providers.
- In this state, the daemon cannot function. We will write a clear message to `os.Stderr` (even if logs are disabled, as this is a fatal startup failure for a CLI command) and exit with code 1 immediately.
