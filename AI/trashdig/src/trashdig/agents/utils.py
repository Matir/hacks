import os
import uuid
from typing import List, Dict, Optional, TYPE_CHECKING, Any
from pathspec import PathSpec
from pathspec.patterns import GitWildMatchPattern
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
import google.genai.types as genai_types

if TYPE_CHECKING:
    from trashdig.config import Config, ProviderConfig
    from google.adk.agents import BaseAgent


def google_provider_extras(provider: str) -> dict[str, Any]:
    """Return agent kwargs that are only valid when the provider is Google.

    Google's Gemini API requires ``includeServerSideToolInvocations=True`` in
    the ``ToolConfig`` whenever built-in server-side tools (e.g. google_search)
    are mixed with function-calling tools.  Non-Google backends (e.g. OpenAI
    compatible endpoints) don't support these fields at all, so they must be
    omitted entirely.

    Args:
        provider: The provider string from ``AgentConfig.provider``.

    Returns:
        A dict of extra keyword arguments to pass to the ``LlmAgent``
        constructor, plus a ``"google_search_tool"`` key holding the tool
        object (or ``None``) so callers can include it in their tool list.
    """
    if provider != "google":
        return {"google_search_tool": None, "generate_content_config": None}

    from google.adk.tools import google_search  # local to avoid import cost for non-Google paths

    return {
        "google_search_tool": google_search,
        "generate_content_config": genai_types.GenerateContentConfig(
            tool_config=genai_types.ToolConfig(includeServerSideToolInvocations=True)
        ),
    }


def describe_provider_auth(provider_name: str, provider_config: "ProviderConfig | None") -> List[str]:
    """Return human-readable lines describing how a provider is authenticated.

    No secret values are included — only the *source* of credentials so the
    user can confirm the right identity is being used.

    Args:
        provider_name: The provider name (e.g. "google", "openai").
        provider_config: The ProviderConfig for this provider, or None if absent.

    Returns:
        A list of log-ready strings.
    """
    lines: List[str] = [f"Provider '{provider_name}':"]

    if provider_name == "google":
        # Priority order matches google-auth and ADK resolution:
        # 1. Explicit API key in config.toml
        # 2. GOOGLE_API_KEY environment variable
        # 3. Application Default Credentials (ADC)
        if provider_config and provider_config.api_key:
            lines.append("  auth: API key from config.toml (key redacted)")
        elif os.environ.get("GOOGLE_API_KEY"):
            lines.append("  auth: API key from GOOGLE_API_KEY environment variable")
        else:
            # ADC — detect which flavour is active
            adc_file = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
            if adc_file:
                lines.append(f"  auth: Application Default Credentials (service account file: {adc_file})")
            else:
                # Well-known ADC path set by `gcloud auth application-default login`
                well_known = os.path.join(
                    os.environ.get("APPDATA", os.path.expanduser("~")),
                    ".config", "gcloud", "application_default_credentials.json",
                )
                if os.path.exists(well_known):
                    lines.append(f"  auth: Application Default Credentials (gcloud user credentials at {well_known})")
                elif os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT"):
                    project = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT")
                    lines.append(f"  auth: Application Default Credentials (metadata server / Workload Identity, project={project})")
                else:
                    lines.append("  auth: Application Default Credentials (no explicit source detected; may use metadata server)")
        # Always report which GCP project will be billed, if known
        project = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCLOUD_PROJECT")
        if project:
            lines.append(f"  project: {project}")
    else:
        # Generic OpenAI-compatible or other provider
        if provider_config and provider_config.api_key:
            lines.append("  auth: API key from config.toml (key redacted)")
        else:
            # Common env var conventions: OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.
            env_key = f"{provider_name.upper()}_API_KEY"
            if os.environ.get(env_key):
                lines.append(f"  auth: API key from {env_key} environment variable")
            else:
                lines.append("  auth: no API key found in config or environment")

        base_url = (provider_config.base_url if provider_config else None) or os.environ.get("OPENAI_BASE_URL")
        if base_url:
            lines.append(f"  base_url: {base_url}")

    return lines


