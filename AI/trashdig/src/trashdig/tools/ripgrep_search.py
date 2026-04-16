from typing import Any

from .base import _run_sandboxed, artifact_tool, get_config


@artifact_tool(max_chars=4000)
def ripgrep_search(pattern: str, path: str | None = None, extra_args: list[str] | None = None, tool_context: Any = None) -> str:
    """Performs a fast textual search across the codebase using ripgrep.

    Args:
        pattern: The regex pattern to search for.
        path: The directory or file to search in. Defaults to Config workspace_root.
        extra_args: Additional arguments to pass to rg (e.g., ["-i", "-A", "2"]).
        tool_context: ADK context (injected).

    Returns:
        The standard output of the ripgrep command.
    """
    if path is None:
        path = get_config().workspace_root
        
    cmd = ["rg", "--column", "--line-number", "--no-heading", "--color", "never", pattern, path]
    if extra_args:
        cmd.extend(extra_args)
    
    result = _run_sandboxed(cmd, network=False, workspace_dir=path)
    
    # The existing tests expect specific error messages if rg is not found
    if result.returncode == 127:
        return result.stderr
    return result.stdout if result.stdout else result.stderr
