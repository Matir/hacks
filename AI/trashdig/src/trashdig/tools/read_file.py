from typing import Any

from trashdig.config import WorkspacePathError, resolve_workspace_path
from trashdig.sandbox.landlock_tool import landlock_tool

from .base import artifact_tool


@artifact_tool(max_chars=4000)
@landlock_tool()
def read_file(file_path: str, first_line: int | None = None, last_line: int | None = None, tool_context: Any = None) -> str:
    """Reads the content of a file, optionally restricted to a range of lines.

    Args:
        file_path: Path to the file to read.
        first_line: The first line to read (1-indexed). Defaults to 1.
        last_line: The last line to read (inclusive). If None, reads to EOF.
        tool_context: ADK context (injected).

    Returns:
        The file content or an error message.
    """
    try:
        file_path = resolve_workspace_path(file_path)
    except WorkspacePathError as e:
        return f"Error reading file {file_path}: {str(e)}"
    try:
        with open(file_path, encoding="utf-8") as f:
            lines = f.readlines()

        start_idx = 0 if first_line is None else max(0, first_line - 1)
        end_idx = len(lines) if last_line is None else last_line

        return "".join(lines[start_idx:end_idx])
    except Exception as e:
        return f"Error reading file {file_path}: {str(e)}"
