from typing import Any

from trashdig.sandbox.landlock_tool import landlock_tool

from .base import WorkspacePathError, _run_sandboxed, artifact_tool, resolve_workspace_path

EXIT_COMMAND_NOT_FOUND = 127


@artifact_tool(max_chars=4000)
@landlock_tool()
def ripgrep_search(  # noqa: PLR0913
    pattern: str,
    path: str | None = None,
    extra_args: list[str] | None = None,
    lines_before: int | None = None,
    lines_after: int | None = None,
    number_lines: bool = False,
    tool_context: Any = None,
) -> str:
    """Performs a fast textual search across the codebase using ripgrep.

    Args:
        pattern: The regex pattern to search for.
        path: The directory or file to search in. Defaults to Config workspace_root.
        extra_args: Additional arguments to pass to rg (e.g., ["-i"]).
        lines_before: Print num lines of leading context before matching lines (-B).
        lines_after: Print num lines of trailing context after matching lines (-A).
        number_lines: Show line numbers with each match (-n).
        tool_context: ADK context (injected).

    Returns:
        The standard output of the ripgrep command.
    """
    try:
        path = resolve_workspace_path(path)
    except WorkspacePathError as e:
        return f"Error: {e}"

    cmd = ["rg", "--column", "--no-heading", "--color", "never", pattern, path]
    if number_lines:
        cmd.append("-n")
    if lines_before is not None:
        cmd.extend(["-B", str(lines_before)])
    if lines_after is not None:
        cmd.extend(["-A", str(lines_after)])
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
