import os
import re
from contextlib import suppress
from typing import Any

from trashdig.metadata.languages import get_language_metadata
from trashdig.sandbox.landlock_tool import landlock_tool

from .base import _make_parser, artifact_tool, get_config
from .ripgrep_search import ripgrep_search


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


def _get_full_callee_path(func_node: Any, metadata: Any) -> list[str]:
    """Extract the full path of a callee (e.g. ['module', 'func'])."""
    if func_node.type == "identifier":
        return [func_node.text.decode("utf-8")]
    if func_node.type == "attribute" or (
        metadata.name == "csharp" and func_node.type == "member_access_expression"
    ):
        # In python: (attribute object: (_) attribute: (identifier))
        # In JS: (attribute_expression object: (_) property: (property_identifier))
        # In Go: (selector_expression operand: (_) field: (field_identifier))
        # This implementation is a bit Python-centric, but trying to generalize

        obj = func_node.child_by_field_name("object") or func_node.child_by_field_name("operand")
        attr = (
            func_node.child_by_field_name("attribute")
            or func_node.child_by_field_name("property")
            or func_node.child_by_field_name("field")
            or func_node.child_by_field_name("name")
        )

        path: list[str] = []
        if obj:
            if obj.type == "identifier":
                path.append(obj.text.decode("utf-8"))
            elif obj.type in (
                "attribute",
                "selector_expression",
                "member_access_expression",
                "attribute_expression",
            ):
                path.extend(_get_full_callee_path(obj, metadata))
            elif obj.type == "call" or obj.type == "call_expression":
                # For call().method, we might want to know the call's callee
                inner_callee_node = obj.child_by_field_name("function")
                if inner_callee_node:
                    path.extend(_get_full_callee_path(inner_callee_node, metadata))
                path.append("()")  # Marker for call

        if attr and attr.type in ("identifier", "property_identifier", "field_identifier"):
            path.append(attr.text.decode("utf-8"))

        return path
    return []


def _resolve_import(
    symbol_name: str,
    file_content: bytes,
    language: str = "python",
) -> str | None:
    """Attempt to resolve which module/file a symbol is imported from.

    Args:
        symbol_name: The name of the symbol to resolve.
        file_content: Raw bytes of the file where symbol is used.
        language: Programming language.

    Returns:
        The likely module name or file path prefix, or None.
    """
    if language != "python":
        return None  # TODO: Implement for other languages

    parser = _make_parser(language)
    if parser is None:
        return None
    tree = parser.parse(file_content)

    # Search for:
    # 1. from X import symbol_name
    # 2. import symbol_name (less likely for functions)
    # 3. import X as symbol_name

    def walk(node: Any) -> str | None:
        if node.type == "import_from_statement":
            # node structure: from module_name import name1, name2
            module_node = node.child_by_field_name("module_name")
            if module_node:
                module_name = module_node.text.decode("utf-8")
                # Check if symbol_name is in the imported names
                for child in node.children:
                    if child.type == "dotted_name" and child.text.decode("utf-8") == symbol_name:
                        return module_name
                    if child.type == "aliased_import":
                        name = child.child_by_field_name("name")
                        alias = child.child_by_field_name("alias")
                        if alias and alias.text.decode("utf-8") == symbol_name:
                            return module_name
                        if not alias and name and name.text.decode("utf-8") == symbol_name:
                            return module_name

        if node.type == "import_statement":
            for child in node.children:
                if child.type == "dotted_name" and child.text.decode("utf-8") == symbol_name:
                    return symbol_name
                if child.type == "aliased_import":
                    alias = child.child_by_field_name("alias")
                    if alias and alias.text.decode("utf-8") == symbol_name:
                        name = child.child_by_field_name("name")
                        return name.text.decode("utf-8") if name else None

        for child in node.children:
            res = walk(child)
            if res:
                return res
        return None

    return walk(tree.root_node)


def _module_to_file_path(module_name: str, project_root: str) -> str | None:
    """Converts a python module name (a.b.c) to a likely file path."""
    rel_path = module_name.replace(".", os.sep)
    # Try .py and /__init__.py
    options = [rel_path + ".py", os.path.join(rel_path, "__init__.py")]
    for opt in options:
        if os.path.exists(os.path.join(project_root, opt)):
            return opt
    return None


