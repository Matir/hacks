import os
from typing import Optional
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from trashdig.config import AgentConfig
from trashdig.agents.utils import read_file_content, google_provider_extras
from trashdig.services.permissions import PermissionManager
from trashdig.tools import ripgrep_search, bash_tool, container_bash_tool, web_fetch


def load_prompt(file_path: str) -> str:
    """Loads a prompt from a markdown file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


class ValidatorAgent(LlmAgent):
    """Validator Agent for TrashDig."""
    pass


def create_validator_agent(
    config: AgentConfig = None, permission_manager: Optional[PermissionManager] = None
) -> ValidatorAgent:
    """Creates a Validator agent."""
    if config is None:
        config = AgentConfig()

    prompt_path = os.path.join(os.getcwd(), "prompts", "validator.md")
    instruction = load_prompt(prompt_path)

    extras = google_provider_extras(config.provider)
    tools = [
        FunctionTool(ripgrep_search),
        FunctionTool(container_bash_tool),
        FunctionTool(bash_tool),
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

    return ValidatorAgent(
        name="validator",
        model=config.model,
        instruction=instruction,
        description="Generates and executes PoCs to verify potential vulnerabilities in isolated containers.",
        tools=tools,
        **kwargs,
    )
