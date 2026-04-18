import logging
import os
from typing import TYPE_CHECKING, Any, Optional

import google.genai.types as genai_types
from google.adk.runners import Runner
from google.adk.tools import google_search
from pathspec import PathSpec

from trashdig.config import get_config

# The following imports are for type hinting only and avoid circular dependencies.
if TYPE_CHECKING:
    from google.adk.agents import BaseAgent
    from google.adk.artifacts import BaseArtifactService
    from google.adk.sessions import BaseSessionService

    from trashdig.config import Config, ProviderConfig


def google_provider_extras(provider: str) -> dict[str, Any]:
    """Return agent kwargs that are only valid when the provider is Google."""
    if provider != "google":
        return {"google_search_tool": None, "generate_content_config": None}

    return {
        "google_search_tool": google_search,
        "generate_content_config": genai_types.GenerateContentConfig(
            tool_config=genai_types.ToolConfig(include_server_side_tool_invocations=True)
        ),
    }


def _describe_google_auth(provider_config: "ProviderConfig | None") -> list[str]:
    """Return lines describing Google provider authentication."""
    lines: list[str] = []
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
    return lines


def _describe_generic_auth(provider_name: str, provider_config: "ProviderConfig | None") -> list[str]:
    """Return lines describing generic provider authentication."""
    lines: list[str] = []
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


def describe_provider_auth(provider_name: str, provider_config: "ProviderConfig | None") -> list[str]:
    """Return human-readable lines describing how a provider is authenticated."""
    lines: list[str] = [f"Provider '{provider_name}':"]

    if provider_name == "google":
        lines.extend(_describe_google_auth(provider_config))
    else:
        lines.extend(_describe_generic_auth(provider_name, provider_config))

    return lines


def log_auth_info(config: "Config", logger: logging.Logger) -> None:
    """Log authentication information for every provider referenced by agents."""
    referenced: dict[str, "ProviderConfig"] = {}
    for agent_cfg in config.agents.values():
        if agent_cfg.provider not in referenced:
            referenced[agent_cfg.provider] = config.get_provider_config(agent_cfg.provider)

    if not referenced:
        default_provider = config.default_provider
        referenced[default_provider] = config.get_provider_config(default_provider)

    for prov_name, prov_cfg in referenced.items():
        for line in describe_provider_auth(prov_name, prov_cfg):
            logger.info(line)


def load_prompt(file_name: str) -> str:
    """Loads a prompt from a markdown file in the prompts directory.

    Args:
        file_name: Name of the prompt file (e.g., 'stack_scout.md').

    Returns:
        The content of the prompt file.
    """
    # Prompts are located in the 'prompts' directory at the project root.
    # We find it relative to this file: src/trashdig/agents/utils/helpers.py -> project_root/prompts
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
    prompt_path = os.path.join(base_dir, "prompts", file_name)

    if not os.path.exists(prompt_path):
        # Fallback for full paths or if the prompts directory isn't where we expect
        if os.path.exists(file_name):
            prompt_path = file_name
        else:
            raise FileNotFoundError(f"Prompt file not found: {file_name} (checked {prompt_path})")

    with open(prompt_path, encoding="utf-8") as f:
        return f.read()


def get_project_structure(root_path: str | None = None) -> list[str]:
    """Walks the project directory and returns a list of files.

    Args:
        root_path: The directory to walk. Defaults to Config workspace_root.
    """
    if root_path is None:
        root_path = get_config().workspace_root

    files: list[str] = []
    gitignore_path = os.path.join(root_path, ".gitignore")
    spec: PathSpec | None = None
    if os.path.exists(gitignore_path):
        with open(gitignore_path, encoding="utf-8") as f:
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
        with open(file_path, encoding="utf-8") as f:
            content = f.read(max_chars)
            return content
    except (UnicodeDecodeError, PermissionError, FileNotFoundError):
        return "[Error: Could not read file content]"

def detect_frameworks(file_list: list[str], project_root: str | None = None) -> dict[str, list[str]]:
    """Analyzes dependency files to identify known frameworks and libraries."""
    if project_root is None:
        project_root = get_config().workspace_root

    stack: dict[str, list[str]] = {
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
                    if name in content and name not in stack[category]:
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

async def run_agent(  # noqa: PLR0913
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
    runner = Runner(
        agent=agent,
        app_name=agent.name,
        session_service=session_service,
        artifact_service=artifact_service,
        auto_create_session=True,
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
