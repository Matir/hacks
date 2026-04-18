from typing import Any

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from trashdig.agents.utils.helpers import google_provider_extras, load_prompt
from trashdig.config import AgentConfig
from trashdig.services.permissions import PermissionManager
from trashdig.tools import (
    bash_tool,
    container_bash_tool,
    find_files,
    list_files,
    read_file,
    ripgrep_search,
    web_fetch,
)


class ValidatorAgent(LlmAgent):
    """Validator Agent for TrashDig."""
    pass


def create_validator_agent(
    config: AgentConfig | None = None, permission_manager: PermissionManager | None = None
) -> ValidatorAgent:
    """Creates a Validator agent."""
    if config is None:
        config = AgentConfig()

    instruction = load_prompt("validator.md")

    extras = google_provider_extras(config.provider)
    tools: list[Any] = [
        FunctionTool(ripgrep_search),
        FunctionTool(container_bash_tool),
        FunctionTool(bash_tool),
        FunctionTool(read_file),
        FunctionTool(web_fetch),
        FunctionTool(list_files),
        FunctionTool(find_files),
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

    return ValidatorAgent(
        name="validator",
        model=config.model,
        instruction=instruction,
        description="Generates and executes PoCs to verify potential vulnerabilities in isolated containers.",
        tools=tools,
        **kwargs,
    )
