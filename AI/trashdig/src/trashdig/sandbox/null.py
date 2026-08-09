import logging
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
        # self.env is already the complete environment (merged with the parent
        # process's and denylist-filtered by get_sandbox()) -- use it as-is
        # rather than re-merging raw os.environ, which would let filtered-out
        # secrets back in.
        return subprocess.run(  # noqa: S603
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd or self.workspace_dir,
            env=dict(self.env),
            check=False
        )
