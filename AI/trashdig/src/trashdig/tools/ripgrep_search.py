from typing import Any

from trashdig.sandbox.landlock_tool import landlock_tool

from .base import _run_sandboxed, artifact_tool, get_config

EXIT_COMMAND_NOT_FOUND = 127


@artifact_tool(max_chars=4000)
@landlock_tool()
def ripgrep_search(
    pattern: str,
    path: str | None = None,
    extra_args: list[str] | None = None,
    tool_context: Any = None,
) -> str:
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

    # rg exit codes: 0 = matches found, 1 = no matches (not an error), 2 = error
    if result.returncode == EXIT_COMMAND_NOT_FOUND:
        return result.stderr
    if result.returncode == 1:
        return ""
    if result.returncode != 0:
        return result.stderr or f"ripgrep error (exit {result.returncode})"
    return result.stdout
