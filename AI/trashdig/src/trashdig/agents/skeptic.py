from typing import Any, List, Optional

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from trashdig.agents.utils import google_provider_extras, load_prompt, read_file_content
from trashdig.config import AgentConfig
from trashdig.services.permissions import PermissionManager
from trashdig.tools import ripgrep_search, web_fetch


class SkepticAgent(LlmAgent):
    """Skeptic Agent for TrashDig."""
    pass


def create_skeptic_agent(
    config: Optional[AgentConfig] = None, permission_manager: Optional[PermissionManager] = None
) -> SkepticAgent:
    """Creates a Skeptic agent."""
    if config is None:
        config = AgentConfig()

    instruction = load_prompt("skeptic.md")

    extras = google_provider_extras(config.provider)
    tools: List[Any] = [
        FunctionTool(ripgrep_search),
        FunctionTool(read_file_content),
        FunctionTool(web_fetch),
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

    return SkepticAgent(
        name="skeptic",
        model=config.model,
        instruction=instruction,
        description="Critically reviews potential vulnerabilities to identify false positives.",
        tools=tools,
        **kwargs,
    )
