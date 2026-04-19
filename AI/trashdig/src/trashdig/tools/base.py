import hashlib
import inspect
import logging
import os
import subprocess
from collections.abc import Callable
from functools import wraps
from typing import Any

import tree_sitter
import tree_sitter_c_sharp
import tree_sitter_go
import tree_sitter_javascript
import tree_sitter_python
from google.adk.artifacts import BaseArtifactService, FileArtifactService
from google.adk.tools import ToolContext

from trashdig.config import get_config
from trashdig.sandbox import get_sandbox
from trashdig.sandbox.base import Sandbox

logger = logging.getLogger(__name__)


def _run_sandboxed(
    command: list[str],
    timeout: int | None = None,
    network: bool = False,
    workspace_dir: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Runs a command inside a sandbox and returns its result object.

    Args:
        command: The command and its arguments.
        timeout: Execution timeout in seconds.
        network: Whether to allow network access.
        workspace_dir: The project root directory. Defaults to Config workspace_root.

    Returns:
        A subprocess.CompletedProcess object.
    """
    config = get_config()
    if workspace_dir is None:
        workspace_dir = config.workspace_root

    require_sandbox = config.data.get("require_sandbox", True)

    try:
        sandbox: Sandbox = get_sandbox(
            workspace_dir=workspace_dir,
            network=network,
            require_sandbox=require_sandbox,
        )
    except RuntimeError as e:
        return subprocess.CompletedProcess(
            args=command, returncode=1, stdout="", stderr=str(e)
        )

    try:
        return sandbox.run(command, timeout=timeout)
    except FileNotFoundError:
        return subprocess.CompletedProcess(
            args=command,
            returncode=127,
            stdout="",
            stderr=f"Error: Command '{command[0]}' not found in PATH."
        )
    except subprocess.TimeoutExpired as e:
        return subprocess.CompletedProcess(
            args=command,
            returncode=124,  # Standard timeout exit code
            stdout=e.stdout.decode() if e.stdout else "",
            stderr=e.stderr.decode() if e.stderr else "Command timed out"
        )
    except Exception as e:
        return subprocess.CompletedProcess(
            args=command,
            returncode=1,
            stdout="",
            stderr=f"Error running sandboxed command: {e}"
        )


def _get_ts_language(lang: Any) -> Any:
    """Gets the tree-sitter language object for the given language string or metadata."""
    lang_name = lang.name if hasattr(lang, "name") else str(lang).lower()

    if lang_name == "python":
        return tree_sitter.Language(tree_sitter_python.language())
    if lang_name == "go":
        return tree_sitter.Language(tree_sitter_go.language())
    if lang_name in ("javascript", "typescript", "js", "ts"):
        return tree_sitter.Language(tree_sitter_javascript.language())
    if lang_name in ("csharp", "cs"):
        return tree_sitter.Language(tree_sitter_c_sharp.language())
    return None


# Language objects are read-only after construction and safe to share across
# threads. Parser objects are NOT thread-safe (mutable C state), so we cache
# only the Language and construct a new Parser per call.
_LANGUAGE_CACHE: dict[str, tree_sitter.Language] = {}


def _make_parser(lang: Any) -> tree_sitter.Parser | None:
    """Creates a tree-sitter parser with a cached Language for the given language."""
    lang_name = lang.name if hasattr(lang, "name") else str(lang).lower()
    if lang_name not in _LANGUAGE_CACHE:
        ts_lang = _get_ts_language(lang)
        if ts_lang is None:
            return None
        _LANGUAGE_CACHE[lang_name] = ts_lang
    return tree_sitter.Parser(_LANGUAGE_CACHE[lang_name])


_artifact_service: BaseArtifactService | None = None


def init_artifact_manager(data_dir: str) -> BaseArtifactService:
    """Initializes and returns an artifact service, storing it as the singleton."""
    global _artifact_service  # noqa: PLW0603
    artifacts_dir = os.path.join(data_dir, "artifacts")
    os.makedirs(artifacts_dir, exist_ok=True)
    _artifact_service = FileArtifactService(artifacts_dir)
    return _artifact_service


def get_artifact_service() -> BaseArtifactService:
    """Returns the artifact service instance configured for the project."""
    global _artifact_service  # noqa: PLW0602
    if _artifact_service is not None:
        return _artifact_service
    config = get_config()
    return FileArtifactService(config.data_dir)


def _process_tool_result_sync(func_name: str, result: str, max_chars: int) -> str:
    """Legacy synchronous tool result processing."""
    if len(result) <= max_chars:
        return result

    # Truncate and save to a local artifact file
    filename = f"tool_{func_name}_{hashlib.sha256(result.encode()).hexdigest()[:8]}.txt"
    svc = get_artifact_service()
    base_path = getattr(svc, "base_path", None) or getattr(svc, "_base_path", None)
    if base_path is None:
        config = get_config()
        base_path = config.data_dir
    artifact_path = os.path.join(base_path, filename)
    os.makedirs(os.path.dirname(artifact_path), exist_ok=True)
    with open(artifact_path, "w", encoding="utf-8") as f:
        f.write(result)

    summary = (
        f"[TRUNCATED: Showing first {max_chars} characters]\n"
        f"Output truncated for context efficiency. Total Size: {len(result)} characters.\n"
        f"Full output saved as legacy artifact: {artifact_path}\n"
        f"{result[:max_chars]}"
    )
    return summary


async def _process_tool_result_async(
    func_name: str, result: str, max_chars: int, ctx: ToolContext
) -> str:
    """Modern asynchronous tool result processing using ADK Artifacts."""
    from google.genai import types as genai_types  # noqa: PLC0415

    if len(result) <= max_chars:
        return result

    try:
        filename = f"{func_name}_{hashlib.sha256(result.encode()).hexdigest()[:8]}.txt"
        part = genai_types.Part(text=result)
        version = await ctx.save_artifact(filename, part)
        summary = (
            f"[TRUNCATED: Showing first {max_chars} characters]\n"
            f"Output truncated for context efficiency. Total Size: {len(result)} characters.\n"
            f"Full output saved as ADK artifact: {filename}, version {version}\n"
            f"{result[:max_chars]}"
        )
        return summary
    except Exception:
        # Fallback to legacy sync save if ADK API fails
        logger.debug("ADK artifact save failed, falling back to legacy save.")

    # Fallback to legacy sync save
    return _process_tool_result_sync(func_name, result, max_chars)


def artifact_tool(max_chars: int = 5000) -> Callable:
    """Decorator for tools that might produce large output.

    Automatically handles truncation and artifact storage.
    """

    def decorator(func: Callable) -> Callable:
        if inspect.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                # Extract ToolContext if provided as a kwarg (ADK standard)
                ctx = kwargs.get("tool_context") or kwargs.get("ctx")
                result = await func(*args, **kwargs)
                if not isinstance(result, str):
                    s = str(result)
                    if len(s) <= max_chars:
                        return result
                    result = s

                if ctx and hasattr(ctx, "save_artifact"):
                    return await _process_tool_result_async(
                        func.__name__, result, max_chars, ctx
                    )
                return _process_tool_result_sync(func.__name__, result, max_chars)

            return async_wrapper
        else:

            @wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                result = func(*args, **kwargs)
                if not isinstance(result, str):
                    s = str(result)
                    if len(s) <= max_chars:
                        return result
                    result = s
                return _process_tool_result_sync(func.__name__, result, max_chars)

            return sync_wrapper

    return decorator
