# Research Notes: Configuration Merging & Observability Logging

## Precedence Resolution Strategy

When combining multiple configuration sources (CLI flags, TOML file, Environment variables, Defaults), we must prevent flag defaults from overriding explicit TOML settings.

### Alternatives Considered

1. **Explicit Visitation Check (`flag.Visit`)**:
   - Parse flags with empty/zero defaults.
   - Load TOML, then load env, then load flags.
   - For each flag, check if it was visited. If so, override the TOML value.
   - *Drawback*: Requires maintaining a list of visited flags and manual reassignment, which can be verbose.

2. **Dynamic Flag Defaults (Selected)**:
   - First, resolve defaults, environment variables, and TOML values into a temporary configuration struct.
   - Register CLI flags using the fields of this temporary struct as their default values!
   - Parse the CLI flags.
   - *Benefit*: Extremely clean. If the user does not pass a flag, it defaults to the value resolved from TOQL/env. If the user passes a flag, it overrides the TOML value.

### TOML Parsing

We will use `github.com/BurntSushi/toml`.
Example usage:
```go
type TomlConfig struct {
    LLMProvider  *string `toml:"llm_provider"`
    LLMModel     *string `toml:"llm_model"`
    GeminiAPIKey *string `toml:"gemini_api_key"`
    OpenAIAPIKey *string `toml:"openai_api_key"`
    LogFile      *string `toml:"logfile"`
    LogLevel     *string `toml:"loglevel"`
}
```
Using pointer fields in TOML struct allows distinguishing between an empty value (absent) and an explicitly set empty string.

## Logging Strategy

The constitution requires low latency and actionable errors.

### Logging System Design
- We will implement a custom `Logger` in a new `log` package.
- It will support levels: `info` (0), `warning` (1), `error` (2).
- If `logfile` is specified, we will initialize an `os.OpenFile` and set the logger output to it. Otherwise, default to `os.Stdout`/`os.Stderr`.
- To avoid blocking socket operations, log writing will be done directly to the file stream. Since local disk writes are fast, standard buffered or synchronized writers will be sufficient under 1ms.
- To prevent API key leaks, the log engine must actively strip or mask strings that match the configured Gemini/OpenAI API keys when formatting prompt telemetry.
