from typing import Any

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from trashdig.agents.utils.helpers import google_provider_extras, load_prompt
from trashdig.config import AgentConfig
from trashdig.services.permissions import PermissionManager
from trashdig.tools import (
    find_files,
    find_references,
    get_ast_summary,
    get_project_structure,
    get_scope_info,
    get_symbol_definition,
    list_files,
    read_file,
    ripgrep_search,
    trace_taint_cross_file,
    trace_variable_semantic,
)


class CodeInvestigatorAgent(LlmAgent):
    """Code Investigator Agent for TrashDig."""

    pass


def create_code_investigator_agent(
    config: AgentConfig | None = None,
    permission_manager: PermissionManager | None = None,
    extra_tools: list[Any] | None = None,
) -> CodeInvestigatorAgent:
    """Creates a Code Investigator agent."""
    if config is None:
        config = AgentConfig()

    instruction = load_prompt("code_investigator.md")

    extras = google_provider_extras(config.provider)
    tools: list[Any] = [
        FunctionTool(list_files),
        FunctionTool(find_files),
        FunctionTool(get_project_structure),
        FunctionTool(ripgrep_search),
        FunctionTool(find_references),
        FunctionTool(read_file),
        FunctionTool(get_ast_summary),
        FunctionTool(get_symbol_definition),
        FunctionTool(trace_variable_semantic),
        FunctionTool(get_scope_info),
        FunctionTool(trace_taint_cross_file),
    ]

    if permission_manager:
        tools = permission_manager.wrap_tools(tools)
    if extra_tools:
        tools.extend(extra_tools)

    kwargs = (
        {"generate_content_config": extras["generate_content_config"]}
        if extras["generate_content_config"]
        else {}
    )

    return CodeInvestigatorAgent(
        name="code_investigator",
        model=config.model,
        instruction=instruction,
        description="Answers specific technical questions about the codebase.",
        tools=tools,
        **kwargs,
    )
