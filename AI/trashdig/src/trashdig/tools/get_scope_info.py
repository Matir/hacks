from typing import Any

from trashdig.metadata.languages import (
    get_language_metadata,
)
from trashdig.metadata.languages import (
    get_ts_language as _get_ts_language,
)
from trashdig.metadata.languages import make_parser as _make_parser
from trashdig.sandbox.landlock_tool import landlock_tool

from .base import get_config


def _find_enclosing_scopes(node: Any, target_line: int, metadata: Any) -> list[Any]:
    """Finds all scope-defining nodes enclosing a line number (innermost last)."""
    scopes = []

    if (
        node.type in metadata.scope_types
        and node.start_point[0] <= target_line <= node.end_point[0]
    ):
        scopes.append(node)

    for child in node.children:
        res = _find_enclosing_scopes(child, target_line, metadata)
        if res:
            scopes.extend(res)
    return scopes


def _extract_params_from_node(p: Any, metadata: Any) -> list[str]:
    """Helper to extract names from a parameter node."""
    params = []
    if p.type == "identifier":
        name = p.text.decode("utf-8")
        if name not in metadata.skip_symbols:
            params.append(name)
    elif p.type in metadata.parameter_types:
        for child in p.children:
            if child.type == "identifier":
                name = child.text.decode("utf-8")
                if name not in metadata.skip_symbols:
                    params.append(name)
                break
    return params


def _extract_params(func_node: Any, metadata: Any) -> list[str]:
    """Extract parameter names from a function node."""
    params: list[str] = []

    params_node = func_node.child_by_field_name("parameters")
    if params_node:
        for p in params_node.children:
            params.extend(_extract_params_from_node(p, metadata))

    if not params and metadata.name == "javascript" and func_node.type == "arrow_function":
        p = func_node.child_by_field_name("parameter")
        if p and p.type == "identifier":
            params.append(p.text.decode("utf-8"))

    return params


def _extract_local_variables(scope_node: Any, target_line: int, metadata: Any) -> list[str]:  # noqa: C901
    """Extract variables defined within a scope up to a target line."""
    vars_found: list[str] = []

    def _handle_decl(node: Any) -> None:
        """Helper for JS/C# multiple declarators."""
        for child in node.children:
            if child.type == "variable_declarator":
                name_node = child.child_by_field_name("name")
                if name_node and name_node.type == "identifier":
                    name = name_node.text.decode("utf-8")
                    if name not in vars_found:
                        vars_found.append(name)

    def _handle_assignment(node: Any) -> None:
        left = node.child_by_field_name("left")
        if not left and node.type == "variable_declaration":
            _handle_decl(node)
        elif left and left.type == "identifier":
            name = left.text.decode("utf-8")
            if name not in vars_found and name not in metadata.skip_symbols:
                vars_found.append(name)
        elif node.type in {"lexical_declaration", "variable_declaration"}:
            _handle_decl(node)

    def walk(node: Any) -> None:  # noqa: C901
        # Stop if we passed the target line
        if node.start_point[0] > target_line:
            return

        if node.type in metadata.assignment_types:
            _handle_assignment(node)

        # Skip walking into nested scopes (they have their own local variables)
        if node != scope_node and node.type in metadata.scope_types:
            return

        for child in node.children:
            walk(child)

    walk(scope_node)
    return vars_found


@landlock_tool()
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
    metadata = get_language_metadata(language)
    if not ts_lang or not metadata:
        return f"Error: Language '{language}' not supported."

    file_path = get_config().resolve_workspace_path(file_path)
    try:
        with open(file_path, "rb") as f:
            content = f.read()

        parser = _make_parser(language)
        if parser is None:
            return f"Error: Could not create parser for {language}"
        tree = parser.parse(content)

        target_line = line_number - 1
        scopes = _find_enclosing_scopes(tree.root_node, target_line, metadata)

        if not scopes:
            return "Global scope or no enclosing function found."

        # Innermost scope
        inner_scope = scopes[-1]
        name_node = inner_scope.child_by_field_name("name")
        scope_name = name_node.text.decode("utf-8") if name_node else "anonymous"

        params = _extract_params(inner_scope, metadata)
        local_vars = _extract_local_variables(inner_scope, target_line, metadata)

        # Remove params from local_vars to avoid duplication
        local_vars = [v for v in local_vars if v not in params]

        report = [f"Scope: {scope_name} ({inner_scope.type.replace('_', ' ')})"]
        report.append(f"Parameters: {', '.join(params) if params else 'None'}")
        report.append(f"Local Variables: {', '.join(local_vars) if local_vars else 'None'}")

        # Handle outer scopes
        if len(scopes) > 1:
            outer_vars: list[str] = []
            for outer in scopes[:-1]:
                outer_vars.extend(_extract_params(outer, metadata))
                outer_vars.extend(_extract_local_variables(outer, target_line, metadata))

            # De-duplicate and remove inner params/vars
            all_inner = set(params) | set(local_vars)
            unique_outer = []
            for v in outer_vars:
                if v not in all_inner and v not in unique_outer:
                    unique_outer.append(v)

            if unique_outer:
                report.append(f"Outer Variables: {', '.join(unique_outer)}")

        return "\n".join(report)

    except Exception as e:
        return f"Error analyzing scope: {str(e)}"
