"""Landlock filesystem sandbox decorator for Python-native tool functions.

This module provides a :func:`landlock_tool` decorator that wraps synchronous
Python tool functions to run in a forked child process with Linux Landlock
filesystem restrictions applied.

Usage::

    @artifact_tool(max_chars=4000)
    @landlock_tool()
    def read_file(file_path: str, tool_context: Any = None) -> str: ...

On non-Linux platforms or when the ``TRASHDIG_SKIP_SANDBOX`` environment
variable is set to ``"1"``, the function is called directly in the current
process (no child is spawned).  Set ``require_sandbox = true`` in
``trashdig.toml`` (the default) to make Landlock unavailability a hard failure
on Linux rather than a silent fall-through to unsandboxed execution.

The decorator must sit **inside** ``@artifact_tool`` so that
:class:`~google.adk.tools.ToolContext` is consumed by the outer decorator and
never forwarded to the child (``ToolContext`` is not picklable).
"""

import inspect
import logging
import multiprocessing
import multiprocessing.connection
import os
import platform
import sys
import traceback
from collections.abc import Callable
from functools import wraps
from typing import Any

from trashdig.config import get_config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level multiprocessing context.
#
# Initialised with ``forkserver`` as the default; replaced by
# :func:`init_sandbox_mp_context` at application startup.  Using a module-
# level context object (rather than ``multiprocessing.set_start_method``)
# avoids touching the global default and lets tests override the method to
# ``spawn`` without needing a live forkserver.
# ---------------------------------------------------------------------------
_mp_context: Any = multiprocessing.get_context("forkserver")

# Snapshot of ``sys.path`` at context-init time.  Passed to every child so
# that Landlock can allow the paths needed for Python imports.
_sys_path_snapshot: list[str] = list(sys.path)


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------


class SandboxError(RuntimeError):
    """Raised when a sandboxed child process terminates abnormally."""

    def __init__(self, func_name: str, exitcode: int, stderr: str = "") -> None:
        """Initialise SandboxError.

        Args:
            func_name: Name of the sandboxed tool function.
            exitcode: Exit code returned (or signalled) by the child process.
            stderr: Any stderr text captured before the abnormal exit.
        """
        msg = f"{func_name} sandbox child exited with code {exitcode}"
        if stderr:
            msg += f"\n{stderr}"
        super().__init__(msg)


class ToolTimeoutError(SandboxError):
    """Raised when a sandboxed tool call exceeds its per-call time limit."""

    def __init__(self, func_name: str, timeout: int) -> None:
        """Initialise ToolTimeoutError.

        Args:
            func_name: Name of the sandboxed tool function.
            timeout: Timeout in seconds that was exceeded.
        """
        # Bypass SandboxError.__init__ to provide a different message format.
        RuntimeError.__init__(self, f"{func_name} sandbox child timed out after {timeout}s")
        self.timeout = timeout


# ---------------------------------------------------------------------------
# Startup hook
# ---------------------------------------------------------------------------


def init_sandbox_mp_context(method: str = "forkserver") -> None:
    """Initialise the multiprocessing start method used for sandboxed calls.

    Must be called **once** at application startup, after
    :func:`~trashdig.config.load_config` but before any threads are spawned
    (i.e. before ``asyncio.run()`` or ``app.run()``).  Using ``forkserver``
    avoids fork-after-thread deadlocks in the multithreaded main process.

    In tests, call with ``method='spawn'`` to obtain a clean interpreter per
    call without needing a pre-started forkserver process.

    Args:
        method: One of ``'forkserver'``, ``'spawn'``, or ``'fork'``.
    """
    global _mp_context, _sys_path_snapshot  # noqa: PLW0603
    _mp_context = multiprocessing.get_context(method)
    _sys_path_snapshot = list(sys.path)


# ---------------------------------------------------------------------------
# Child-process helpers
# ---------------------------------------------------------------------------


