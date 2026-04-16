import hashlib
import inspect
import logging
import os
import time
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

logger = logging.getLogger(__name__)


def _get_ts_language(lang: str) -> Any:
    """Gets the tree-sitter language object for the given language string."""
    lang = lang.lower()
    if lang == "python":
        return tree_sitter.Language(tree_sitter_python.language())
    if lang == "go":
        return tree_sitter.Language(tree_sitter_go.language())
    if lang in ("javascript", "typescript", "js", "ts"):
        return tree_sitter.Language(tree_sitter_javascript.language())
    if lang in ("csharp", "cs"):
        return tree_sitter.Language(tree_sitter_c_sharp.language())
    return None


def get_artifact_service() -> BaseArtifactService:
    """Returns the artifact service instance configured for the project."""
    config = get_config()
    return FileArtifactService(config.data_dir)


def _process_tool_result_sync(func_name: str, result: str, max_chars: int) -> str:
    """Legacy synchronous tool result processing."""
    if len(result) <= max_chars:
        return result

    # Truncate and save to a local artifact file
    config = get_config()
    filename = f"tool_{func_name}_{hashlib.sha256(result.encode()).hexdigest()[:8]}.txt"
    artifact_path = os.path.join(config.data_dir, filename)
    os.makedirs(config.data_dir, exist_ok=True)
    with open(artifact_path, "w", encoding="utf-8") as f:
        f.write(result)

    summary = (
        f"[TRUNCATED] Output too large ({len(result)} chars). "
        f"Full output saved to: {artifact_path}\n"
        f"Showing first {max_chars // 2} chars:\n"
        f"{result[:max_chars // 2]}\n"
        f"...\n"
        f"Showing last {max_chars // 2} chars:\n"
        f"{result[-max_chars // 2:]}"
    )
    return summary


async def _process_tool_result_async(
    func_name: str, result: str, max_chars: int, ctx: ToolContext
) -> str:
    """Modern asynchronous tool result processing using ADK Artifacts."""
    if len(result) <= max_chars:
        return result

    # Check for artifact service in context
    art_service = getattr(ctx, "artifact_service", None)
    if art_service:
        try:
            filename = f"tool_{func_name}_{int(time.time())}_{hashlib.sha256(result.encode()).hexdigest()[:8]}.txt"
            # Use ADK Artifact API
            await art_service.create_artifact(filename, result.encode("utf-8"))
            summary = (
                f"[TRUNCATED] Output too large ({len(result)} chars). "
                f"Full output available via artifact: '{filename}'\n"
                f"Showing first {max_chars // 2} chars:\n"
                f"{result[:max_chars // 2]}\n"
                f"...\n"
                f"Showing last {max_chars // 2} chars:\n"
                f"{result[-max_chars // 2:]}\n"
                f"To see more, use the 'load_artifacts' tool with name: '{filename}'"
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
            async def async_wrapper(*args: Any, **kwargs: Any) -> str:
                # Extract ToolContext if provided as a kwarg (ADK standard)
                ctx = kwargs.get("ctx")
                result = await func(*args, **kwargs)
                if not isinstance(result, str):
                    result = str(result)

                if ctx and isinstance(ctx, ToolContext):
                    return await _process_tool_result_async(
                        func.__name__, result, max_chars, ctx
                    )
                return _process_tool_result_sync(func.__name__, result, max_chars)

            return async_wrapper
        else:

            @wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> str:
                result = func(*args, **kwargs)
                if not isinstance(result, str):
                    result = str(result)
                return _process_tool_result_sync(func.__name__, result, max_chars)

            return sync_wrapper

    return decorator
