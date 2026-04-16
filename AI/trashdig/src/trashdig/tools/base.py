import re
import subprocess
import os
import json
import hashlib
import inspect
from datetime import datetime
from typing import List, Optional, Any, Dict, Set, Tuple, Callable
from functools import wraps
from google.adk.artifacts import BaseArtifactService, FileArtifactService
from google.genai import types
from ..sandbox import get_sandbox
from ..config import get_config

# ---------------------------------------------------------------------------
# Artifact System
# ---------------------------------------------------------------------------

_ARTIFACT_SERVICE: Optional[BaseArtifactService] = None

def init_artifact_manager(data_dir: Optional[str] = None) -> BaseArtifactService:
    """Initializes the artifact service based on the global data directory.

    Args:
        data_dir: The global data directory. Defaults to config value.
    
    Returns:
        The initialized BaseArtifactService.
    """
    global _ARTIFACT_SERVICE
    if data_dir is None:
        data_dir = get_config().data_dir
        
    artifact_dir = os.path.join(data_dir, "artifacts")
    os.makedirs(artifact_dir, exist_ok=True)
    _ARTIFACT_SERVICE = FileArtifactService(root_dir=artifact_dir)
    return _ARTIFACT_SERVICE

def get_artifact_service() -> Optional[BaseArtifactService]:
    """Returns the initialized BaseArtifactService, if any."""
    return _ARTIFACT_SERVICE

def _process_tool_result_sync(func_name: str, result: Any, max_chars: int) -> str:
    """Synchronous version of _process_tool_result for legacy/internal use."""
    if not isinstance(result, str) or len(result) <= max_chars:
        return result

    global _ARTIFACT_SERVICE
    artifact_dir = get_config().resolve_data_path("artifacts")
    if isinstance(_ARTIFACT_SERVICE, FileArtifactService):
        artifact_dir = str(_ARTIFACT_SERVICE.root_dir)

    content_hash = hashlib.sha256(result.encode("utf-8")).hexdigest()[:12]
    filename = f"{func_name}_{content_hash}.txt"
    artifact_path = os.path.join(artifact_dir, filename)

    os.makedirs(artifact_dir, exist_ok=True)
    with open(artifact_path, "w", encoding="utf-8") as f:
        f.write(result)

    summary = (
        f"[TRUNCATED: Showing first {max_chars} characters]\n"
        f"{result[:max_chars]}\n"
        f"---\n"
        f"Output truncated for context efficiency.\n"
        f"Full output saved as legacy artifact: {artifact_path}\n"
        f"Total Size: {len(result)} characters.\n"
        f"To see more, use: 'read_file' on the artifact path."
    )
    return summary

async def _process_tool_result(func_name: str, result: Any, max_chars: int, tool_context: Any = None) -> str:
    """Internal helper to process a tool result and create an artifact if needed.

    Args:
        func_name: Name of the tool function.
        result: The raw result from the tool.
        max_chars: Threshold for truncation.
        tool_context: The ADK ToolContext (Context).

    Returns:
        The processed (potentially truncated) result string.
    """
    if not isinstance(result, str) or len(result) <= max_chars:
        return result

    # If we have a tool_context and an artifact service, use the ADK API
    if tool_context and hasattr(tool_context, "save_artifact"):
        try:
            content_hash = hashlib.sha256(result.encode("utf-8")).hexdigest()[:12]
            filename = f"{func_name}_{content_hash}.txt"
            
            # Save the artifact using ADK API
            artifact_part = types.Part.from_text(text=result)
            version = await tool_context.save_artifact(filename, artifact_part)
            
            # Construct a summary response with the artifact reference
            summary = (
                f"[TRUNCATED: Showing first {max_chars} characters]\n"
                f"{result[:max_chars]}\n"
                f"---\n"
                f"Output truncated for context efficiency.\n"
                f"Full output saved as ADK artifact: {filename} (version {version})\n"
                f"Total Size: {len(result)} characters.\n"
                f"To see more, use the 'load_artifacts' tool with name: '{filename}'"
            )
            return summary
        except Exception:
            # Fallback to legacy sync save if ADK API fails
            pass

    # Fallback to legacy sync save
    return _process_tool_result_sync(func_name, result, max_chars)

