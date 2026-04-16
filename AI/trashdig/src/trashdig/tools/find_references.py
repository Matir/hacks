from typing import Optional, Any
from .base import artifact_tool, get_config
from .ripgrep_search import ripgrep_search

@artifact_tool(max_chars=5000)
def find_references(symbol_name: str, path: Optional[str] = None, tool_context: Any = None) -> str:
    """Finds all references (call sites, usages) of a symbol in the project.

    Args:
        symbol_name: The name of the symbol to find.
        path: The directory to search in. Defaults to Config workspace_root.
        tool_context: ADK context (injected).

    Returns:
        A list of occurrences.
    """
    if path is None:
        path = get_config().workspace_root
        
    # Use ripgrep to find all usages, but exclude definitions
    extra_args = ["--line-number", "--column", "-v", f"def {symbol_name}|class {symbol_name}"]
    return ripgrep_search(f"\\b{symbol_name}\\b", path, extra_args=extra_args)
