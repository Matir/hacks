"""TrashDig sandbox package."""

import logging
import os
import sys

from trashdig.sandbox.base import Sandbox
from trashdig.sandbox.landlock_tool import (
    SandboxError,
    ToolTimeoutError,
    init_sandbox_mp_context,
    landlock_tool,
)
from trashdig.sandbox.null import NullSandbox

logger = logging.getLogger(__name__)


def get_sandbox(
    workspace_dir: str,
    network: bool = False,
    require_sandbox: bool = True,
    allowlist: list[str] | None = None,
) -> Sandbox:
    """Returns the appropriate sandbox for the current platform.

    On Linux, uses MinijailSandbox. On macOS, uses BxSandbox (requires
    ``bx`` in PATH). Falls back to NullSandbox when ``require_sandbox``
    is False and no native sandbox is available.

    Args:
        workspace_dir: The project root directory.
        network: Whether to allow network access.
        require_sandbox: Whether to raise on sandbox unavailability.
        allowlist: Additional paths to permit inside the sandbox.

    Returns:
        A Sandbox instance appropriate for the current platform.

    Raises:
        RuntimeError: If ``require_sandbox`` is True and no sandbox
            implementation is available or initializable.
    """
    allowlist = allowlist or []

    if os.environ.get("TRASHDIG_SKIP_SANDBOX") == "1":
        return NullSandbox(workspace_dir=workspace_dir, network=network, allowlist=allowlist)

    if sys.platform == "linux":
        from trashdig.sandbox.minijail import MinijailSandbox  # noqa: PLC0415

        try:
            return MinijailSandbox(
                workspace_dir=workspace_dir, network=network, allowlist=allowlist
            )
        except Exception as e:
            if require_sandbox:
                raise RuntimeError(
                    f"Sandbox required but MinijailSandbox failed to initialize: {e}"
                ) from e
            logger.warning(
                "MinijailSandbox failed to initialize, falling back to NullSandbox: %s", e
            )

    elif sys.platform == "darwin":
        # BxSandbox is imported here rather than at module level because it is
        # macOS-only; importing it unconditionally would fail on Linux where bx
        # is irrelevant.
        try:
            from trashdig.sandbox.bx import BxSandbox  # noqa: PLC0415

            return BxSandbox(workspace_dir=workspace_dir, network=network, allowlist=allowlist)
        except RuntimeError as e:
            if require_sandbox:
                raise RuntimeError(f"Sandbox required but BxSandbox not available: {e}") from e
            logger.warning("BxSandbox not available, falling back to NullSandbox: %s", e)

    else:
        msg = (
            "No native sandbox implementation available for this platform. "
            "Set require_sandbox = false in trashdig.toml or use Linux/macOS."
        )
        if require_sandbox:
            raise RuntimeError(msg)
        logger.warning(msg)

    return NullSandbox(workspace_dir=workspace_dir, network=network, allowlist=allowlist)


__all__ = [
    "Sandbox",
    "NullSandbox",
    "SandboxError",
    "ToolTimeoutError",
    "get_sandbox",
    "init_sandbox_mp_context",
    "landlock_tool",
]