def log_auth_info(config: "Config", logger) -> None:
    """Log authentication information for every provider referenced by agents.

    Args:
        config: The loaded TrashDig Config.
        logger: A stdlib logging.Logger to write to.
    """
    # Collect the unique providers actually referenced by configured agents
    referenced: Dict[str, Any] = {}
    for agent_cfg in config.agents.values():
        if agent_cfg.provider not in referenced:
            referenced[agent_cfg.provider] = config.providers.get(agent_cfg.provider)

    # If no agents are explicitly configured, fall back to the global default provider
    if not referenced:
        default_provider = getattr(config, "default_provider", "google")
        referenced[default_provider] = config.providers.get(default_provider)

    for prov_name, prov_cfg in referenced.items():
        for line in describe_provider_auth(prov_name, prov_cfg):
            logger.info(line)


async def run_prompt(
    agent: "BaseAgent",
    prompt: str,
    on_event: Optional[callable] = None,
    on_stats: Optional[callable] = None,
    on_error: Optional[callable] = None,
) -> Dict[str, Any]:
    """Run a single text prompt through an ADK agent and return structured results.

    The ADK Runner requires a session service; we use an in-memory one that is
    discarded after each call so agents remain stateless between invocations.

    Args:
        agent: The ADK LlmAgent to invoke.
        prompt: The user-turn text to send.
        on_event: Optional callable invoked with a formatted string for each
            tool call the agent makes, allowing callers to surface progress.
        on_stats: Optional callable invoked with (input_tokens, output_tokens, new_msg)
            after a successful run, for tracking cumulative LLM usage.
        on_error: Optional callable invoked with no arguments when the API call
            itself raises an exception.

    Returns:
        A dict containing:
            - text: The agent's final text response.
            - input_tokens: Total prompt tokens used.
            - output_tokens: Total completion/tool tokens used.
            - tool_calls: A list of {name, args} dicts for each tool execution.
    """
    from trashdig.rate_limiter import get_rate_limiter
    limiter = get_rate_limiter()

    session_service = InMemorySessionService()
    runner = Runner(
        agent=agent,
        app_name=agent.name,
        session_service=session_service,
    )
    user_id = "trashdig"
    session = await session_service.create_session(
        app_name=agent.name,
        user_id=user_id,
        session_id=str(uuid.uuid4()),
    )
    content = genai_types.Content(role="user", parts=[genai_types.Part(text=prompt)])
    final_text = ""
    input_tokens = 0
    output_tokens = 0
    tool_calls: List[Dict[str, Any]] = []

    if limiter:
        await limiter.wait_for_request()

    try:
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session.id,
            new_message=content,
        ):
            # Extract token usage from usage_metadata if present
            # ADK events may carry usage_metadata directly, inside 'response', or 'raw_response'
            usage = getattr(event, "usage_metadata", None)
            if usage is None:
                usage = getattr(getattr(event, "response", None), "usage_metadata", None)
            if usage is None:
                usage = getattr(getattr(event, "raw_response", None), "usageMetadata", None)

            if usage is not None:
                # Robust extraction with fallbacks for both class attributes and dict keys
                if isinstance(usage, dict):
                    pt = usage.get("prompt_token_count") or usage.get("promptTokenCount") or 0
                    ct = usage.get("candidates_token_count") or usage.get("candidatesTokenCount") or 0
                else:
                    pt = getattr(usage, "prompt_token_count", 0) or getattr(usage, "promptTokenCount", 0) or 0
                    ct = getattr(usage, "candidates_token_count", 0) or getattr(usage, "candidatesTokenCount", 0) or 0

                if pt:
                    input_tokens = max(input_tokens, pt)
                if ct:
                    output_tokens = max(output_tokens, ct)
                
                # Provide intermediate updates for tokens during streaming
                if on_stats:
                    try:
                        on_stats(input_tokens, output_tokens, new_msg=False)
                    except TypeError:
                        on_stats(input_tokens, output_tokens)

            if event.content and event.content.parts:
                for part in event.content.parts:
                    fc = getattr(part, "function_call", None)
                    if fc and getattr(fc, "name", None):
                        args = getattr(fc, "args", {}) or {}
                        tool_calls.append({"name": fc.name, "args": args})
                        if on_event:
                            args_str = ", ".join(
                                f"{k}={repr(v)[:60]}" for k, v in args.items()
                            )
                            on_event(f"  [dim]→ {fc.name}({args_str})[/dim]")

            if event.is_final_response() and event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        final_text = part.text
    except Exception:
        if on_error:
            on_error()
        raise
    
    if limiter:
        await limiter.update_usage(input_tokens + output_tokens)

    if on_stats:
        try:
            on_stats(input_tokens, output_tokens, new_msg=True)
        except TypeError:
            on_stats(input_tokens, output_tokens)

    return {
        "text": final_text,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "tool_calls": tool_calls,
    }

