from typing import Any

from trashdig.utils import is_binary_available

from .base import WorkspacePathError, _run_sandboxed, artifact_tool, resolve_workspace_path

EXIT_TIMEOUT = 124


@artifact_tool(max_chars=8000)
def semgrep_scan(
    path: str | None = None, config: str = "p/security-audit", tool_context: Any = None
) -> str:
    """Scans the codebase for security patterns using semgrep.

    Args:
        path: The directory or file to scan. Defaults to Config workspace_root.
        config: The semgrep configuration/rules to use (e.g., "p/security-audit", "p/python").
        tool_context: ADK context (injected).

    Returns:
        The JSON output of the semgrep scan as a string.
    """
    if not is_binary_available("semgrep"):
        return "Error: semgrep is not installed or not in PATH."

    try:
        path = resolve_workspace_path(path)
    except WorkspacePathError as e:
        return f"Error: {e}"

    cmd = ["semgrep", "--json", "--config", config, path]

    # Run semgrep with a timeout to avoid hanging
    result = _run_sandboxed(cmd, timeout=120, network=True, workspace_dir=path)
    if result.returncode == EXIT_TIMEOUT:
        return result.stderr
    return result.stdout if result.stdout else result.stderr
