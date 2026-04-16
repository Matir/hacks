import os
import re
from contextlib import suppress
from typing import Any

from .base import _make_parser, artifact_tool, get_config
from .ripgrep_search import ripgrep_search

# Known dangerous sinks per language. A call to any of these functions is
# considered a potential vulnerability if tainted data reaches it.
_SINKS: dict[str, set[str]] = {
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
    return any(_node_contains_identifier(child, name) for child in node.children)


def _extract_callee_name(func_node: Any) -> str | None:
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
) -> list[tuple[str, int, int]]:
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

    results: list[tuple[str, int, int]] = []

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
) -> list[int]:
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
    lines: list[int] = []

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


def _find_function_files(
    func_name: str,
    project_root: str = ".",
    language: str = "python",
) -> list[str]:
    """Find all files that define *func_name* using ripgrep.

    Args:
        func_name: The function name to search for.
        project_root: Root directory to search in.
        language: Programming language (affects the search pattern).

    Returns:
        A list of relative file paths of matches.
    """
    if language == "python":
        patterns = [rf"\bdef {re.escape(func_name)}\b", rf"\basync def {re.escape(func_name)}\b"]
    elif language in ("javascript", "go"):
        patterns = [rf"\bfunction {re.escape(func_name)}\b", rf"\b{re.escape(func_name)}\s*=\s*(?:async\s+)?function"]
    else:
        patterns = [rf"\b{re.escape(func_name)}\b"]

    all_files: set[str] = set()
    abs_project_root = os.path.abspath(project_root)
    for pattern in patterns:
        output = ripgrep_search(pattern, project_root, extra_args=["-l"])
        if output and "Error" not in output:
            for line in output.strip().splitlines():
                path = line.strip()
                if path:
                    if os.path.isabs(path):
                        with suppress(ValueError):
                            path = os.path.relpath(path, abs_project_root)
                    all_files.add(path)
    return sorted(all_files)


def _find_function_node(node: Any, func_name: str) -> Any | None:
    """Find a function or method definition by name."""
    if node.type in ("function_definition", "method_definition"):
        name_node = node.child_by_field_name("name")
        if name_node and name_node.text.decode("utf-8") == func_name:
            return node
    for child in node.children:
        result = _find_function_node(child, func_name)
        if result:
            return result
    return None


def _extract_function_params(func_node: Any) -> list[str]:
    """Collect parameter names from a function node, excluding self/cls."""
    params_node = func_node.child_by_field_name("parameters")
    if params_node is None:
        return []

    params: list[str] = []
    for p in params_node.children:
        if p.type in ("identifier", "typed_parameter", "default_parameter",
                      "list_splat_pattern", "dictionary_splat_pattern"):
            # Get the raw name
            if p.type == "identifier":
                name = p.text.decode("utf-8")
            else:
                name_child = next(
                    (c for c in p.children if c.type == "identifier"), None
                )
                name = name_child.text.decode("utf-8") if name_child else p.text.decode("utf-8")

            if name not in ("self", "cls"):
                params.append(name)
    return params


def _resolve_param_name(
    func_name: str,
    arg_index: int,
    func_file: str,
    language: str = "python",
) -> str | None:
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

    func_node = _find_function_node(tree.root_node, func_name)
    if func_node is None:
        return None

    params = _extract_function_params(func_node)

    if arg_index < len(params):
        return params[arg_index]
    return None

def _process_tainted_calls(  # noqa: PLR0913
    calls: list[tuple[str, int, int]],
    var: str,
    sinks: set[str],
    report_lines: list[str],
    indent: str,
    project_root: str,
    language: str,
    depth: int,
    max_depth: int,
    visited: set[tuple[str, str]],
) -> bool:
    """Process calls where a tainted variable is passed as an argument."""
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
            # Resolve callee files and param name
            callee_files = _find_function_files(callee, project_root, language)
            if not callee_files:
                report_lines.append(
                    f"{indent}    [definition of '{callee}' not found in project — "
                    f"may be an external library call]"
                )
                continue

            if len(callee_files) > 1:
                report_lines.append(
                    f"{indent}    [Warning: multiple definitions for '{callee}' found. Following first match in {callee_files[0]}]"
                )

            callee_file = callee_files[0]
            abs_callee_file = os.path.join(project_root, callee_file)
            param_name = _resolve_param_name(callee, arg_idx, abs_callee_file, language)
            if param_name:
                _trace_recursive(
                    param_name, callee_file, depth + 1, max_depth,
                    visited, report_lines, project_root, language, sinks
                )
            else:
                report_lines.append(
                    f"{indent}    [could not resolve param at index {arg_idx} in {callee}]"
                )
    return found_sink


def _trace_recursive(  # noqa: PLR0913
    var: str,
    file_path: str,
    depth: int,
    max_depth: int,
    visited: set[tuple[str, str]],
    report_lines: list[str],
    project_root: str,
    language: str,
    sinks: set[str],
) -> None:
    """Internal recursive function for taint tracing."""
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

    calls = _find_calls_passing_variable(var, content, language)
    found_sink = _process_tainted_calls(
        calls, var, sinks, report_lines, indent, project_root,
        language, depth, max_depth, visited
    )

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


@artifact_tool(max_chars=8000)
def trace_taint_cross_file(
    variable: str,
    source_file: str,
    project_root: str | None = None,
    language: str = "python",
    max_depth: int = 5,
) -> str:
    """Trace a tainted variable across file boundaries toward known dangerous sinks.

    Starting from *variable* in *source_file*, the tracer follows the data flow
    into callee functions (potentially in other files) until it either reaches a
    known sink, exhausts all paths, or hits the depth limit.

    Args:
        variable: The tainted variable name to trace (e.g. ``"user_id"``).
        source_file: The file where the taint originates (relative to *project_root*).
        project_root: Root directory of the project being analysed. Defaults to Config workspace_root.
        language: Programming language (python, javascript, go, csharp).
        max_depth: Maximum number of file hops to follow before stopping.

    Returns:
        A human-readable trace report listing each hop.
    """
    if project_root is None:
        project_root = get_config().workspace_root

    sinks = _SINKS.get(language, set())
    report_lines: list[str] = [
        f"Taint trace: variable='{variable}', start='{source_file}', language={language}",
        "=" * 60,
    ]
    visited: set[tuple[str, str]] = set()

    _trace_recursive(
        variable, source_file, 0, max_depth, visited,
        report_lines, project_root, language, sinks
    )

    report_lines.append("\n" + "=" * 60)
    has_sink = any("*** SINK ***" in line for line in report_lines)
    report_lines.append(
        "RESULT: POTENTIAL VULNERABILITY FOUND" if has_sink else "RESULT: No sinks reached within depth limit"
    )
    return "\n".join(report_lines)
