from typing import List, Optional
from .base import artifact_tool, get_config
from .ripgrep_search import ripgrep_search

@artifact_tool(max_chars=5000)
def get_symbol_definition(symbol_name: str, path: Optional[str] = None) -> str:
    """Finds the definition of a function or class across the project.

    Args:
        symbol_name: The name of the function or class to find.
        path: The directory to search in. Defaults to Config workspace_root.

    Returns:
        The file path and a snippet of the definition if found.
    """
    if path is None:
        path = get_config().workspace_root
        
    patterns = [f"def {symbol_name}", f"class {symbol_name}", f"async def {symbol_name}"]
    results: List[str] = []
    
    for pattern in patterns:
        res = ripgrep_search(f"\\b{pattern}\\b", path, extra_args=["-C", "5"])
        if res and "Error" not in res:
            results.append(res)
            
    return "\n---\n".join(results) if results else f"Definition for '{symbol_name}' not found."
