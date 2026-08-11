from trashdig.config import WorkspacePathError, resolve_workspace_path
from trashdig.sandbox.landlock_tool import landlock_tool

from ..agents.utils.helpers import get_project_structure as _get_struct
from .base import filter_by_gitignore


@landlock_tool()
def get_project_structure(path: str | None = None) -> str:
    """Returns a list of all files in the project, respecting .gitignore.

    Args:
        path: The root directory to list. Defaults to Config workspace_root.

    Returns:
        A newline-separated list of file paths.
    """
    try:
        path = resolve_workspace_path(path)
    except WorkspacePathError as e:
        return f"Error: {e}"
    files = _get_struct(path)
    files = filter_by_gitignore(files, workspace_root=path)
    return "\n".join(files)

