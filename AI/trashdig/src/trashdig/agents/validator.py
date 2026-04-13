import os
import json
from typing import Dict, Any
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool, google_search
from trashdig.config import AgentConfig
from trashdig.agents.utils import read_file_content
from trashdig.tools import ripgrep_search, bash_tool, container_bash_tool, web_fetch
from trashdig.findings import Finding

def load_prompt(file_path: str) -> str:
    """Loads a prompt from a markdown file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

class ValidatorAgent(LlmAgent):
    """Validator Agent for TrashDig."""

    async def verify_finding(self, finding: Finding, tech_stack: str = "") -> Dict[str, Any]:
        """Attempts to verify a potential finding by running a PoC.

        Args:
            finding: The potential vulnerability to verify.
            tech_stack: The detected project tech stack.

        Returns:
            A dictionary with the verification results (status, poc_code, output).
        """
        # Read the file content where the vulnerability was found
        file_content = read_file_content(finding.file_path)
        
        response = await self.run_async(
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
        
        try:
            cleaned_response = response.text.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:-3].strip()
            return json.loads(cleaned_response)
        except (json.JSONDecodeError, AttributeError):
            return {
                "status": "Unverified",
                "error": "Failed to parse Validator response",
                "raw": response.text if hasattr(response, 'text') else str(response)
            }

def create_validator_agent(config: AgentConfig = None) -> ValidatorAgent:
    """Creates a Validator agent."""
    if config is None:
        config = AgentConfig()

    prompt_path = os.path.join(os.getcwd(), "prompts", "validator.md")
    instruction = load_prompt(prompt_path)

    return ValidatorAgent(
        name="validator",
        model=config.model,
        instruction=instruction,
        description="Generates and executes PoCs to verify potential vulnerabilities in isolated containers.",
        tools=[
            FunctionTool(ripgrep_search),
            FunctionTool(container_bash_tool),
            FunctionTool(bash_tool),
            FunctionTool(read_file_content),
            FunctionTool(web_fetch),
            google_search
        ],
    )
