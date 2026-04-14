import os
import json
from typing import Dict, Any, Optional
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from trashdig.config import AgentConfig
from trashdig.agents.utils import read_file_content, google_provider_extras
from trashdig.services.permissions import PermissionManager
from trashdig.engine.engine import Engine
from trashdig.tools import ripgrep_search, web_fetch
from trashdig.findings import Finding


def load_prompt(file_path: str) -> str:
    """Loads a prompt from a markdown file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


class SkepticAgent(LlmAgent):
    """Skeptic Agent for TrashDig."""

    async def debunk_finding(
        self,
        finding: Finding,
        project_root: str = ".",
        log_fn=None,
        engine: Optional[Engine] = None,
        stats_fn=None,
        error_fn=None,
        conversation_log_fn=None,
    ) -> Dict[str, Any]:
        """Attempts to debunk a potential finding by performing an adversarial review.

        Args:
            finding: The potential vulnerability to debunk.
            project_root: The project root directory.
            log_fn: Optional callable for progress messages.
            engine: Optional Engine instance to use.
            stats_fn: Optional callable for token usage tracking.
            error_fn: Optional callable for LLM error tracking.
            conversation_log_fn: Optional callable for structured conversation logging.

        Returns:
            A dictionary with the debunking results (is_valid, skeptic_notes).
        """
        if engine is None:
            engine = Engine()

        def _log(msg: str) -> None:
            if log_fn:
                log_fn(msg)

        _log(
            f"[bold]Skeptic:[/bold] reviewing [bold yellow]{finding.title}[/bold yellow]"
        )

        file_content = read_file_content(finding.file_path)
        _log("[bold]Skeptic:[/bold] analyzing for logical flaws…")

        prompt = (
            f"Please review this potential finding and try to debunk it:\n\n"
            f"Title: {finding.title}\n"
            f"Description: {finding.description}\n"
            f"Vulnerable Code:\n{finding.vulnerable_code}\n\n"
            f"File Path: {finding.file_path}\n"
            f"File Content:\n{file_content}\n\n"
            f"Your Goal:\n"
            f"Find any reason why this is a False Positive. Check reachability, "
            f"framework protections, or logical errors in the original report."
        )

        result = await engine.run(
            self,
            prompt,
            on_event=log_fn,
            on_stats=stats_fn,
            on_error=error_fn,
        )
        text = result.text

        if conversation_log_fn:
            conversation_log_fn(
                self.name,
                prompt,
                text,
                result.tool_calls,
                result.input_tokens,
                result.output_tokens,
            )

        try:
            cleaned_response = text.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:].rstrip("`").strip()
            result_data = json.loads(cleaned_response)
            
            is_valid = result_data.get("is_valid", True)
            status = "Survived Scrutiny" if is_valid else "Debunked"
            status_color = "green" if is_valid else "red"
            
            _log(f"[bold]Skeptic:[/bold] [{status_color}]{status}[/{status_color}]")
            if result_data.get("skeptic_notes"):
                _log(
                    f"  [dim]{result_data['skeptic_notes'][:120]}{'…' if len(result_data.get('skeptic_notes', '')) > 120 else ''}[/dim]"
                )
            return {
                "is_valid": is_valid,
                "skeptic_notes": result_data.get("skeptic_notes", "")
            }
        except (json.JSONDecodeError, AttributeError):
            if error_fn:
                error_fn()
            _log("[bold]Skeptic:[/bold] [red]failed to parse response[/red]")
            return {
                "is_valid": True, # Fail safe: assume it is valid if the skeptic fails
                "error": "Failed to parse Skeptic response",
                "skeptic_notes": f"Error parsing response: {text}",
            }


def create_skeptic_agent(
    config: AgentConfig = None, permission_manager: Optional[PermissionManager] = None
) -> SkepticAgent:
    """Creates a Skeptic agent."""
    if config is None:
        config = AgentConfig()

    prompt_path = os.path.join(os.getcwd(), "prompts", "skeptic.md")
    instruction = load_prompt(prompt_path)

    extras = google_provider_extras(config.provider)
    tools = [
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