def artifact_tool(max_chars: int = 5000) -> Callable:
    """A decorator that automatically saves large tool outputs as artifacts.

    Supports both synchronous and asynchronous functions. It automatically
    detects if a 'tool_context' argument is provided to use the ADK Artifact API.

    Args:
        max_chars: Threshold for truncation and artifact creation.

    Returns:
        The decorated tool function.
    """
    def decorator(func: Callable) -> Callable:
        sig = inspect.signature(func)
        has_context = "tool_context" in sig.parameters

        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> str:
                result = await func(*args, **kwargs)
                ctx = kwargs.get("tool_context")
                if ctx is None and has_context:
                    ctx_idx = list(sig.parameters.keys()).index("tool_context")
                    if len(args) > ctx_idx:
                        ctx = args[ctx_idx]
                
                return await _process_tool_result(func.__name__, result, max_chars, tool_context=ctx)
            return async_wrapper
        else:
            @wraps(func)
            def hybrid_wrapper(*args: Any, **kwargs: Any) -> Any:
                # If the tool is sync, we run it first.
                result = func(*args, **kwargs)
                ctx = kwargs.get("tool_context")
                if ctx is None and has_context:
                    ctx_idx = list(sig.parameters.keys()).index("tool_context")
                    if len(args) > ctx_idx:
                        ctx = args[ctx_idx]
                
                if ctx is not None:
                    # Return a coroutine so FunctionTool can await it
                    return _process_tool_result(func.__name__, result, max_chars, tool_context=ctx)
                else:
                    # Return string directly for sync internal use
                    return _process_tool_result_sync(func.__name__, result, max_chars)
            return hybrid_wrapper
    return decorator

def _run_sandboxed(
    command: List[str],
    timeout: Optional[int] = None,
    network: bool = False,
    workspace_dir: Optional[str] = None
) -> subprocess.CompletedProcess[str]:
    """Internal helper to run a command in the configured sandbox.

    Args:
        command: The command to execute.
        timeout: Execution timeout in seconds.
        network: Whether to allow network access. Defaults to False for safety.
        workspace_dir: Optional override for the sandbox root. Defaults to os.getcwd().

    Returns:
        The subprocess result.
    """
    cfg = get_config()
    actual_workspace = workspace_dir or os.getcwd()
    require_sandbox = cfg.require_sandbox
    
    sandbox = get_sandbox(
        workspace_dir=actual_workspace,
        env=os.environ.copy(),
        network=network,
        require_sandbox=require_sandbox
    )
    try:
        return sandbox.run(command, timeout=timeout)
    except FileNotFoundError:
        # Return a mock-like object that indicates failure
        return subprocess.CompletedProcess(
            args=command,
            returncode=127,
            stdout="",
            stderr=f"Error: {command[0]} not found in PATH."
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(
            args=command,
            returncode=124,
            stdout="",
            stderr=f"Error: {command[0]} scan timed out."
        )

def _get_ts_language(language: str) -> Any:
    """Helper to get tree-sitter Language objects.

    Args:
        language: Programming language string.

    Returns:
        A ``tree_sitter.Language`` instance or ``None`` if not supported.
    """
    import tree_sitter
    import tree_sitter_python
    import tree_sitter_javascript
    import tree_sitter_go
    import tree_sitter_c_sharp

    capsules = {
        "python": tree_sitter_python.language(),
        "javascript": tree_sitter_javascript.language(),
        "go": tree_sitter_go.language(),
        "csharp": tree_sitter_c_sharp.language(),
    }
    capsule = capsules.get(language)
    return tree_sitter.Language(capsule) if capsule is not None else None


def _make_parser(language: str) -> Any:
    """Return a ready-to-use ``tree_sitter.Parser`` for *language*, or ``None``.

    Args:
        language: Programming language string (python, javascript, go, csharp).

    Returns:
        A configured ``tree_sitter.Parser`` or ``None`` if unsupported.
    """
    import tree_sitter
    lang = _get_ts_language(language)
    if lang is None:
        return None
    return tree_sitter.Parser(lang)