def _apply_landlock_rules(  # noqa: C901
    workspace_dir: str,
    extra_paths: list[str],
    write: bool,
    sys_path_snap: list[str],
) -> None:
    """Apply a Landlock filesystem ruleset in the current (child) process.

    This function is irreversible once called.  It restricts the process to
    the allowed paths listed in ``landlock_sandbox_tools.md``.

    Args:
        workspace_dir: Project root directory (read-only or read+write).
        extra_paths: Additional read-only paths beyond the workspace.
        write: If ``True``, grant read+write access to *workspace_dir*.
        sys_path_snap: ``sys.path`` snapshot captured at context-init time.

    Raises:
        ImportError: If the ``landlock`` package is not installed.
        RuntimeError: If the Landlock ruleset cannot be created or applied.
    """
    # Deferred import: only runs in the child process on Linux.
    # The import is here (not at module top) so that the package absence or
    # kernel incompatibility is detected at call time inside the child,
    # allowing the parent wrapper to handle it gracefully.
    from landlock import FSAccess, Ruleset  # noqa: PLC0415

    read_only = FSAccess.READ_FILE | FSAccess.READ_DIR
    read_write = FSAccess.all()
    tmp_access = (
        FSAccess.READ_FILE
        | FSAccess.WRITE_FILE
        | FSAccess.READ_DIR
        | FSAccess.MAKE_DIR
        | FSAccess.REMOVE_DIR
        | FSAccess.MAKE_REG
        | FSAccess.REMOVE_FILE
    )

    rs = Ruleset()

    # Project workspace
    if os.path.exists(workspace_dir):
        rs.allow(workspace_dir, rules=read_write if write else read_only)

    # Caller-declared extra paths (always read-only)
    for path in extra_paths:
        if path and os.path.exists(path):
            rs.allow(path, rules=read_only)

    # Python runtime: interpreter, stdlib, active venv
    for prefix in {sys.prefix, sys.exec_prefix}:
        if prefix and os.path.exists(prefix):
            rs.allow(prefix, rules=read_only)

    # Installed packages and project source tree (for in-child imports)
    for p in sys_path_snap:
        if p and os.path.exists(p):
            rs.allow(p, rules=read_only)

    # /proc/self — required by ctypes and various subprocess internals
    if os.path.exists("/proc/self"):
        rs.allow("/proc/self", rules=read_only)

    # /tmp — writable scratch space
    if os.path.exists("/tmp"):  # noqa: S108
        rs.allow("/tmp", rules=tmp_access)  # noqa: S108

    # /dev — device files: /dev/null, /dev/urandom, /dev/random
    if os.path.exists("/dev"):
        rs.allow("/dev", rules=read_only)

    rs.apply()


def _send_error(
    conn: "multiprocessing.connection.Connection",
    exc: BaseException,
    tb_str: str,
) -> None:
    """Send an error payload through the IPC pipe with a pickling fallback.

    If *exc* itself is not picklable (e.g. it holds a non-picklable object
    such as a tree-sitter node), a ``RuntimeError`` string representation is
    sent instead.

    Args:
        conn: Write-end of a ``multiprocessing.Pipe``.
        exc: The exception to transmit.
        tb_str: Formatted traceback string for debug logging on the parent side.
    """
    try:
        conn.send(("err", exc, tb_str))
    except Exception:
        conn.send(("err", RuntimeError(f"{type(exc).__name__}: {exc}"), tb_str))


def _child_main(  # noqa: PLR0913
    conn: "multiprocessing.connection.Connection",
    func: Callable[..., Any],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    workspace_dir: str,
    extra_paths: list[str],
    write: bool,
    sys_path_snap: list[str],
    require_sandbox: bool,
) -> None:
    """Entry point executed inside the sandboxed child process.

    Applies Landlock (Linux only), calls *func*, then sends the result or
    exception back through *conn*.

    Args:
        conn: Write-end of a ``multiprocessing.Pipe``.
        func: The tool function to execute.
        args: Positional arguments (``tool_context`` already stripped).
        kwargs: Keyword arguments (``tool_context`` already stripped).
        workspace_dir: Project root directory passed to Landlock.
        extra_paths: Additional read-only paths beyond the workspace.
        write: Whether *workspace_dir* needs read+write access.
        sys_path_snap: ``sys.path`` snapshot for in-child import access.
        require_sandbox: Whether to hard-fail if Landlock cannot be applied.
    """
    # Must be set before Landlock is applied (env mutation is not a FS op).
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

    # Apply Landlock on Linux only.  On other platforms the child runs with
    # an unrestricted filesystem but still provides subprocess isolation.
    if platform.system() == "Linux":
        try:
            _apply_landlock_rules(workspace_dir, extra_paths, write, sys_path_snap)
        except ImportError as exc:
            if require_sandbox:
                _send_error(conn, exc, traceback.format_exc())
                return
            logger.warning(
                "%s: python-landlock not installed; running unsandboxed",
                func.__name__,
            )
        except Exception as exc:
            if require_sandbox:
                _send_error(conn, exc, traceback.format_exc())
                return
            logger.warning(
                "%s: Landlock unavailable (%s); running unsandboxed",
                func.__name__,
                exc,
            )

    # Execute the tool function and send the result back.
    try:
        result = func(*args, **kwargs)
    except Exception as exc:
        _send_error(conn, exc, traceback.format_exc())
        return

    try:
        conn.send(("ok", result))
    except Exception:
        # result is not picklable — fall back to its string representation.
        conn.send(("ok", str(result)))


# ---------------------------------------------------------------------------
# Public decorator
# ---------------------------------------------------------------------------


