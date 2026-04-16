import sys
import shutil
import logging
from typing import List, Optional, Dict
from .base import Sandbox
from .null import NullSandbox

logger = logging.getLogger(__name__)

def get_sandbox(
    workspace_dir: str,
    allowlist: Optional[List[str]] = None,
    env: Optional[Dict[str, str]] = None,
    network: bool = True,
    require_sandbox: bool = True,
) -> Sandbox:
    """Factory function to return the appropriate sandbox implementation.

    Args:
        workspace_dir: The project root directory.
        allowlist: Additional read-only paths.
        env: Environment variables.
        network: Whether to allow network access.
        require_sandbox: If True, raises an error if a native sandbox is not found.

    Returns:
        A Sandbox instance.
    """
    if sys.platform.startswith("linux"):
        # Check if minijail0 is available
        if shutil.which("minijail0"):
            from .minijail import MinijailSandbox
            return MinijailSandbox(
                workspace_dir=workspace_dir,
                allowlist=allowlist,
                env=env,
                network=network
            )
        elif require_sandbox:
            raise RuntimeError(
                "minijail0 not found. Cannot run in a sandbox on Linux. "
                "Install 'minijail' or set 'security.require_sandbox = false' in trashdig.toml to proceed unsandboxed."
            )
    else:
        # Check for other native sandboxes here (e.g. sandbox-exec on macOS) in the future.
        if require_sandbox:
            raise RuntimeError(
                f"No native sandbox implementation available for platform: {sys.platform}. "
                "Sandboxing is required by configuration. To proceed unsandboxed, "
                "set 'security.require_sandbox = false' in trashdig.toml."
            )

        # Graceful degradation only if not required
        logger.warning(
            f"No native sandbox implementation available for platform: {sys.platform}. "
            "Falling back to NullSandbox (Unsandboxed execution)."
        )
        return NullSandbox(
            workspace_dir=workspace_dir,
            allowlist=allowlist,
            env=env,
            network=network
        )

    # Fallback to NullSandbox if it's not required
    return NullSandbox(
        workspace_dir=workspace_dir,
        allowlist=allowlist,
        env=env,
        network=network
    )
