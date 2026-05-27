from typing import Any

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from trashdig.agents.utils.helpers import google_provider_extras, load_prompt
from trashdig.config import AgentConfig
from trashdig.services.permissions import PermissionManager
from trashdig.tools import (
    find_files,
    list_files,
    query_vulndb,
    read_file,
    ripgrep_search,
    web_fetch,
)


class CriticAgent(LlmAgent):
    """Critic Agent for TrashDig."""
    pass


def create_critic_agent(
    config: AgentConfig | None = None,
    permission_manager: PermissionManager | None = None,
    extra_tools: list[Any] | None = None,
) -> CriticAgent:
    """Creates a Critic agent.

    Args:
        config: Optional agent configuration.
        permission_manager: Optional permission manager for wrapping tools.
        extra_tools: Optional additional tools.

    Returns:
        A configured CriticAgent instance.
    """
    if config is None:
        config = AgentConfig()

    instruction = load_prompt("critic.md")
    extras = google_provider_extras(config.provider)

    tools: list[Any] = [
        FunctionTool(ripgrep_search),
        FunctionTool(query_vulndb),
        FunctionTool(read_file),
        FunctionTool(web_fetch),
        FunctionTool(list_files),
        FunctionTool(find_files),
    ]

    if extras["google_search_tool"] is not None:
        tools.append(extras["google_search_tool"])

    if permission_manager:
        tools = permission_manager.wrap_tools(tools)
    if extra_tools:
        tools.extend(extra_tools)

    kwargs = (
        {"generate_content_config": extras["generate_content_config"]}
        if extras["generate_content_config"]
        else {}
    )

    return CriticAgent(
        name="critic",
        model=config.model,
        instruction=instruction,
        description="Adversarial reviewer that challenges hypotheses and PoC results.",
        tools=tools,
        **kwargs,
    )
