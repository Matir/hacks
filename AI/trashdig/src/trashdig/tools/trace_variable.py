from trashdig.sandbox.landlock_tool import landlock_tool

from .base import artifact_tool
from .ripgrep_search import ripgrep_search


@artifact_tool(max_chars=5000)
@landlock_tool()
def trace_variable(variable_name: str, file_path: str) -> str:
    """Finds all occurrences of a variable in a file to trace its flow.

    Args:
        variable_name: Name of the variable to trace.
        file_path: Path to the file.

    Returns:
        The results of the ripgrep search for the variable.
    """
    return ripgrep_search(
        f"\\b{variable_name}\\b", file_path, extra_args=["--line-number", "--column"]
    )