def _find_calls_passing_variable(
    variable_name: str,
    content: bytes,
    language: str = "python",
) -> list[tuple[str, int, int, Any]]:
    """Find all calls in *content* where *variable_name* appears as an argument.

    Args:
        variable_name: The tainted variable to search for.
        content: Raw file bytes.
        language: Programming language.

    Returns:
        A list of ``(callee_name, arg_index, line_number, callee_node)`` tuples.
    """
    parser = _make_parser(language)
    if parser is None:
        return []
    tree = parser.parse(content)

    results: list[tuple[str, int, int, Any]] = []

    def walk(node: Any) -> None:
        if node.type == "call":
            callee_node = node.children[0] if node.children else None
            callee = _extract_callee_name(callee_node) if callee_node else None

            arg_list = next((c for c in node.children if c.type == "argument_list"), None)
            if callee and arg_list:
                actual_args = [c for c in arg_list.children if c.type not in ("(", ")", ",")]
                for idx, arg in enumerate(actual_args):
                    if _node_contains_identifier(arg, variable_name):
                        results.append((callee, idx, node.start_point[0] + 1, callee_node))
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
    metadata: Any = None,
) -> list[str]:
    """Find all files that define *func_name* using ripgrep.

    Args:
        func_name: The function name to search for.
        project_root: Root directory to search in.
        metadata: Language metadata.

    Returns:
        A list of relative file paths of matches.
    """
    if not metadata:
        patterns = [rf"\b{re.escape(func_name)}\b"]
    else:
        patterns = [p.format(name=re.escape(func_name)) for p in metadata.definition_patterns]

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


def _find_function_node(node: Any, func_name: str, metadata: Any) -> Any | None:
    """Find a function or method definition by name."""
    if node.type in metadata.definition_types:
        name_node = node.child_by_field_name("name")
        if not name_node:
            for field in ("declarator", "identifier"):
                name_node = node.child_by_field_name(field)
                if name_node:
                    break
        if name_node and name_node.text.decode("utf-8") == func_name:
            return node
    for child in node.children:
        result = _find_function_node(child, func_name, metadata)
        if result:
            return result
    return None


def _extract_function_params(func_node: Any, metadata: Any) -> list[str]:
    """Collect parameter names from a function node, excluding skip symbols."""
    params_node = func_node.child_by_field_name("parameters")
    if params_node is None:
        # JS arrow function fallback
        if metadata.name == "javascript" and func_node.type == "arrow_function":
            p = func_node.child_by_field_name("parameter")
            if p and p.type == "identifier":
                return [p.text.decode("utf-8")]
        return []

    params: list[str] = []
    for p in params_node.children:
        if p.type in metadata.parameter_types:
            # Get the raw name
            if p.type == "identifier":
                name = p.text.decode("utf-8")
            else:
                name_child = next((c for c in p.children if c.type == "identifier"), None)
                name = name_child.text.decode("utf-8") if name_child else p.text.decode("utf-8")

            if name not in metadata.skip_symbols:
                params.append(name)
    return params


def _resolve_param_name(
    func_name: str,
    arg_index: int,
    func_file: str,
    metadata: Any,
) -> str | None:
    """Return the parameter name at *arg_index* in the definition of *func_name*.

    Reads *func_file* and parses the function signature with tree-sitter.

    Args:
        func_name: The function whose signature to inspect.
        arg_index: Zero-based position of the parameter to resolve.
        func_file: Path to the file containing the function definition.
        metadata: Language metadata.

    Returns:
        The parameter name string, or ``None`` if it cannot be resolved.
    """
    try:
        with open(func_file, "rb") as f:
            content = f.read()
    except OSError:
        return None

    parser = _make_parser(metadata.name)
    if parser is None:
        return None
    tree = parser.parse(content)

    func_node = _find_function_node(tree.root_node, func_name, metadata)
    if func_node is None:
        return None

    params = _extract_function_params(func_node, metadata)

    if arg_index < len(params):
        return params[arg_index]
    return None


def _find_assignment(
    variable_name: str,
    file_content: bytes,
    metadata: Any,
) -> str | None:
    """Find the value assigned to a variable in the current file."""
    parser = _make_parser(metadata.name)
    if parser is None:
        return None
    tree = parser.parse(file_content)

    # Search for: variable_name = Value(...)
    def walk(node: Any) -> str | None:
        if node.type in metadata.assignment_types:
            left = node.child_by_field_name("left")
            right = node.child_by_field_name("right")
            # For some languages, name might be a child declarator
            if not left and node.type in ("variable_declaration", "lexical_declaration"):
                for child in node.children:
                    if child.type == "variable_declarator":
                        name_node = child.child_by_field_name("name")
                        val_node = child.child_by_field_name("value")
                        if (
                            name_node
                            and name_node.text.decode("utf-8") == variable_name
                            and val_node
                        ):
                            if val_node.type in ("call", "call_expression"):
                                callee = val_node.child_by_field_name("function")
                                if callee:
                                    return callee.text.decode("utf-8")

            if left and left.text.decode("utf-8") == variable_name and right:
                if right.type in ("call", "call_expression"):
                    # Extract callee of the assignment (e.g. 'Database' in 'db = Database()')
                    callee = right.child_by_field_name("function")
                    if callee:
                        return callee.text.decode("utf-8")
        for child in node.children:
            res = walk(child)
            if res:
                return res
        return None

    return walk(tree.root_node)


