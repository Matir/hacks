import os
import json
from typing import Dict, Any, Optional
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from trashdig.config import AgentConfig
from trashdig.agents.utils import (
    get_project_structure,
    detect_frameworks,
    run_prompt,
    google_provider_extras,
)
from trashdig.tools import (
    ripgrep_search,
    get_ast_summary,
    query_cwe_database,
    find_references,
    get_scope_info,
    web_fetch,
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


class ArchaeologistAgent(LlmAgent):
    """Archaeologist Agent for TrashDig.

    This agent is responsible for mapping the project structure, identifying
    high-value targets (entry points, controllers, etc.), and generating
    initial vulnerability hypotheses.
    """

    async def scan_project(self, root_path: str = ".", log_fn=None, stats_fn=None, error_fn=None) -> Dict[str, Any]:
        """Scans the project structure and provides summaries.

        Args:
            root_path: Root directory of the project to scan.
            log_fn: Optional callable for progress messages (Rich markup supported).

        Returns:
            A dictionary containing:
                - mapping: A dict of file paths to {summary, is_high_value}.
                - hypotheses: A list of proposed security hypotheses.
                - tech_stack: A string description of detected technologies.
        """

        def _log(msg: str) -> None:
            if log_fn:
                log_fn(msg)

        _log(
            f"[bold]Archaeologist:[/bold] walking [cyan]{os.path.abspath(root_path)}[/cyan]"
        )
        file_list = get_project_structure(root_path)
        _log(
            f"[bold]Archaeologist:[/bold] found [yellow]{len(file_list)}[/yellow] files"
        )

        tech_stack = detect_frameworks(file_list, root_path)
        stack_str = ", ".join(
            [f"{cat}: {', '.join(libs)}" for cat, libs in tech_stack.items() if libs]
        )
        if stack_str:
            _log(f"[bold]Archaeologist:[/bold] tech stack — {stack_str}")
        else:
            _log(
                "[bold]Archaeologist:[/bold] tech stack — unknown (no recognised dependency files)"
            )

        _log(
            "[bold]Archaeologist:[/bold] asking LLM to map files and identify high-value targets…"
        )

        prompt_data = {
            "project_context": f"Project located at {os.path.abspath(root_path)}",
            "file_tree": "\n".join(file_list),
            "tech_stack": stack_str or "Unknown",
        }

        text = await run_prompt(
            self,
            f"Please analyze this project structure. The project uses the following technologies: {prompt_data['tech_stack']}.\n\n"
            f"Provide a JSON response with two keys:\n"
            f"1. 'mapping': A dictionary mapping file paths to a dictionary containing 'summary' (1 sentence) and "
            f"'is_high_value' (boolean).\n"
            f"2. 'hypotheses': A list of objects with 'target' (file path), 'description' (what to look for), and "
            f"'confidence' (0.0-1.0).\n\n"
            f"Flag files as high-value and propose hypotheses if they contain security-critical "
            f"logic relevant to the detected frameworks (e.g., routes, auth, db queries).\n\n"
            f"Only return the JSON object.\n\n"
            f"File Tree:\n{prompt_data['file_tree']}",
            on_event=log_fn,
            on_stats=stats_fn,
            on_error=error_fn,
        )

        try:
            cleaned_response = text.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:].rstrip("`").strip()

            data: Dict[str, Any] = json.loads(cleaned_response)
            # Support both old and new formats for robustness
            if "mapping" not in data:
                data = {"mapping": data, "hypotheses": [], "tech_stack": stack_str}
            else:
                data["tech_stack"] = stack_str

            mapping = data.get("mapping", {})
            high_value = [
                p
                for p, d in mapping.items()
                if isinstance(d, dict) and d.get("is_high_value")
            ]
            _log(
                f"[bold]Archaeologist:[/bold] mapped [yellow]{len(mapping)}[/yellow] files, "
                f"[green]{len(high_value)}[/green] flagged as high-value"
            )
            for path in high_value:
                summary = mapping[path].get("summary", "")
                _log(f"  [green]★[/green] [cyan]{path}[/cyan] — {summary}")

            hypos = data.get("hypotheses", [])
            if hypos:
                _log(
                    f"[bold]Archaeologist:[/bold] generated [yellow]{len(hypos)}[/yellow] follow-up hypotheses"
                )
                for h in hypos:
                    conf = h.get("confidence", 0)
                    _log(
                        f"  [dim]? {h.get('target', '?')} (confidence {conf:.0%}) — {h.get('description', '')}[/dim]"
                    )

            return data
        except (json.JSONDecodeError, AttributeError):
            if error_fn:
                error_fn()
            return {
                "mapping": {},
                "hypotheses": [],
                "tech_stack": stack_str,
                "error": "Failed to parse Archaeologist response",
                "raw": text,
            }


def create_archaeologist_agent(
    config: Optional[AgentConfig] = None,
) -> ArchaeologistAgent:
    """Creates and configures an Archaeologist agent.

    Args:
        config: Optional agent configuration. If None, default config is used.

    Returns:
        A configured ArchaeologistAgent instance.
    """
    if config is None:
        config = AgentConfig()

    prompt_path = os.path.join(os.getcwd(), "prompts", "archaeologist.md")
    instruction = load_prompt(prompt_path)

    extras = google_provider_extras(config.provider)
    tools = [
        FunctionTool(ripgrep_search),
        FunctionTool(get_ast_summary),
        FunctionTool(query_cwe_database),
        FunctionTool(find_references),
        FunctionTool(get_scope_info),
        FunctionTool(web_fetch),
    ]
    if extras["google_search_tool"] is not None:
        tools.append(extras["google_search_tool"])

    kwargs = (
        {"generate_content_config": extras["generate_content_config"]}
        if extras["generate_content_config"]
        else {}
    )

    return ArchaeologistAgent(
        name="archaeologist",
        model=config.model,
        instruction=instruction,
        description="Maps the project structure and summarizes high-level file purposes for security researchers.",
        tools=tools,
        **kwargs,
    )
