import os
from typing import Optional
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool, load_artifacts as load_artifacts_tool
from trashdig.config import AgentConfig
from trashdig.agents.utils import google_provider_extras
from trashdig.services.permissions import PermissionManager
from trashdig.tools import (
    ripgrep_search,
    semgrep_scan,
    get_ast_summary,
    query_cwe_database,
    get_symbol_definition,
    trace_variable,
    find_references,
    get_scope_info,
    trace_variable_semantic,
    trace_taint_cross_file,
    web_fetch,
    read_file,
)


def load_prompt(file_path: str) -> str:
    """Loads a prompt from a markdown file.

    Args:
        file_path: Path to the prompt file.

    Returns:
        The content of the prompt file.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


class HunterAgent(LlmAgent):
    """Hunter Agent for TrashDig."""
    pass


def create_hunter_agent(
    config: AgentConfig = None, permission_manager: Optional[PermissionManager] = None
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

    prompt_path = os.path.join(os.getcwd(), "prompts", "hunter.md")
    instruction = load_prompt(prompt_path)

    extras = google_provider_extras(config.provider)
    tools = [
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
