import subprocess
import logging
from typing import List, Optional, Dict
from .base import Sandbox

logger = logging.getLogger(__name__)

class NullSandbox(Sandbox):
    """Fallback implementation that performs no sandboxing."""

    def run(
        self,
        command: List[str],
        timeout: Optional[int] = None,
        cwd: Optional[str] = None,
    ) -> subprocess.CompletedProcess[str]:
        """Runs the command on the host without any isolation.

        Args:
            command: The command and its arguments.
            timeout: Execution timeout in seconds.
            cwd: The working directory inside the sandbox.

        Returns:
            A subprocess.CompletedProcess object.
        """
        logger.warning(
            f"!!! RUNNING COMMAND UNSANDBOXED !!! "
            f"Command: {' '.join(command)}"
        )
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd or self.workspace_dir,
            env=self.env,
            check=False
        )
