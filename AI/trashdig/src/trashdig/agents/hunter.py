from typing import Any

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from google.adk.tools import load_artifacts as load_artifacts_tool

from trashdig.agents.utils import google_provider_extras, load_prompt
from trashdig.config import AgentConfig
from trashdig.services.permissions import PermissionManager
from trashdig.tools import (
    find_references,
    get_ast_summary,
    get_scope_info,
    get_symbol_definition,
    query_cwe_database,
    read_file,
    ripgrep_search,
    semgrep_scan,
    trace_taint_cross_file,
    trace_variable,
    trace_variable_semantic,
    web_fetch,
)


class HunterAgent(LlmAgent):
    """Hunter Agent for TrashDig."""
    pass


def create_hunter_agent(
    config: AgentConfig | None = None, permission_manager: PermissionManager | None = None
) -> HunterAgent:
    """Creates a Hunter agent.

    Args:
        config: Optional agent configuration.
        permission_manager: Optional permission manager.

    Returns:
        A configured HunterAgent instance.
    """
    if config is None:
        config = AgentConfig()

    instruction = load_prompt("hunter.md")

    extras = google_provider_extras(config.provider)
    tools: list[Any] = [
        FunctionTool(ripgrep_search),
        FunctionTool(semgrep_scan),
        FunctionTool(get_ast_summary),
        FunctionTool(query_cwe_database),
        FunctionTool(get_symbol_definition),
        FunctionTool(trace_variable),
        FunctionTool(find_references),
        FunctionTool(get_scope_info),
        FunctionTool(trace_variable_semantic),
        FunctionTool(trace_taint_cross_file),
        FunctionTool(web_fetch),
        FunctionTool(read_file),
        load_artifacts_tool,
    ]
    if extras["google_search_tool"] is not None:
        tools.append(extras["google_search_tool"])

    if permission_manager:
        tools = permission_manager.wrap_tools(tools)

    kwargs = (
        {"generate_content_config": extras["generate_content_config"]}
        if extras["generate_content_config"]
        else {}
    )

    return HunterAgent(
        name="hunter",
        model=config.model,
        instruction=instruction,
        description="Performs deep-dive vulnerability analysis on prioritized targets.",
        tools=tools,
        **kwargs,
    )