def _process_tainted_calls(  # noqa: PLR0913
    calls: list[tuple[str, int, int, Any]],
    var: str,
    report_lines: list[str],
    indent: str,
    project_root: str,
    metadata: Any,
    depth: int,
    max_depth: int,
    visited: set[tuple[str, str]],
    file_content: bytes,
) -> bool:
    """Process calls where a tainted variable is passed as an argument."""
    found_sink = False

    for callee, arg_idx, line_no, callee_node in calls:
        # Check if it's a known direct sink
        if callee in metadata.sinks:
            report_lines.append(
                f"{indent}  *** SINK *** Line {line_no}: '{var}' passed to '{callee}()' "
                f"(arg {arg_idx}) — potential vulnerability"
            )
            found_sink = True
            continue

        # Check for method sinks (e.g. conn.execute)
        is_method_sink_candidate = callee in metadata.method_sinks

        report_lines.append(
            f"{indent}  CALL Line {line_no}: '{var}' → '{callee}()' (arg {arg_idx}) — following..."
        )

        # --- ENHANCED RESOLUTION ---
        callee_files: list[str] = []

        # 1. Check if it's an attribute call (obj.method)
        path = _get_full_callee_path(callee_node, metadata)
        obj_name = None
        if len(path) > 1:
            obj_name = path[0]
            # Try to see where obj_name comes from
            # a) Is it an imported module name?
            imported_module = _resolve_import(obj_name, file_content, metadata.name)
            if not imported_module:
                # b) Is it a local variable assigned from an imported class?
                assigned_from = _find_assignment(obj_name, file_content, metadata)
                if assigned_from:
                    imported_module = _resolve_import(assigned_from, file_content, metadata.name)

            if imported_module:
                m_path = _module_to_file_path(imported_module, project_root)
                if m_path:
                    callee_files = [m_path]
                # It's an imported module but not in project (e.g. stdlib)
                # If it's a known method sink, treat as sink
                elif is_method_sink_candidate:
                    report_lines.append(
                        f"{indent}  *** SINK (Library) *** Line {line_no}: '{var}' passed to '{callee}()' "
                        f"on library object '{obj_name}' (module '{imported_module}')"
                    )
                    found_sink = True
                    continue

        # 2. Check if the function itself is imported
        if not callee_files:
            imported_module = _resolve_import(callee, file_content, metadata.name)
            if imported_module:
                m_path = _module_to_file_path(imported_module, project_root)
                if m_path:
                    callee_files = [m_path]

        # 3. Fallback to global search
        if not callee_files:
            callee_files = _find_function_files(callee, project_root, metadata)

        # 4. Final heuristic for method sinks:
        # If it's a method sink (like .execute) and we still have NO files OR multiple files
        # but none were resolved via imports, it might be a library sink (sqlite3.execute).
        if is_method_sink_candidate and not callee_files:
            report_lines.append(
                f"{indent}  *** SINK (Method) *** Line {line_no}: '{var}' passed to '{callee}()' "
                f"on object '{obj_name}' — potential library sink"
            )
            found_sink = True
            continue

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
        param_name = _resolve_param_name(callee, arg_idx, abs_callee_file, metadata)
        if param_name:
            _trace_recursive(
                param_name,
                callee_file,
                depth + 1,
                max_depth,
                visited,
                report_lines,
                project_root,
                metadata,
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
    metadata: Any,
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

    calls = _find_calls_passing_variable(var, content, metadata.name)
    found_sink = _process_tainted_calls(
        calls, var, report_lines, indent, project_root, metadata, depth, max_depth, visited, content
    )

    return_lines = _find_returns_variable(var, content, metadata.name)
    for line_no in return_lines:
        report_lines.append(
            f"{indent}  RETURN Line {line_no}: '{var}' returned — caller must be traced separately"
        )

    if not calls and not return_lines:
        report_lines.append(f"{indent}  SAFE: '{var}' has no outgoing flow in this file")
    elif not found_sink and not return_lines and all(c[0] not in metadata.sinks for c in calls):
        pass  # child traces already reported


@artifact_tool(max_chars=8000)
@landlock_tool()
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

    metadata = get_language_metadata(language)
    if not metadata:
        return f"Error: Language '{language}' not supported."

    report_lines: list[str] = [
        f"Taint trace: variable='{variable}', start='{source_file}', language={language}",
        "=" * 60,
    ]
    visited: set[tuple[str, str]] = set()

    _trace_recursive(
        variable, source_file, 0, max_depth, visited, report_lines, project_root, metadata
    )

    report_lines.append("\n" + "=" * 60)
    has_sink = any("*** SINK" in line for line in report_lines)
    report_lines.append(
        "RESULT: POTENTIAL VULNERABILITY FOUND"
        if has_sink
        else "RESULT: No sinks reached within depth limit"
    )
    return "\n".join(report_lines)
