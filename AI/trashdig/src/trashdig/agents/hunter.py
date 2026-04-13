import os
import json
from typing import List
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool, google_search
from trashdig.config import AgentConfig
from trashdig.agents.utils import read_file_content
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
    web_fetch
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

    async def hunt_vulnerabilities(self, targets: List[str], project_root: str = ".") -> Dict[str, Any]:
        """Deep-dive into specific files to identify vulnerabilities.

        Args:
            targets: List of file paths to analyze.
            project_root: Root directory of the project.

        Returns:
            A dictionary with 'findings' (List[Finding]) and 'hypotheses' (List[Dict]).
        """
        all_findings = []
        all_hypotheses = []
        
        for target in targets:
            content = read_file_content(os.path.join(project_root, target))
            
            # For each target, run a deep-dive analysis.
            response = await self.run_async(
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
            
            try:
                cleaned_response = response.text.strip()
                if cleaned_response.startswith("```json"):
                    cleaned_response = cleaned_response[7:-3].strip()
                
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
                        cwe_id=raw.get("cwe_id")
                    )
                    # Automatically save to the findings/ directory
                    finding.save(os.path.join(project_root, "findings"))
                    all_findings.append(finding)

                # Handle hypotheses
                all_hypotheses.extend(data.get("hypotheses", []))

            except (json.JSONDecodeError, AttributeError):
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

    return HunterAgent(
        name="hunter",
        model=config.model,
        instruction=instruction,
        description="Performs deep-dive vulnerability analysis on prioritized targets.",
        tools=[
            FunctionTool(ripgrep_search),
            FunctionTool(semgrep_scan),
            FunctionTool(get_ast_summary),
            FunctionTool(query_cwe_database),
            FunctionTool(get_symbol_definition),
            FunctionTool(trace_variable),
            FunctionTool(find_references),
            FunctionTool(get_scope_info),
            FunctionTool(trace_variable_semantic),
            FunctionTool(web_fetch),
            google_search
        ],
    )