def get_project_structure(root_path: str = ".") -> List[str]:
    """Walks the project directory and returns a list of files, respecting .gitignore.

    Args:
        root_path: The root directory to walk.

    Returns:
        A list of file paths relative to the root, sorted alphabetically.
    """
    files: List[str] = []
    
    # Load .gitignore patterns
    gitignore_path = os.path.join(root_path, ".gitignore")
    spec: Optional[PathSpec] = None
    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r", encoding="utf-8") as f:
            spec = PathSpec.from_lines(GitWildMatchPattern, f.readlines())

    # Noisy directories to always skip
    noisy_dirs = {".git", "node_modules", "dist", "vendor", "__pycache__", ".venv", "findings", "tests"}

    for root, dirs, filenames in os.walk(root_path):
        # Filter directories in-place to avoid walking them
        dirs[:] = [d for d in dirs if d not in noisy_dirs]
        
        for filename in filenames:
            rel_path = os.path.relpath(os.path.join(root, filename), root_path)
            
            # Skip if it matches .gitignore
            if spec and spec.match_file(rel_path):
                continue
                
            files.append(rel_path)
            
    return sorted(files)

def read_file_content(file_path: str, max_chars: int = 2000) -> str:
    """Reads a portion of a file's content for analysis.

    Args:
        file_path: Path to the file.
        max_chars: Maximum number of characters to read. Defaults to 2000.

    Returns:
        The file content (potentially truncated), or an error message.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read(max_chars)
            return content
    except (UnicodeDecodeError, PermissionError, FileNotFoundError):
        return "[Error: Could not read file content]"

def detect_frameworks(file_list: List[str], project_root: str = ".") -> Dict[str, List[str]]:
    """Analyzes dependency files to identify known frameworks and libraries.

    Args:
        file_list: List of project files.
        project_root: Project root directory. Defaults to ".".

    Returns:
        A dictionary mapping categories (e.g., 'web_frameworks', 'databases') to lists 
        of detected technology names.
    """
    stack: Dict[str, List[str]] = {
        "web_frameworks": [],
        "databases": [],
        "auth_libraries": [],
        "other": []
    }
    
    # Key files to check
    dep_files = ["package.json", "requirements.txt", "pyproject.toml", "go.mod", "pom.xml", "Gemfile"]
    
    # Framework signatures
    signatures = {
        "web_frameworks": ["fastapi", "flask", "django", "express", "spring-boot", "rails", "gin", "echo", "nextjs", "react"],
        "databases": ["sqlalchemy", "prisma", "mongoose", "typeorm", "gorm", "postgresql", "mysql", "mongodb", "redis", "sqlite"],
        "auth_libraries": ["passport", "auth0", "next-auth", "firebase-auth", "clerk", "jwt", "oauthlib"]
    }

    for dep_file in dep_files:
        if dep_file in file_list:
            content = read_file_content(os.path.join(project_root, dep_file), max_chars=10000).lower()
            
            for category, names in signatures.items():
                for name in names:
                    if name in content:
                        if name not in stack[category]:
                            stack[category].append(name)
                            
    return stack
