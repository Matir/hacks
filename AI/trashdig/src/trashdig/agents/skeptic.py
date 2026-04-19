from typing import Any

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from trashdig.agents.utils.helpers import google_provider_extras, load_prompt
from trashdig.config import AgentConfig
from trashdig.services.permissions import PermissionManager
from trashdig.tools import find_files, list_files, read_file, ripgrep_search, web_fetch


class SkepticAgent(LlmAgent):
    """Skeptic Agent for TrashDig."""
    pass


def create_skeptic_agent(
    config: AgentConfig | None = None,
    permission_manager: PermissionManager | None = None,
    extra_tools: list[Any] | None = None,
) -> SkepticAgent:
    """Creates a Skeptic agent."""
    if config is None:
        config = AgentConfig()

    instruction = load_prompt("skeptic.md")

    extras = google_provider_extras(config.provider)
    tools: list[Any] = [
        FunctionTool(ripgrep_search),
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

    return SkepticAgent(
        name="skeptic",
        model=config.model,
        instruction=instruction,
        description="Critically reviews potential vulnerabilities to identify false positives.",
        tools=tools,
        **kwargs,
    )
