from ..agents.utils import get_project_structure as _get_struct


def get_project_structure(path: str = ".") -> str:
    """Returns a list of all files in the project, respecting .gitignore.

    Args:
        path: The root directory to list.

    Returns:
        A newline-separated list of file paths.
    """
    files = _get_struct(path)
    return "\n".join(files)
