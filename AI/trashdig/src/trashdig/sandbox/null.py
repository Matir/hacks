import logging
import os
import subprocess

from .base import Sandbox

logger = logging.getLogger(__name__)

class NullSandbox(Sandbox):
    """Fallback implementation that performs no sandboxing."""

    def run(
        self,
        command: list[str],
        timeout: int | None = None,
        cwd: str | None = None,
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
            "!!! RUNNING COMMAND UNSANDBOXED !!! Command: %s",
            " ".join(command)
        )
        return subprocess.run(  # noqa: S603
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd or self.workspace_dir,
            env={**os.environ, **self.env},
            check=False
        )
