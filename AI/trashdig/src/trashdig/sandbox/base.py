import subprocess
from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class Sandbox(ABC):
    """Abstract base class for tool execution sandboxes."""

    def __init__(
        self,
        workspace_dir: str,
        allowlist: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
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
        command: List[str],
        timeout: Optional[int] = None,
        cwd: Optional[str] = None,
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
