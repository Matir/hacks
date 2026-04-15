import os
from typing import Optional
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool, load_artifacts as load_artifacts_tool
from trashdig.config import AgentConfig
from trashdig.agents.utils import (
    google_provider_extras,
)
from trashdig.services.permissions import PermissionManager
from trashdig.tools import (
    ripgrep_search,
    get_ast_summary,
    query_cwe_database,
    find_references,
    get_scope_info,
    web_fetch,
    get_project_structure,
    detect_frameworks,
)


def load_prompt(file_name: str) -> str:
    """Loads a prompt from a markdown file in the prompts directory.

    Args:
        file_name: Name of the prompt file (e.g., 'stack_scout.md').

    Returns:
        The content of the prompt file.
    """
    prompt_path = os.path.join(os.getcwd(), "prompts", file_name)
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


class StackScoutAgent(LlmAgent):
    """StackScout Agent for TrashDig.

    Identifies the tech stack using deterministic checks and LLM inference, 
    and generates a project mapping with high-value targets.
    """
    pass


class WebRouteMapperAgent(LlmAgent):
    """WebRouteMapper Agent for TrashDig.

    Maps reachable endpoints and their handlers to build an attack surface map.
    """
    pass


def create_stack_scout_agent(
    config: Optional[AgentConfig] = None,
    permission_manager: Optional[PermissionManager] = None,
) -> StackScoutAgent:
    if config is None:
        config = AgentConfig()

    instruction = load_prompt("stack_scout.md")
    extras = google_provider_extras(config.provider)
    tools = [
        FunctionTool(ripgrep_search),
        FunctionTool(get_ast_summary),
        FunctionTool(query_cwe_database),
        FunctionTool(find_references),
        FunctionTool(get_scope_info),
        FunctionTool(web_fetch),
        FunctionTool(get_project_structure),
        FunctionTool(detect_frameworks),
        load_artifacts_tool,
    ]
    if extras["google_search_tool"]:
        tools.append(extras["google_search_tool"])

    if permission_manager:
        tools = permission_manager.wrap_tools(tools)

    kwargs = {"generate_content_config": extras["generate_content_config"]} if extras["generate_content_config"] else {}

    return StackScoutAgent(
        name="stack_scout",
        model=config.model,
        instruction=instruction,
        description="Identifies the technology stack and maps the project structure.",
        tools=tools,
        **kwargs,
    )


def create_web_route_mapper_agent(
    config: Optional[AgentConfig] = None,
    permission_manager: Optional[PermissionManager] = None,
) -> WebRouteMapperAgent:
    if config is None:
        config = AgentConfig()

    instruction = load_prompt("web_route_mapper.md")
    extras = google_provider_extras(config.provider)
    tools = [
        FunctionTool(ripgrep_search),
        FunctionTool(get_ast_summary),
        FunctionTool(get_project_structure),
        load_artifacts_tool,
    ]

    if permission_manager:
        tools = permission_manager.wrap_tools(tools)

    kwargs = {"generate_content_config": extras["generate_content_config"]} if extras["generate_content_config"] else {}

    return WebRouteMapperAgent(
        name="web_route_mapper",
        model=config.model,
        instruction=instruction,
        description="Maps reachable web endpoints and their handlers.",
        tools=tools,
        **kwargs,
    )
