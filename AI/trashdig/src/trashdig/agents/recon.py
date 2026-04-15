import os
import json
from typing import Dict, Any, Optional
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool, load_artifacts as load_artifacts_tool
from trashdig.config import AgentConfig
from trashdig.agents.utils import (
    get_project_structure,
    detect_frameworks,
    google_provider_extras,
)
from trashdig.services.permissions import PermissionManager
from trashdig.engine.engine import Engine
from trashdig.tools import (
    ripgrep_search,
    get_ast_summary,
    query_cwe_database,
    find_references,
    get_scope_info,
    web_fetch,
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

    async def scan(
        self,
        root_path: str = ".",
        log_fn=None,
        engine: Optional[Engine] = None,
    ) -> Dict[str, Any]:
        """Performs initial stack discovery and project mapping.

        Returns:
            A dictionary containing:
                - tech_stack: Detailed description of technologies.
                - is_web_app: Boolean indicating if it's a web app.
                - mapping: Dict of file paths to {summary, is_high_value}.
                - hypotheses: List of proposed security hypotheses.
        """
        if engine is None:
            engine = Engine()

        def _log(msg: str) -> None:
            if log_fn:
                log_fn(msg)

        _log(f"[bold]StackScout:[/bold] analyzing [cyan]{os.path.abspath(root_path)}[/cyan]")
        file_list = get_project_structure(root_path)
        
        # Deterministic check
        frameworks = detect_frameworks(file_list, root_path)
        stack_summary = ", ".join(
            [f"{cat}: {', '.join(libs)}" for cat, libs in frameworks.items() if libs]
        )
        if stack_summary:
            _log(f"[bold]StackScout:[/bold] deterministic stack — {stack_summary}")

        prompt = (
            f"Analyze the project at {os.path.abspath(root_path)}.\n"
            f"Deterministic Framework Detection: {stack_summary or 'None'}\n\n"
            f"File Tree:\n" + "\n".join(file_list) + "\n\n"
            "Identify the full tech stack, determine if it is a web application, "
            "map high-value files, and generate security hypotheses."
        )

        result = await engine.run(self, prompt)
        text = result.text

        try:
            cleaned_response = text.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:].rstrip("`").strip()
            data = json.loads(cleaned_response)
            _log(f"[bold]StackScout:[/bold] detected stack: [yellow]{data.get('tech_stack', 'Unknown')}[/yellow]")
            return data
        except (json.JSONDecodeError, AttributeError):
            return {
                "tech_stack": stack_summary,
                "is_web_app": len(frameworks.get("web_frameworks", [])) > 0,
                "mapping": {},
                "hypotheses": [],
                "error": "Failed to parse StackScout response"
            }


class WebRouteMapperAgent(LlmAgent):
    """WebRouteMapper Agent for TrashDig.

    Maps reachable endpoints and their handlers to build an attack surface map.
    """

    async def map_routes(
        self,
        root_path: str = ".",
        log_fn=None,
        engine: Optional[Engine] = None,
    ) -> Dict[str, Any]:
        """Identifies web routes and handlers."""
        if engine is None:
            engine = Engine()

        def _log(msg: str) -> None:
            if log_fn:
                log_fn(msg)

        _log("[bold]WebRouteMapper:[/bold] mapping attack surface…")

        prompt = "Identify all web routes, methods, handlers, and parameters in the project."

        result = await engine.run(self, prompt)
        text = result.text

        try:
            cleaned_response = text.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:].rstrip("`").strip()
            data = json.loads(cleaned_response)
            _log(f"[bold]WebRouteMapper:[/bold] found [yellow]{len(data.get('attack_surface', []))}[/yellow] endpoints")
            return data
        except (json.JSONDecodeError, AttributeError):
            return {"attack_surface": [], "error": "Failed to parse WebRouteMapper response"}


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
