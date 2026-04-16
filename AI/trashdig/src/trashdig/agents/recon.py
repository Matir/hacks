from typing import Any

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from google.adk.tools import load_artifacts as load_artifacts_tool

from trashdig.agents.utils import (
    google_provider_extras,
    load_prompt,
)
from trashdig.config import AgentConfig
from trashdig.services.permissions import PermissionManager
from trashdig.tools import (
    detect_frameworks,
    find_references,
    get_ast_summary,
    get_project_structure,
    get_scope_info,
    query_cwe_database,
    ripgrep_search,
    web_fetch,
)


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
    config: AgentConfig | None = None,
    permission_manager: PermissionManager | None = None,
) -> LlmAgent:
    """Creates a StackScout agent for environment and tech stack detection.

    Args:
        config: Agent configuration.
        permission_manager: Permission manager for tools.

    Returns:
        A configured LlmAgent instance.
    """
    if config is None:
        config = AgentConfig()

    instruction = load_prompt("stack_scout.md")
    extras = google_provider_extras(config.provider)
    tools: list[Any] = [
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
    config: AgentConfig | None = None,
    permission_manager: PermissionManager | None = None,
) -> LlmAgent:
    """Creates a WebRouteMapper agent for attack surface discovery.

    Args:
        config: Agent configuration.
        permission_manager: Permission manager for tools.

    Returns:
        A configured LlmAgent instance.
    """
    if config is None:
        config = AgentConfig()

    instruction = load_prompt("web_route_mapper.md")
    extras = google_provider_extras(config.provider)
    tools: list[Any] = [
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
