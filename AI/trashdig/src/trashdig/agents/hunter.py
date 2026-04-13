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

    async def hunt_vulnerabilities(self, targets: List[str], project_root: str = ".") -> List[Finding]:
        """Deep-dive into specific files to identify vulnerabilities.

        Args:
            targets: List of file paths to analyze.
            project_root: Root directory of the project.

        Returns:
            A list of Finding objects.
        """
        all_findings = []
        
        for target in targets:
            content = read_file_content(os.path.join(project_root, target))
            
            # For each target, run a deep-dive analysis.
            response = await self.run_async(
                f"Analyze the following file for potential security vulnerabilities:\n\n"
                f"File: {target}\n"
                f"Content:\n{content}\n\n"
                f"Identify and document each finding with the following fields in a JSON list of objects:\n"
                f"- title: (Short title of the vulnerability)\n"
                f"- description: (Detailed description)\n"
                f"- severity: (Critical, High, Medium, Low, Info)\n"
                f"- vulnerable_code: (The exact snippet of vulnerable code)\n"
                f"- impact: (Potential impact)\n"
                f"- exploitation_path: (How it could be exploited)\n"
                f"- remediation: (How to fix it)\n"
                f"- cwe_id: (Optional CWE ID, e.g., CWE-89)\n"
            )
            
            try:
                cleaned_response = response.text.strip()
                if cleaned_response.startswith("```json"):
                    cleaned_response = cleaned_response[7:-3].strip()
                
                raw_findings = json.loads(cleaned_response)
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
            except (json.JSONDecodeError, AttributeError):
                continue
                
        return all_findings

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
