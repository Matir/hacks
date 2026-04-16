import json

from ..agents.utils import detect_frameworks as _detect
from ..agents.utils import get_project_structure as _get_struct


def detect_frameworks(path: str = ".") -> str:
    """Performs deterministic detection of frameworks and libraries.

    Args:
        path: The project root directory.

    Returns:
        A JSON string containing detected frameworks by category.
    """
    files = _get_struct(path)
    frameworks = _detect(files, path)
    return json.dumps(frameworks)
