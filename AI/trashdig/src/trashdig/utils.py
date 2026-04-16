import shutil
from typing import Dict, Optional

_BINARY_STUBS: Dict[str, bool] = {}

def is_binary_available(name: str) -> bool:
    """Checks if a binary is available on the system.
    Supports stubs for testing.

    Args:
        name: The name of the binary (e.g., 'minijail0', 'docker').

    Returns:
        True if the binary is available or stubbed as available.
    """
    if name in _BINARY_STUBS:
        return _BINARY_STUBS[name]
    return shutil.which(name) is not None

def get_binary_path(name: str) -> Optional[str]:
    """Gets the path to a binary.
    Supports stubs for testing.

    Args:
        name: The name of the binary.

    Returns:
        The path to the binary, or a stubbed path, or None if not found.
    """
    if name in _BINARY_STUBS:
        return f"/stub/bin/{name}" if _BINARY_STUBS[name] else None
    return shutil.which(name)

def set_binary_stub(name: str, available: bool) -> None:
    """Sets a stub for a binary availability check.
    Only intended for use in tests.

    Args:
        name: The name of the binary.
        available: Whether the binary should be reported as available.
    """
    _BINARY_STUBS[name] = available

def clear_binary_stubs() -> None:
    """Clears all binary stubs.
    Only intended for use in tests.
    """
    _BINARY_STUBS.clear()
