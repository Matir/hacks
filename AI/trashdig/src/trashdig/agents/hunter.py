import os
import json
from typing import List, Dict, Any
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from trashdig.config import AgentConfig
from trashdig.agents.utils import read_file_content, run_prompt, google_provider_extras
from trashdig.tools import (
    ripgrep_search,
    semgrep_scan,
    get_ast_summary,
    query_cwe_database,
    get_symbol_definition,
    trace_variable,
    find_references,
    get_scope_info,
    trace_variable_semantic,
    trace_taint_cross_file,
    web_fetch,
)
from trashdig.findings import Finding


def load_prompt(file_path: str) -> str:
    """Loads a prompt from a markdown file.

    Args:
        file_path: Path to the prompt file.

    Returns:
        The content of the prompt file.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


class HunterAgent(LlmAgent):
    """Hunter Agent for TrashDig."""

    async def hunt_vulnerabilities(
        self,
        targets: List[str],
        project_root: str = ".",
        log_fn=None,
        stats_fn=None,
        error_fn=None,
        conversation_log_fn=None,
    ) -> Dict[str, Any]:
        """Deep-dive into specific files to identify vulnerabilities.

        Args:
            targets: List of file paths to analyze.
            project_root: Root directory of the project.
            log_fn: Optional callable for progress messages (Rich markup supported).
            stats_fn: Optional callable for token usage tracking.
            error_fn: Optional callable for LLM error tracking.
            conversation_log_fn: Optional callable for structured conversation logging.

        Returns:
            A dictionary with 'findings' (List[Finding]) and 'hypotheses' (List[Dict]).
        """

        def _log(msg: str) -> None:
            if log_fn:
                log_fn(msg)

        all_findings = []
        all_hypotheses = []

        for i, target in enumerate(targets, 1):
            _log(
                f"[bold]Hunter:[/bold] analysing [cyan]{target}[/cyan] "
                f"([dim]{i}/{len(targets)}[/dim])"
            )
            content = read_file_content(os.path.join(project_root, target))

            prompt = (
                f"Analyze the following file for potential security vulnerabilities:\n\n"
                f"File: {target}\n"
                f"Content:\n{content}\n\n"
                f"Identify and document each finding or follow-up hypothesis in a JSON response with two keys:\n"
                f"1. 'findings': A list of vulnerability objects:\n"
                f"   - title, description, severity, vulnerable_code, impact, exploitation_path, remediation, cwe_id\n"
                f"2. 'hypotheses': A list of follow-up tasks if you need to trace data flow into other files:\n"
                f"   - target: (The file path or symbol to investigate next)\n"
                f"   - description: (Why you need to look there)\n"
                f"   - confidence: (0.0 to 1.0)\n"
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

                data = json.loads(cleaned_response)

                # Handle findings
                raw_findings = data.get("findings", [])
                if not isinstance(raw_findings, list):
                    raw_findings = [raw_findings]

                for raw in raw_findings:
                    finding = Finding(
                        title=raw.get("title", "Untitled"),
                        description=raw.get("description", "N/A"),
                        severity=raw.get("severity", "N/A"),
                        vulnerable_code=raw.get("vulnerable_code", "N/A"),
                        file_path=target,
                        impact=raw.get("impact", "N/A"),
                        exploitation_path=raw.get("exploitation_path", "N/A"),
                        remediation=raw.get("remediation", "N/A"),
                        cwe_id=raw.get("cwe_id"),
                    )
                    finding.save(os.path.join(project_root, "findings"))
                    all_findings.append(finding)
                    sev_color = {
                        "critical": "red",
                        "high": "red",
                        "medium": "yellow",
                        "low": "green",
                    }.get((finding.severity or "").lower(), "white")
                    _log(
                        f"  [bold {sev_color}]■[/bold {sev_color}] "
                        f"[bold]{finding.title}[/bold] "
                        f"([{sev_color}]{finding.severity}[/{sev_color}])"
                        f" — {finding.description[:80]}{'…' if len(finding.description) > 80 else ''}"
                    )

                hypos = data.get("hypotheses", [])
                all_hypotheses.extend(hypos)
                if hypos:
                    _log(
                        f"  [dim]→ {len(hypos)} follow-up hypothesis{'es' if len(hypos) != 1 else ''} queued[/dim]"
                    )

                if not raw_findings:
                    _log(f"  [dim]no findings in {target}[/dim]")

            except (json.JSONDecodeError, AttributeError):
                if error_fn:
                    error_fn()
                _log(f"  [red]failed to parse Hunter response for {target}[/red]")
                continue

        return {"findings": all_findings, "hypotheses": all_hypotheses}


def create_hunter_agent(config: AgentConfig = None) -> HunterAgent:
    """Creates a Hunter agent.

    Args:
        config: Optional agent configuration.

    Returns:
        A configured HunterAgent instance.
    """
    if config is None:
        config = AgentConfig()

    prompt_path = os.path.join(os.getcwd(), "prompts", "hunter.md")
    instruction = load_prompt(prompt_path)

    extras = google_provider_extras(config.provider)
    tools = [
        FunctionTool(ripgrep_search),
        FunctionTool(semgrep_scan),
        FunctionTool(get_ast_summary),
        FunctionTool(query_cwe_database),
        FunctionTool(get_symbol_definition),
        FunctionTool(trace_variable),
        FunctionTool(find_references),
        FunctionTool(get_scope_info),
        FunctionTool(trace_variable_semantic),
        FunctionTool(trace_taint_cross_file),
        FunctionTool(web_fetch),
    ]
    if extras["google_search_tool"] is not None:
        tools.append(extras["google_search_tool"])

    kwargs = (
        {"generate_content_config": extras["generate_content_config"]}
        if extras["generate_content_config"]
        else {}
    )

    return HunterAgent(
        name="hunter",
        model=config.model,
        instruction=instruction,
        description="Performs deep-dive vulnerability analysis on prioritized targets.",
        tools=tools,
        **kwargs,
    )
