import logging
import os
import subprocess
from typing import Any, List, Optional

from trashdig.utils import get_binary_path

from .base import Sandbox

logger = logging.getLogger(__name__)

class MinijailSandbox(Sandbox):
    """Linux implementation using minijail0 for process isolation."""

    DEFAULT_ALLOWLIST = [
        "/bin", "/usr", "/lib", "/lib64", "/sbin",
        "/etc/ld.so.cache", "/etc/ld.so.conf", "/etc/ld.so.conf.d",
        "/etc/resolv.conf", "/etc/nsswitch.conf", "/etc/passwd",
        "/etc/group", "/etc/hosts", "/etc/localtime",
        "/etc/ssl/certs", "/etc/ca-certificates", "/usr/share/ca-certificates",
        "/usr/share/terminfo", "/usr/lib/locale",
    ]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.minijail_path = get_binary_path("minijail0")
        if not self.minijail_path:
            raise RuntimeError("minijail0 not found in PATH.")

    def run(
        self,
        command: List[str],
        timeout: Optional[int] = None,
        cwd: Optional[str] = None,
    ) -> subprocess.CompletedProcess[str]:
        """Runs the command using minijail0.
        
        Args:
            command: The command and its arguments.
            timeout: Execution timeout in seconds.
            cwd: The working directory inside the sandbox.

        Returns:
            A subprocess.CompletedProcess object.
        """
        # Base minijail flags:
        # -v: Enter a new VFS (mount) namespace.
        # -d: Mount a minimal /dev (requires -v).
        # -p: Enter a new PID namespace.
        # -r: Remount /proc read-only (matches the PID namespace).
        # -t: Mount a private tmpfs on /tmp.
        # -u, -g: Run as current user/group (requires unprivileged namespaces).
        # -U: Enter a new user namespace (allows -v, -p as non-root).
        assert self.minijail_path is not None
        args: List[str] = [
            self.minijail_path,
            "-v", "-d", "-p", "-r", "-t", "-U"
        ]

        # Disable network if requested (-e: Enter a new network namespace)
        if not self.network:
            args.append("-e")

        # Map current user/group
        uid = os.getuid()
        gid = os.getgid()
        args.extend(["-u", str(uid), "-g", str(gid)])

        # Mount workspace as writable
        # -b /path/to/src,/path/to/dest,1 (the '1' makes it writable)
        # Note: In Minijail, multiple -b flags are used for bind mounts.
        args.extend(["-b", f"{self.workspace_dir},{self.workspace_dir},1"])

        # Mount default allowlist (read-only)
        for path in self.DEFAULT_ALLOWLIST:
            if os.path.exists(path):
                args.extend(["-b", f"{path},{path},0"])

        # Mount additional allowlisted paths
        for path in self.allowlist:
            if os.path.exists(path):
                args.extend(["-b", f"{path},{path},0"])

        # Add the command to run
        args.append("--")
        args.extend(command)

        logger.debug(f"Running in Minijail: {' '.join(args)}")

        return subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd or self.workspace_dir,
            env=self.env,
            check=False
        )
