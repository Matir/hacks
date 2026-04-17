import logging
import os
import subprocess
from typing import Any

from trashdig.utils import get_binary_path

from .base import Sandbox

logger = logging.getLogger(__name__)


class BxSandbox(Sandbox):
    """macOS filesystem sandbox using bx-mac.

    Uses bx's allow-first model: everything is accessible by default; sensitive
    paths outside the workspace are blocked by bx's generated sandbox profile
    (~/.ssh, ~/.gnupg, ~/Documents, ~/Downloads, password-manager containers,
    other home-directory sibling projects, etc.).

    Limitation: bx does not provide network isolation. The ``network=False``
    parameter will log a warning but is NOT enforced on macOS. For
    network-isolated execution, use ``container_bash_tool`` (Docker).

    Install bx: ``brew install holtwick/tap/bx``
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initializes the BxSandbox.

        Args:
            *args: Positional arguments forwarded to Sandbox.
            **kwargs: Keyword arguments forwarded to Sandbox.

        Raises:
            RuntimeError: If the ``bx`` binary is not found in PATH.
        """
        super().__init__(*args, **kwargs)
        bx_path = get_binary_path("bx")
        if not bx_path:
            raise RuntimeError(
                "bx not found in PATH. Install via: brew install holtwick/tap/bx"
            )
        self.bx_path: str = bx_path

    def run(
        self,
        command: list[str],
        timeout: int | None = None,
        cwd: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """Runs a command inside the bx filesystem sandbox.

        Args:
            command: The command and its arguments.
            timeout: Execution timeout in seconds.
            cwd: Working directory for the sandboxed process.

        Returns:
            A subprocess.CompletedProcess object.
        """
        if not self.network:
            logger.warning(
                "BxSandbox does not enforce network isolation on macOS. "
                "`network=False` has no effect. Use container_bash_tool "
                "when network isolation is required."
            )

        # bx exec <workdir> [<extra-workdir>...] -- <cmd>
        # Passing allowlist paths as extra workdirs ensures bx's generated
        # profile permits them even if they fall inside a normally-blocked
        # subtree (e.g. a sibling project directory).
        #
        args: list[str] = [self.bx_path, "exec", self.workspace_dir]
        args.extend(self.allowlist)
        args += ["--"]
        args.extend(command)

        logger.debug("Running in bx sandbox: %s", " ".join(args))

        # bx is a Node.js wrapper around sandbox-exec and inherits the parent
        # environment, so merge rather than replace to preserve PATH, NODE_PATH,
        # and other variables required by bx itself.
        merged_env = {**os.environ, **self.env}

        return subprocess.run(  # noqa: S603
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd or self.workspace_dir,
            env=merged_env,
            check=False,
        )
