import os
from typing import List, Dict, Optional, TYPE_CHECKING, Any
from pathspec import PathSpec
import google.genai.types as genai_types

if TYPE_CHECKING:
    from trashdig.config import Config, ProviderConfig


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
            spec = PathSpec.from_lines("gitignore", f.readlines())

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
