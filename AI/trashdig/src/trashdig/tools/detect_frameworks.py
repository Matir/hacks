import json

from trashdig.config import WorkspacePathError, resolve_workspace_path

from ..agents.utils.helpers import detect_frameworks as _detect
from ..agents.utils.helpers import get_project_structure as _get_struct


def detect_frameworks(path: str | None = None) -> str:
    """Performs deterministic detection of frameworks and libraries.

    Args:
        path: The project root directory. Defaults to Config workspace_root.

    Returns:
        A JSON string containing detected frameworks by category.
    """
    try:
        path = resolve_workspace_path(path)
    except WorkspacePathError as e:
        return json.dumps({"error": str(e)})
    files = _get_struct(path)
    frameworks = _detect(files, path)
    return json.dumps(frameworks)
