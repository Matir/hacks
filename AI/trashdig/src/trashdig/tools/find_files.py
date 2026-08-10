import fnmatch
import os

from trashdig.config import WorkspacePathError, resolve_workspace_path
from trashdig.sandbox.landlock_tool import landlock_tool


@landlock_tool()
def find_files(
    pattern: str,
    directory: str | None = None,
    recursive: bool = True,
    case_sensitive: bool = False,
) -> str:
    """Finds files by name pattern in a given directory.

    Args:
        pattern: The file name pattern to search for (e.g., '*.py').
        directory: The root directory to start the search. Defaults to Config workspace_root.
        recursive: Whether to search subdirectories.
        case_sensitive: Whether the pattern matching should be case-sensitive.

    Returns:
        A newline-separated list of relative paths for matching files.
    """
    try:
        directory = resolve_workspace_path(directory)
    except WorkspacePathError as e:
        return f"Error: {e}"
    matches = []
    if not case_sensitive:
        pattern = pattern.lower()

    try:
        if recursive:
            for root, _, files in os.walk(directory):
                for filename in files:
                    full_path = os.path.join(root, filename)
                    rel_path = os.path.relpath(full_path, directory)
                    check_name = rel_path if case_sensitive else rel_path.lower()
                    if fnmatch.fnmatch(check_name, pattern):
                        matches.append(rel_path)
        else:
            for filename in os.listdir(directory):
                full_path = os.path.join(directory, filename)
                if os.path.isfile(full_path):
                    check_name = filename if case_sensitive else filename.lower()
                    if fnmatch.fnmatch(check_name, pattern):
                        matches.append(filename)
        return "\n".join(sorted(matches))
    except Exception as e:
        return f"Error searching in {directory}: {e}"
