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
from .sandbox import get_sandbox
from .config import get_config

# ---------------------------------------------------------------------------
# Artifact System
# ---------------------------------------------------------------------------

_ARTIFACT_SERVICE: Optional[BaseArtifactService] = None

def init_artifact_manager(data_dir: str) -> BaseArtifactService:
    """Initializes the artifact service based on the global data directory.

    Args:
        data_dir: The global data directory (e.g., '.trashdig').
    
    Returns:
        The initialized BaseArtifactService.
    """
    global _ARTIFACT_SERVICE
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
    artifact_dir = ".trashdig/artifacts"
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

def artifact_tool(max_chars: int = 5000):
    """A decorator that automatically saves large tool outputs as artifacts.

    Supports both synchronous and asynchronous functions. It automatically
    detects if a 'tool_context' argument is provided to use the ADK Artifact API.

    Args:
        max_chars: Threshold for truncation and artifact creation.

    Returns:
        The decorated tool function.
    """
    def decorator(func: Callable):
        sig = inspect.signature(func)
        has_context = "tool_context" in sig.parameters

        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs) -> str:
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
            def hybrid_wrapper(*args, **kwargs) -> Any:
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

# ---------------------------------------------------------------------------
# Client Tools
# ---------------------------------------------------------------------------

def _run_sandboxed(command: List[str], timeout: Optional[int] = None, network: bool = True) -> subprocess.CompletedProcess[str]:
    """Internal helper to run a command in the configured sandbox.

    Args:
        command: The command to execute.
        timeout: Execution timeout in seconds.
        network: Whether to allow network access.

    Returns:
        The subprocess result.
    """
    cfg = get_config()
    workspace_dir = os.getcwd() # Or get from config if implemented
    require_sandbox = cfg.require_sandbox
    
    sandbox = get_sandbox(
        workspace_dir=workspace_dir,
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

@artifact_tool(max_chars=4000)
def read_file(file_path: str, tool_context: Any = None) -> str:
    """Reads the complete content of a file.

    Args:
        file_path: Path to the file to read.
        tool_context: ADK context (injected).

    Returns:
        The file content or an error message.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file {file_path}: {str(e)}"

@artifact_tool(max_chars=4000)
def ripgrep_search(pattern: str, path: str = ".", extra_args: Optional[List[str]] = None, tool_context: Any = None) -> str:
    """Performs a fast textual search across the codebase using ripgrep.

    Args:
        pattern: The regex pattern to search for.
        path: The directory or file to search in.
        extra_args: Additional arguments to pass to rg (e.g., ["-i", "-A", "2"]).
        tool_context: ADK context (injected).

    Returns:
        The standard output of the ripgrep command.
    """
    cmd = ["rg", "--column", "--line-number", "--no-heading", "--color", "never", pattern, path]
    if extra_args:
        cmd.extend(extra_args)
    
    result = _run_sandboxed(cmd, network=False)
    # The existing tests expect specific error messages if rg is not found
    if result.returncode == 127:
        return result.stderr
    return result.stdout if result.stdout else result.stderr

@artifact_tool(max_chars=8000)
def semgrep_scan(path: str = ".", config: str = "p/security-audit", tool_context: Any = None) -> str:
    """Scans the codebase for security patterns using semgrep.

    Args:
        path: The directory or file to scan.
        config: The semgrep configuration/rules to use (e.g., "p/security-audit", "p/python").
        tool_context: ADK context (injected).

    Returns:
        The JSON output of the semgrep scan as a string.
    """
    cmd = ["semgrep", "--json", "--config", config, path]
    
    # Run semgrep with a timeout to avoid hanging
    result = _run_sandboxed(cmd, timeout=120, network=True)
    if result.returncode == 124:
        return result.stderr
    return result.stdout if result.stdout else result.stderr

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

@artifact_tool(max_chars=5000)
def get_ast_summary(file_path: str, language: str = "python", tool_context: Any = None) -> str:
    """Generates a simplified AST summary of a file using tree-sitter.

    Args:
        file_path: Path to the file to analyze.
        language: Programming language of the file (python, javascript, go, csharp).
        tool_context: ADK context (injected).

    Returns:
        A text representation of the top-level AST nodes (functions, classes, etc.).
    """
    ts_lang = _get_ts_language(language)

    if not ts_lang:
        return f"Error: Language '{language}' not supported for AST analysis."

    try:
        with open(file_path, "rb") as f:
            content = f.read()

        parser = _make_parser(language)
        tree = parser.parse(content)
        
        summary: List[str] = []
        root_node = tree.root_node
        
        for node in root_node.children:
            if node.type in ("function_definition", "class_definition", "method_definition"):
                name_node = node.child_by_field_name("name")
                name = name_node.text.decode('utf-8') if name_node else "anonymous"
                summary.append(f"{node.type.replace('_', ' ').capitalize()}: {name}")
                
        return "\n".join(summary) if summary else "No top-level definitions found."
        
    except Exception as e:
        return f"Error analyzing AST: {str(e)}"

@artifact_tool(max_chars=5000)
def get_symbol_definition(symbol_name: str, path: str = ".") -> str:
    """Finds the definition of a function or class across the project.

    Args:
        symbol_name: The name of the function or class to find.
        path: The directory to search in.

    Returns:
        The file path and a snippet of the definition if found.
    """
    patterns = [f"def {symbol_name}", f"class {symbol_name}", f"async def {symbol_name}"]
    results: List[str] = []
    
    for pattern in patterns:
        res = ripgrep_search(f"\\b{pattern}\\b", path, extra_args=["-C", "5"])
        if res and "Error" not in res:
            results.append(res)
            
    return "\n---\n".join(results) if results else f"Definition for '{symbol_name}' not found."

@artifact_tool(max_chars=5000)
def find_references(symbol_name: str, path: str = ".") -> str:
    """Finds all references (call sites, usages) of a symbol in the project.

    Args:
        symbol_name: The name of the symbol to find.
        path: The directory to search in.

    Returns:
        A list of occurrences.
    """
    # Use ripgrep to find all usages, but exclude definitions
    extra_args = ["--line-number", "--column", "-v", f"def {symbol_name}|class {symbol_name}"]
    return ripgrep_search(f"\\b{symbol_name}\\b", path, extra_args=extra_args)

def get_scope_info(file_path: str, line_number: int, language: str = "python") -> str:
    """Identifies the variables and parameters available at a specific line.

    Args:
        file_path: Path to the file.
        line_number: The line number to analyze.
        language: Programming language.

    Returns:
        A description of the local scope.
    """
    ts_lang = _get_ts_language(language)
    if not ts_lang:
        return f"Error: Language '{language}' not supported."

    try:
        with open(file_path, "rb") as f:
            content = f.read()

        parser = _make_parser(language)
        tree = parser.parse(content)

        # Simple implementation: Find the parent function/method and extract parameters
        # In a real implementation, we'd walk up and find assignments too.
        # Tree-sitter line numbers are 0-indexed.
        target_line = line_number - 1
        
        def find_enclosing_function(node: Any) -> Optional[Any]:
            """Helper to find the function node enclosing a line number.

            Args:
                node: The starting node for traversal.

            Returns:
                The enclosing function node or None.
            """
            if node.type in ("function_definition", "method_definition"):
                if node.start_point[0] <= target_line <= node.end_point[0]:
                    return node
            for child in node.children:
                res = find_enclosing_function(child)
                if res:
                    return res
            return None

        func_node = find_enclosing_function(tree.root_node)
        if not func_node:
            return "Global scope or no enclosing function found."

        name_node = func_node.child_by_field_name("name")
        func_name = name_node.text.decode('utf-8') if name_node else "anonymous"
        
        params_node = func_node.child_by_field_name("parameters")
        params: List[str] = []
        if params_node:
            # Simple parameter extraction
            for p in params_node.children:
                if p.type in ("identifier", "typed_parameter", "parameter_declaration"):
                    params.append(p.text.decode('utf-8'))

        return f"Function: {func_name}\nParameters: {', '.join(params) if params else 'None'}"

    except Exception as e:
        return f"Error analyzing scope: {str(e)}"

@artifact_tool(max_chars=5000)
def trace_variable_semantic(variable_name: str, file_path: str, language: str = "python") -> str:
    """Traces a variable through a file using AST awareness.

    Args:
        variable_name: Name of the variable.
        file_path: Path to the file.
        language: Programming language.

    Returns:
        A list of categorized usages.
    """
    ts_lang = _get_ts_language(language)
    if not ts_lang:
        return f"Error: Language '{language}' not supported."

    try:
        with open(file_path, "rb") as f:
            content = f.read()

        parser = _make_parser(language)
        tree = parser.parse(content)

        usages: List[str] = []
        def walk(node: Any) -> None:
            """Recursively traverses the AST to find variable usages.

            Args:
                node: The current node in the traversal.
            """
            if node.type == "identifier" and node.text.decode('utf-8') == variable_name:
                parent = node.parent
                category = "USAGE"
                if parent.type in ("assignment", "variable_declaration"):
                    category = "ASSIGNMENT/DEFINITION"
                elif parent.type == "argument_list":
                    category = "SINK ARGUMENT"
                
                usages.append(f"Line {node.start_point[0] + 1}: {category}")
            
            for child in node.children:
                walk(child)
        
        walk(tree.root_node)
        return "\n".join(usages) if usages else f"Variable '{variable_name}' not found."

    except Exception as e:
        return f"Error tracing variable: {str(e)}"

# ---------------------------------------------------------------------------
# Cross-file taint analysis
# ---------------------------------------------------------------------------

# Known dangerous sinks per language. A call to any of these functions is
# considered a potential vulnerability if tainted data reaches it.
_SINKS: Dict[str, Set[str]] = {
    "python": {
        # SQL
        "execute", "executemany", "executescript", "raw", "RawSQL",
        # OS / shell
        "system", "popen", "run", "call", "check_call", "check_output", "Popen",
        # Code injection
        "eval", "exec", "compile",
        # Template injection
        "render_template_string", "from_string",
        # Deserialisation
        "loads", "load",
        # File write
        "write",
    },
    "javascript": {
        "eval", "exec", "execSync", "execFile", "spawnSync",
        "innerHTML", "outerHTML", "write", "query", "execute",
        "dangerouslySetInnerHTML",
    },
    "go": {"Exec", "Command", "Query", "Execute"},
    "csharp": {"Execute", "ExecuteNonQuery", "ExecuteReader", "ExecuteScalar", "Start"},
}


def _node_contains_identifier(node: Any, name: str) -> bool:
    """Return True if *node* or any descendant is an identifier equal to *name*.

    Args:
        node: A tree-sitter ``Node``.
        name: Identifier text to look for.

    Returns:
        ``True`` if the identifier is found, ``False`` otherwise.
    """
    if node.type == "identifier" and node.text.decode("utf-8") == name:
        return True
    for child in node.children:
        if _node_contains_identifier(child, name):
            return True
    return False


def _extract_callee_name(func_node: Any) -> Optional[str]:
    """Extract the plain function/method name from a call's callee node.

    Handles simple identifiers (``fetch``) and attribute access (``cursor.execute``).

    Args:
        func_node: The first child of a tree-sitter ``call`` node.

    Returns:
        The callee name string, or ``None`` if it cannot be determined.
    """
    if func_node.type == "identifier":
        return func_node.text.decode("utf-8")
    if func_node.type == "attribute":
        # Last identifier child is the method name (e.g. "execute" in "cursor.execute")
        for child in reversed(func_node.children):
            if child.type == "identifier":
                return child.text.decode("utf-8")
    return None


def _find_calls_passing_variable(
    variable_name: str,
    content: bytes,
    language: str = "python",
) -> List[Tuple[str, int, int]]:
    """Find all calls in *content* where *variable_name* appears as an argument.

    Args:
        variable_name: The tainted variable to search for.
        content: Raw file bytes.
        language: Programming language.

    Returns:
        A list of ``(callee_name, arg_index, line_number)`` tuples.
    """
    parser = _make_parser(language)
    if parser is None:
        return []
    tree = parser.parse(content)

    results: List[Tuple[str, int, int]] = []

    def walk(node: Any) -> None:
        if node.type == "call":
            callee_node = node.children[0] if node.children else None
            callee = _extract_callee_name(callee_node) if callee_node else None
            arg_list = next(
                (c for c in node.children if c.type == "argument_list"), None
            )
            if callee and arg_list:
                actual_args = [
                    c for c in arg_list.children if c.type not in ("(", ")", ",")
                ]
                for idx, arg in enumerate(actual_args):
                    if _node_contains_identifier(arg, variable_name):
                        results.append((callee, idx, node.start_point[0] + 1))
        for child in node.children:
            walk(child)

    walk(tree.root_node)
    return results


def _find_returns_variable(
    variable_name: str,
    content: bytes,
    language: str = "python",
) -> List[int]:
    """Return line numbers where *variable_name* appears in a return statement.

    Args:
        variable_name: The tainted variable to search for.
        content: Raw file bytes.
        language: Programming language.

    Returns:
        A list of 1-based line numbers.
    """
    parser = _make_parser(language)
    if parser is None:
        return []
    tree = parser.parse(content)
    lines: List[int] = []

    def walk(node: Any) -> None:
        if node.type == "return_statement":
            for child in node.children:
                if _node_contains_identifier(child, variable_name):
                    lines.append(node.start_point[0] + 1)
                    break
        for child in node.children:
            walk(child)

    walk(tree.root_node)
    return lines


def _find_function_file(
    func_name: str,
    project_root: str = ".",
    language: str = "python",
) -> Optional[str]:
    """Find the file that defines *func_name* using ripgrep.

    Args:
        func_name: The function name to search for.
        project_root: Root directory to search in.
        language: Programming language (affects the search pattern).

    Returns:
        The relative file path of the first match, or ``None``.
    """
    if language == "python":
        patterns = [rf"\bdef {re.escape(func_name)}\b", rf"\basync def {re.escape(func_name)}\b"]
    elif language in ("javascript", "go"):
        patterns = [rf"\bfunction {re.escape(func_name)}\b", rf"\b{re.escape(func_name)}\s*=\s*(?:async\s+)?function"]
    else:
        patterns = [rf"\b{re.escape(func_name)}\b"]

    for pattern in patterns:
        output = ripgrep_search(pattern, project_root, extra_args=["-l"])
        if output and "Error" not in output:
            first = output.strip().splitlines()[0].strip()
            if first:
                return first
    return None


def _resolve_param_name(
    func_name: str,
    arg_index: int,
    func_file: str,
    language: str = "python",
) -> Optional[str]:
    """Return the parameter name at *arg_index* in the definition of *func_name*.

    Reads *func_file* and parses the function signature with tree-sitter.

    Args:
        func_name: The function whose signature to inspect.
        arg_index: Zero-based position of the parameter to resolve.
        func_file: Path to the file containing the function definition.
        language: Programming language.

    Returns:
        The parameter name string, or ``None`` if it cannot be resolved.
    """
    try:
        with open(func_file, "rb") as f:
            content = f.read()
    except OSError:
        return None

    parser = _make_parser(language)
    if parser is None:
        return None
    tree = parser.parse(content)

    def find_func(node: Any) -> Optional[Any]:
        if node.type in ("function_definition", "method_definition"):
            name_node = node.child_by_field_name("name")
            if name_node and name_node.text.decode("utf-8") == func_name:
                return node
        for child in node.children:
            result = find_func(child)
            if result:
                return result
        return None

    func_node = find_func(tree.root_node)
    if func_node is None:
        return None

    params_node = func_node.child_by_field_name("parameters")
    if params_node is None:
        return None

    # Collect actual parameter nodes (skip self/cls and punctuation)
    params: List[str] = []
    for p in params_node.children:
        if p.type in ("identifier", "typed_parameter", "default_parameter",
                      "list_splat_pattern", "dictionary_splat_pattern"):
            # Get the raw name (first identifier inside typed/default params)
            if p.type == "identifier":
                name = p.text.decode("utf-8")
            else:
                name_child = next(
                    (c for c in p.children if c.type == "identifier"), None
                )
                name = name_child.text.decode("utf-8") if name_child else p.text.decode("utf-8")
            if name not in ("self", "cls"):
                params.append(name)

    if arg_index < len(params):
        return params[arg_index]
    return None

@artifact_tool(max_chars=8000)
def trace_taint_cross_file(
    variable: str,
    source_file: str,
    project_root: str = ".",
    language: str = "python",
    max_depth: int = 5,
) -> str:
    """Trace a tainted variable across file boundaries toward known dangerous sinks.

    Starting from *variable* in *source_file*, the tracer follows the data flow
    into callee functions (potentially in other files) until it either reaches a
    known sink, exhausts all paths, or hits the depth limit.

    This implements the **[HIGH] Enhanced Taint Analysis** requirement: cross-file
    data flow tracing from entry points to sinks.

    Args:
        variable: The tainted variable name to trace (e.g. ``"user_id"``).
        source_file: The file where the taint originates (relative to *project_root*).
        project_root: Root directory of the project being analysed.
        language: Programming language (python, javascript, go, csharp).
        max_depth: Maximum number of file hops to follow before stopping.

    Returns:
        A human-readable trace report listing each hop, categorising usages as
        SINK (vulnerability), CALL (data flows into a callee), RETURN, or SAFE
        (no dangerous usage found within the depth limit).
    """
    sinks = _SINKS.get(language, set())
    report_lines: List[str] = [
        f"Taint trace: variable='{variable}', start='{source_file}', language={language}",
        "=" * 60,
    ]
    visited: Set[Tuple[str, str]] = set()  # (file_path, variable_name) pairs

    def _trace(var: str, file_path: str, depth: int) -> None:
        key = (file_path, var)
        if depth > max_depth or key in visited:
            if key in visited:
                report_lines.append(f"  {'  ' * depth}[cycle detected: {file_path}:{var}]")
            else:
                report_lines.append(f"  {'  ' * depth}[max depth {max_depth} reached]")
            return
        visited.add(key)

        full_path = os.path.join(project_root, file_path)
        indent = "  " * depth

        report_lines.append(f"\n{indent}File: {file_path}  Variable: '{var}'")

        try:
            with open(full_path, "rb") as f:
                content = f.read()
        except OSError:
            report_lines.append(f"{indent}  [could not read file]")
            return

        # 1. Check for sink calls
        calls = _find_calls_passing_variable(var, content, language)
        found_sink = False
        for callee, arg_idx, line_no in calls:
            if callee in sinks:
                report_lines.append(
                    f"{indent}  *** SINK *** Line {line_no}: '{var}' passed to '{callee}()' "
                    f"(arg {arg_idx}) — potential vulnerability"
                )
                found_sink = True
            else:
                report_lines.append(
                    f"{indent}  CALL Line {line_no}: '{var}' → '{callee}()' (arg {arg_idx}) — following..."
                )
                # Resolve callee file and param name
                callee_file = _find_function_file(callee, project_root, language)
                if callee_file:
                    param_name = _resolve_param_name(callee, arg_idx, callee_file, language)
                    if param_name:
                        _trace(param_name, callee_file, depth + 1)
                    else:
                        report_lines.append(
                            f"{indent}    [could not resolve param at index {arg_idx} in {callee}]"
                        )
                else:
                    report_lines.append(
                        f"{indent}    [definition of '{callee}' not found in project — "
                        f"may be an external library call]"
                    )

        # 2. Check for return statements (taint escapes function)
        return_lines = _find_returns_variable(var, content, language)
        for line_no in return_lines:
            report_lines.append(
                f"{indent}  RETURN Line {line_no}: '{var}' returned — "
                f"caller must be traced separately"
            )

        if not calls and not return_lines:
            report_lines.append(f"{indent}  SAFE: '{var}' has no outgoing flow in this file")
        elif not found_sink and not return_lines and all(
            c[0] not in sinks for c in calls
        ):
            pass  # child traces already reported

    _trace(variable, source_file, depth=0)

    report_lines.append("\n" + "=" * 60)
    has_sink = any("*** SINK ***" in line for line in report_lines)
    report_lines.append(
        "RESULT: POTENTIAL VULNERABILITY FOUND" if has_sink else "RESULT: No sinks reached within depth limit"
    )
    return "\n".join(report_lines)

@artifact_tool(max_chars=5000)
def trace_variable(variable_name: str, file_path: str) -> str:
    """Finds all occurrences of a variable in a file to trace its flow.

    Args:
        variable_name: Name of the variable to trace.
        file_path: Path to the file.

    Returns:
        The results of the ripgrep search for the variable.
    """
    return ripgrep_search(f"\\b{variable_name}\\b", file_path, extra_args=["--line-number", "--column"])

@artifact_tool(max_chars=5000)
def bash_tool(command: str, timeout: int = 30) -> str:
    """Executes a bash command or script and returns the output.

    Args:
        command: The bash command to execute.
        timeout: Execution timeout in seconds.

    Returns:
        A formatted string containing stdout, stderr, and the exit code.
    """
    # Note: Bash commands need to be executed through a shell
    cmd = ["bash", "-c", command]
    try:
        result = _run_sandboxed(cmd, timeout=timeout, network=True)
        output: List[str] = []
        if result.stdout:
            output.append(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            output.append(f"STDERR:\n{result.stderr}")
        if not output:
            output.append(f"Command exited with code {result.returncode} (No output)")
        else:
            output.append(f"Exit Code: {result.returncode}")
        return "\n\n".join(output)
    except Exception as e:
        return f"Error executing command: {str(e)}"

@artifact_tool(max_chars=5000)
def container_bash_tool(command: str, image: str = "python:3.11-slim", timeout: int = 60) -> str:
    """Executes a bash command or script inside a temporary Docker container.
    This provides an isolated environment for running Proof of Concepts.

    Args:
        command: The command to execute.
        image: The Docker image to use (e.g., 'python:3.11-slim', 'node:lts-slim').
        timeout: Execution timeout in seconds.

    Returns:
        The output of the command or an error message.
    """
    # Check if Docker is available
    try:
        subprocess.run(["docker", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "[Warning: Docker not found. Falling back to host bash_tool]\n\n" + bash_tool(command, timeout)

    # Use a temporary container to run the command
    # We mount the current project directory read-only for context if needed,
    # but the command runs in a scratch space.
    project_root = os.getcwd()
    cmd = [
        "docker", "run", "--rm",
        "--network", "none", # Isolate network by default
        "-v", f"{project_root}:/app:ro",
        "-w", "/tmp",
        image,
        "bash", "-c", command
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False
        )
        output: List[str] = []
        if result.stdout:
            output.append(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            output.append(f"STDERR:\n{result.stderr}")
        if not output:
            output.append(f"Command exited with code {result.returncode} (No output)")
        else:
            output.append(f"Exit Code: {result.returncode}")
        return "\n\n".join(output)
    except subprocess.TimeoutExpired:
        return "Error: Container execution timed out."
    except Exception as e:
        return f"Error executing command in container: {str(e)}"

@artifact_tool(max_chars=8000)
async def web_fetch(url: str) -> str:
    """Fetches the content of a web page and returns its text.
    Use this to read specific articles, documentation, or CVE details.

    Args:
        url: The URL of the web page to fetch.

    Returns:
        The text content of the page (cleaned of HTML tags).
    """
    import aiohttp
    from bs4 import BeautifulSoup
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                if response.status != 200:
                    return f"Error: Failed to fetch page, status code {response.status}"
                
                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")
                
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.extract()
                
                # Get text and clean up whitespace
                text = soup.get_text()
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = "\n".join(chunk for chunk in chunks if chunk)
                
                # We return the whole text, the artifact_tool will handle truncation if needed
                return text
    except Exception as e:
        return f"Error fetching URL: {str(e)}"

@artifact_tool(max_chars=5000)
def query_cwe_database(query: str) -> str:
    """Queries the built-in CWE knowledge base for descriptions and examples.

    Args:
        query: The search query (CWE ID, title, or description keyword).

    Returns:
        A formatted string containing matching CWE entries and examples.
    """
    try:
        data_path = os.path.join(os.path.dirname(__file__), "data", "cwe_db.json")
        with open(data_path, "r", encoding="utf-8") as f:
            cwe_data: List[Dict[str, Any]] = json.load(f)
        results: List[str] = []
        q = query.lower()
        for item in cwe_data:
            if (q in item["cwe_id"].lower() or q in item["title"].lower() or q in item["description"].lower()):
                results.append(f"### {item['cwe_id']}: {item['title']}\n{item['description']}\n")
                if "examples" in item:
                    for ex in item["examples"]:
                        results.append(f"**Vulnerable Example ({ex['language']}):**\n```\n{ex['vulnerable_code']}\n```\n")
        return "\n".join(results) if results else f"No results found for query: {query}"
    except Exception as e:
        return f"Error querying CWE database: {str(e)}"

# ---------------------------------------------------------------------------
# Workflow & Loop Tools
# ---------------------------------------------------------------------------

def exit_loop(tool_context: Any) -> str:
    """Exits the current autonomous loop. Call this when no more targets remain.

    Args:
        tool_context: The ADK ToolContext (injected automatically).

    Returns:
        A confirmation message.
    """
    # ADK uses 'escalate' to break out of a LoopAgent
    if hasattr(tool_context, "actions"):
        tool_context.actions.escalate = True
    return "Loop exit requested."

def get_next_hypothesis(project_path: str, db_path: str = ".trashdig/trashdig.db") -> str:
    """Retrieves the next pending hypothesis from the database.

    Args:
        project_path: The root directory of the project.
        db_path: Path to the SQLite database.

    Returns:
        A JSON string containing the hypothesis details, or 'None' if no pending tasks.
    """
    import sqlite3
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM hypotheses WHERE project_path = ? AND status = 'pending' ORDER BY confidence DESC LIMIT 1",
            (project_path,)
        ).fetchone()
        conn.close()
        
        if row:
            return json.dumps(dict(row))
        return "None"
    except Exception as e:
        return f"Error accessing database: {str(e)}"

def update_hypothesis_status(task_id: str, status: str, db_path: str = ".trashdig/trashdig.db") -> str:
    """Updates the status of a hypothesis (e.g., to 'completed' or 'failed').

    Args:
        task_id: The unique ID of the hypothesis task.
        status: The new status (e.g., 'completed', 'failed').
        db_path: Path to the SQLite database.

    Returns:
        A confirmation message.
    """
    import sqlite3
    try:
        conn = sqlite3.connect(db_path)
        conn.execute(
            "UPDATE hypotheses SET status = ?, updated_at = ? WHERE task_id = ?",
            (status, datetime.now().isoformat(), task_id)
        )
        conn.commit()
        conn.close()
        return f"Hypothesis {task_id} updated to {status}."
    except Exception as e:
        return f"Error updating database: {str(e)}"