def landlock_tool(
    extra_paths: list[str] | None = None,
    timeout: int = 30,
    write: bool = False,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Wrap a synchronous tool function to run in a sandboxed child process.

    On Linux (kernel ≥ 5.13) the child has Landlock filesystem restrictions
    applied, confining it to the project workspace, the Python runtime, and a
    small set of system paths.  On non-Linux platforms the child runs
    unrestricted (sandboxing is a no-op there).

    Place this decorator **inside** ``@artifact_tool`` so that
    :class:`~google.adk.tools.ToolContext` is handled by the outer decorator
    and is never forwarded into the unpicklable child::

        @artifact_tool(max_chars=4000)
        @landlock_tool()
        def read_file(file_path: str, tool_context: Any = None) -> str: ...

    When the ``TRASHDIG_SKIP_SANDBOX`` environment variable is ``"1"`` the
    function is called directly in the current process — this is the fast path
    used by the test suite.

    Args:
        extra_paths: Additional read-only paths to allow beyond the workspace
            and Python runtime.  Evaluated at call time; defaults to ``[]``.
        timeout: Per-call timeout in seconds before ``ToolTimeoutError`` is
            raised and the child is killed.  Defaults to 30.
        write: If ``True``, grant read+write access to the workspace root.
            Defaults to ``False`` (read-only).  Only set this for tools that
            explicitly modify workspace files.

    Returns:
        A decorator that wraps the target function with subprocess sandboxing.

    Raises:
        TypeError: If applied to a coroutine (async def) function.
    """
    resolved_extra: list[str] = list(extra_paths or [])

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        """Apply the landlock subprocess wrapper to *func*."""
        if inspect.iscoroutinefunction(func):
            raise TypeError(
                f"@landlock_tool cannot be applied to the coroutine function"
                f" {func.__name__!r}. "
                "Wrap it with loop.run_in_executor() for async support."
            )

        # When `spawn` or `forkserver` start methods are used, the target
        # function passed to the child process must be pickle-able by name.
        # Standard Python pickle does this by resolving <module>.<qualname>.
        # After decoration, this would return the wrapper rather than the
        # original function, causing a PicklingError.  Fix: stash the original
        # under a unique module attribute derived from its qualified name, then
        # update func.__qualname__ to match so pickle can find it in the
        # child's reimported module.  The child mirrors the same stash on
        # re-import, giving the lookup a stable target across process restarts.
        _orig_qualname: str = func.__qualname__
        _stash_attr: str = f"__landlock_orig_{_orig_qualname.replace('.', '__')}"
        _func_module = sys.modules.get(func.__module__)
        if _func_module is not None:
            setattr(_func_module, _stash_attr, func)
            func.__qualname__ = _stash_attr  # pickle now resolves to the stashed original

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            """Execute *func* in a sandboxed child process.

            Returns:
                The return value of *func*.

            Raises:
                ToolTimeoutError: If the child exceeds *timeout* seconds.
                SandboxError: If the child terminates abnormally.
            """
            # Fast path: skip subprocess sandboxing entirely for tests.
            if os.environ.get("TRASHDIG_SKIP_SANDBOX") == "1":
                return func(*args, **kwargs)

            # Resolve runtime config in the parent before forking.
            config = get_config()
            workspace_dir: str = config.workspace_root
            require_sandbox: bool = bool(config.data.get("require_sandbox", True))

            # Strip ToolContext: not picklable and not used in tool function bodies.
            clean_kwargs: dict[str, Any] = {
                k: v for k, v in kwargs.items() if k not in ("tool_context", "ctx")
            }

            parent_conn, child_conn = _mp_context.Pipe(duplex=False)
            child = _mp_context.Process(
                target=_child_main,
                args=(
                    child_conn,
                    func,
                    args,
                    clean_kwargs,
                    workspace_dir,
                    resolved_extra,
                    write,
                    _sys_path_snapshot,
                    require_sandbox,
                ),
                daemon=True,
            )
            try:
                child.start()
            except Exception:
                # child.start() can fail with PicklingError or resource errors.
                # Close both ends to avoid leaking the pipe file descriptors.
                child_conn.close()
                parent_conn.close()
                raise
            # Parent closes its write-end immediately so that when the child
            # exits the pipe EOF is detectable via recv() raising EOFError.
            child_conn.close()

            # Read BEFORE join — if the child writes more than ~64 KB and we
            # call join() first, both sides block (pipe-buffer deadlock).
            if not parent_conn.poll(timeout):
                child.kill()
                child.join()
                raise ToolTimeoutError(func.__name__, timeout)

            try:
                message = parent_conn.recv()
            except EOFError:
                child.join()
                raise SandboxError(func.__name__, child.exitcode or -1) from None
            finally:
                parent_conn.close()

            child.join()

            tag, *payload = message
            if tag == "ok":
                return payload[0]

            exc, tb_str = payload
            logger.debug("sandbox child traceback:\n%s", tb_str)
            raise exc  # re-raise the original exception from the child

        # @wraps copied func.__qualname__ (the stash name) onto wrapper.
        # Restore the public-facing qualname so tracebacks and repr show the
        # original function name rather than the mangled stash attribute.
        wrapper.__qualname__ = _orig_qualname
        return wrapper

    return decorator


__all__ = [
    "SandboxError",
    "ToolTimeoutError",
    "init_sandbox_mp_context",
    "landlock_tool",
]
