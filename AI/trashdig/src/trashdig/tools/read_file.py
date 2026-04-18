from typing import Any

from trashdig.sandbox.landlock_tool import landlock_tool

from .base import artifact_tool


@artifact_tool(max_chars=4000)
@landlock_tool()
def read_file(file_path: str, tool_context: Any = None) -> str:
    """Reads the complete content of a file.

    Args:
        file_path: Path to the file to read.
        tool_context: ADK context (injected).

    Returns:
        The file content or an error message.
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file {file_path}: {str(e)}"
