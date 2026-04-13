import os
import json
from typing import Dict, Any
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool, google_search
from trashdig.config import AgentConfig
from trashdig.agents.utils import get_project_structure, detect_frameworks
from trashdig.tools import (
    ripgrep_search,
    get_ast_summary,
    query_cwe_database,
    find_references,
    get_scope_info,
    web_fetch
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
    """Archaeologist Agent for TrashDig."""

    async def scan_project(self, root_path: str = ".") -> Dict[str, Any]:
        """Scans the project structure and provides summaries.

        Args:
            root_path: Root directory of the project to scan.

        Returns:
            A dictionary mapping file paths to their summaries and flags.
        """
        file_list = get_project_structure(root_path)
        tech_stack = detect_frameworks(file_list, root_path)
        
        stack_str = ", ".join([f"{cat}: {', '.join(libs)}" for cat, libs in tech_stack.items() if libs])
        
        prompt_data = {
            "project_context": f"Project located at {os.path.abspath(root_path)}",
            "file_tree": "\n".join(file_list),
            "tech_stack": stack_str or "Unknown"
        }
        
        # The prompt is already loaded as 'instruction' during initialization.
        response = await self.run_async(
            f"Please analyze this project structure. The project uses the following technologies: {prompt_data['tech_stack']}.\n\n"
            f"Provide a JSON response with two keys:\n"
            f"1. 'mapping': A dictionary mapping file paths to a dictionary containing 'summary' (1 sentence) and "
            f"'is_high_value' (boolean).\n"
            f"2. 'hypotheses': A list of objects with 'target' (file path), 'description' (what to look for), and "
            f"'confidence' (0.0-1.0).\n\n"
            f"Flag files as high-value and propose hypotheses if they contain security-critical "
            f"logic relevant to the detected frameworks (e.g., routes, auth, db queries).\n\n"
            f"Only return the JSON object.\n\n"
            f"File Tree:\n{prompt_data['file_tree']}"
        )
        
        try:
            # Clean up response if it has markdown formatting
            cleaned_response = response.text.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:-3].strip()
            
            data = json.loads(cleaned_response)
            # Support both old and new formats for robustness
            if "mapping" in data:
                return data
            return {"mapping": data, "hypotheses": []}
        except (json.JSONDecodeError, AttributeError):
            # Fallback or error handling
            return {"error": "Failed to parse Archaeologist response", "raw": response.text if hasattr(response, 'text') else str(response)}

def create_archaeologist_agent(config: AgentConfig = None) -> ArchaeologistAgent:
    """Creates an Archaeologist agent.

    Args:
        config: Optional agent configuration.

    Returns:
        A configured ArchaeologistAgent instance.
    """
    if config is None:
        config = AgentConfig()

    prompt_path = os.path.join(os.getcwd(), "prompts", "archaeologist.md")
    instruction = load_prompt(prompt_path)

    return ArchaeologistAgent(
        name="archaeologist",
        model=config.model,
        instruction=instruction,
        description="Maps the project structure and summarizes high-level file purposes for security researchers.",
        tools=[
            FunctionTool(ripgrep_search),
            FunctionTool(get_ast_summary),
            FunctionTool(query_cwe_database),
            FunctionTool(find_references),
            FunctionTool(get_scope_info),
            FunctionTool(web_fetch),
            google_search
        ],
    )
