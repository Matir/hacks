import os
import json
from typing import Dict, Any
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from trashdig.config import AgentConfig
from trashdig.agents.utils import read_file_content, run_prompt, google_provider_extras
from trashdig.tools import ripgrep_search, bash_tool, container_bash_tool, web_fetch
from trashdig.findings import Finding


def load_prompt(file_path: str) -> str:
    """Loads a prompt from a markdown file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


class ValidatorAgent(LlmAgent):
    """Validator Agent for TrashDig."""

    async def verify_finding(
        self,
        finding: Finding,
        tech_stack: str = "",
        log_fn=None,
        stats_fn=None,
        error_fn=None,
        conversation_log_fn=None,
    ) -> Dict[str, Any]:
        """Attempts to verify a potential finding by running a PoC.

        Args:
            finding: The potential vulnerability to verify.
            tech_stack: The detected project tech stack.
            log_fn: Optional callable for progress messages (Rich markup supported).
            stats_fn: Optional callable for token usage tracking.
            error_fn: Optional callable for LLM error tracking.
            conversation_log_fn: Optional callable for structured conversation logging.

        Returns:
            A dictionary with the verification results (status, poc_code, output).
        """

        def _log(msg: str) -> None:
            if log_fn:
                log_fn(msg)

        _log(
            f"[bold]Validator:[/bold] verifying [bold yellow]{finding.title}[/bold yellow]"
        )
        _log(f"  [dim]file: {finding.file_path}[/dim]")

        file_content = read_file_content(finding.file_path)
        _log("[bold]Validator:[/bold] generating and executing PoC…")

        prompt = (
            f"Please verify this potential finding:\n\n"
            f"Title: {finding.title}\n"
            f"Vulnerable Code:\n{finding.vulnerable_code}\n\n"
            f"Project Tech Stack: {tech_stack}\n"
            f"File Content:\n{file_content}\n\n"
            f"Instructions:\n"
            f"1. Generate a PoC (Python script, curl command, etc.).\n"
            f"2. Execute the PoC using `container_bash_tool`. This tool runs the command inside a temporary Docker container.\n"
            f"3. Analyze the results.\n"
            f"4. Provide a JSON response with: 'status' (Verified/False Positive), "
            f"'poc_code' (the script/command used), and 'reasoning' (why it was confirmed or refuted)."
        )

        result = await run_prompt(
            self,
            prompt,
            on_event=log_fn,
            on_stats=stats_fn,
            on_error=error_fn,
        )
        text = result["text"]

        if conversation_log_fn:
            conversation_log_fn(
                self.name,
                prompt,
                text,
                result["tool_calls"],
                result["input_tokens"],
                result["output_tokens"],
            )

        try:
            cleaned_response = text.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:].rstrip("`").strip()
            result = json.loads(cleaned_response)
            status = result.get("status", "Unverified")
            status_color = (
                "green"
                if status == "Verified"
                else "red"
                if status == "False Positive"
                else "yellow"
            )
            _log(f"[bold]Validator:[/bold] [{status_color}]{status}[/{status_color}]")
            if result.get("reasoning"):
                _log(
                    f"  [dim]{result['reasoning'][:120]}{'…' if len(result.get('reasoning', '')) > 120 else ''}[/dim]"
                )
            return result
        except (json.JSONDecodeError, AttributeError):
            if error_fn:
                error_fn()
            _log("[bold]Validator:[/bold] [red]failed to parse response[/red]")
            return {
                "status": "Unverified",
                "error": "Failed to parse Validator response",
                "raw": text,
            }


def create_validator_agent(config: AgentConfig = None) -> ValidatorAgent:
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
