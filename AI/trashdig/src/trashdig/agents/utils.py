import os
from typing import List, Dict, Optional, TYPE_CHECKING, Any
from pathspec import PathSpec
import google.genai.types as genai_types

if TYPE_CHECKING:
    from trashdig.config import Config, ProviderConfig
    from google.adk.agents import BaseAgent
    from google.adk.sessions import BaseSessionService
    from google.adk.artifacts import BaseArtifactService


def google_provider_extras(provider: str) -> dict[str, Any]:
    """Return agent kwargs that are only valid when the provider is Google."""
    if provider != "google":
        return {"google_search_tool": None, "generate_content_config": None}

    from google.adk.tools import google_search

    return {
        "google_search_tool": google_search,
        "generate_content_config": genai_types.GenerateContentConfig(
            tool_config=genai_types.ToolConfig(includeServerSideToolInvocations=True)
        ),
    }


def describe_provider_auth(provider_name: str, provider_config: "ProviderConfig | None") -> List[str]:
    """Return human-readable lines describing how a provider is authenticated."""
    lines: List[str] = [f"Provider '{provider_name}':"]

    if provider_name == "google":
        if provider_config and provider_config.api_key:
            lines.append("  auth: API key from config.toml (key redacted)")
        elif os.environ.get("GOOGLE_API_KEY"):
            lines.append("  auth: API key from GOOGLE_API_KEY environment variable")
        else:
            adc_file = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
            if adc_file:
                lines.append(f"  auth: Application Default Credentials (service account file: {adc_file})")
            else:
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
        project = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCLOUD_PROJECT")
        if project:
            lines.append(f"  project: {project}")
    else:
        if provider_config and provider_config.api_key:
            lines.append("  auth: API key from config.toml (key redacted)")
        else:
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
    """Log authentication information for every provider referenced by agents."""
    referenced: Dict[str, Any] = {}
    for agent_cfg in config.agents.values():
        if agent_cfg.provider not in referenced:
            referenced[agent_cfg.provider] = config.providers.get(agent_cfg.provider)

    if not referenced:
        default_provider = getattr(config, "default_provider", "google")
        referenced[default_provider] = config.providers.get(default_provider)

    for prov_name, prov_cfg in referenced.items():
        for line in describe_provider_auth(prov_name, prov_cfg):
            logger.info(line)


def get_project_structure(root_path: str = ".") -> List[str]:
    """Walks the project directory and returns a list of files."""
    files: List[str] = []
    gitignore_path = os.path.join(root_path, ".gitignore")
    spec: Optional[PathSpec] = None
    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r", encoding="utf-8") as f:
            spec = PathSpec.from_lines("gitignore", f.readlines())

    noisy_dirs = {".git", "node_modules", "dist", "vendor", "__pycache__", ".venv", "findings", "tests"}

    for root, dirs, filenames in os.walk(root_path):
        dirs[:] = [d for d in dirs if d not in noisy_dirs]
        for filename in filenames:
            rel_path = os.path.relpath(os.path.join(root, filename), root_path)
            if spec and spec.match_file(rel_path):
                continue
            files.append(rel_path)
    return sorted(files)

def read_file_content(file_path: str, max_chars: int = 2000) -> str:
    """Reads a portion of a file's content for analysis."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read(max_chars)
            return content
    except (UnicodeDecodeError, PermissionError, FileNotFoundError):
        return "[Error: Could not read file content]"

def detect_frameworks(file_list: List[str], project_root: str = ".") -> Dict[str, List[str]]:
    """Analyzes dependency files to identify known frameworks and libraries."""
    stack: Dict[str, List[str]] = {
        "web_frameworks": [],
        "databases": [],
        "auth_libraries": [],
        "other": []
    }
    dep_files = ["package.json", "requirements.txt", "pyproject.toml", "go.mod", "pom.xml", "Gemfile"]
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

def get_response_text(resp: Any) -> str:
    """Extracts all text parts from an ADK LlmResponse or Event."""
    text = ""
    if hasattr(resp, "content") and resp.content and resp.content.parts:
        for part in resp.content.parts:
            if hasattr(part, "text") and part.text:
                text += part.text
    return text

async def run_agent(
    agent: "BaseAgent",
    prompt: str,
    session_id: str,
    session_service: "BaseSessionService",
    artifact_service: Optional["BaseArtifactService"] = None,
    user_id: str = "default_user",
) -> str:
    """Helper to run an agent synchronously-like and return the final text response.

    Args:
        agent: The ADK agent instance.
        prompt: The user prompt.
        session_id: The session ID.
        session_service: The ADK SessionService.
        artifact_service: The ADK ArtifactService.
        user_id: The user ID.

    Returns:
        The final text response from the agent.
    """
    from google.adk.runners import Runner
    import google.genai.types as genai_types

    runner = Runner(
        agent=agent,
        app_name=agent.name,
        session_service=session_service,
        artifact_service=artifact_service,
    )

    content = genai_types.Content(role="user", parts=[genai_types.Part(text=prompt)])
    
    final_text = ""
    async for event in runner.run_async(
        new_message=content,
        session_id=session_id,
        user_id=user_id,
    ):
        final_text += get_response_text(event)
    
    return final_text
