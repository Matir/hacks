import subprocess
from abc import ABC, abstractmethod


class Sandbox(ABC):
    """Abstract base class for tool execution sandboxes."""

    def __init__(
        self,
        workspace_dir: str,
        allowlist: list[str] | None = None,
        env: dict[str, str] | None = None,
        network: bool = True,
    ):
        """Initializes the sandbox.

        Args:
            workspace_dir: The project root directory to allow write access.
            allowlist: Additional read-only paths to mount.
            env: Environment variables for the sandboxed process.
            network: Whether to allow network access.
        """
        self.workspace_dir = workspace_dir
        self.allowlist = allowlist or []
        self.env = env or {}
        self.network = network

    @abstractmethod
    def run(
        self,
        command: list[str],
        timeout: int | None = None,
        cwd: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """Runs a command inside the sandbox.

        Args:
            command: The command and its arguments.
            timeout: Execution timeout in seconds.
            cwd: The working directory inside the sandbox.

        Returns:
            A subprocess.CompletedProcess object.
        """
        pass
