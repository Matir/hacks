from typing import Any

from .base import _get_ts_language, _make_parser, get_config


def _find_enclosing_scopes(node: Any, target_line: int, language: str) -> list[Any]:
    """Finds all scope-defining nodes enclosing a line number (innermost last)."""
    scopes = []
    
    # Types that define a scope
    scope_types = ("function_definition", "method_definition", "function_declaration", "class_definition")
    if language in ("javascript", "typescript", "js", "ts"):
        scope_types += ("arrow_function",)

    if (
        node.type in scope_types
        and node.start_point[0] <= target_line <= node.end_point[0]
    ):
        scopes.append(node)
    
    for child in node.children:
        res = _find_enclosing_scopes(child, target_line, language)
        if res:
            scopes.extend(res)
            # Since we only check children if the parent might contain the line,
            # and we want innermost last, this works.
    return scopes


def _extract_params(func_node: Any) -> list[str]:
    """Extract parameter names from a function node."""
    params: list[str] = []
    
    # Standard parameters field
    params_node = func_node.child_by_field_name("parameters")
    if params_node:
        for p in params_node.children:
            # Python/JS/Go identifiers
            if p.type == "identifier":
                params.append(p.text.decode('utf-8'))
            # JS formal_parameters children might be identifiers
            elif p.type in ("typed_parameter", "parameter_declaration", "formal_parameter"):
                 # Recursive check for identifier in these types
                 for child in p.children:
                     if child.type == "identifier":
                         params.append(child.text.decode('utf-8'))
                         break
    
    # JS Arrow function might have a single identifier as param instead of parameter_list
    if not params and func_node.type == "arrow_function":
        p = func_node.child_by_field_name("parameter")
        if p and p.type == "identifier":
            params.append(p.text.decode('utf-8'))

    return params


def _extract_local_variables(scope_node: Any, target_line: int) -> list[str]:
    """Extract variables defined within a scope up to a target line."""
    vars_found: list[str] = []

    def walk(node: Any) -> None:
        # Stop if we passed the target line
        if node.start_point[0] > target_line:
            return

        # Python/JS assignment: x = ...
        if node.type == "assignment":
            left = node.child_by_field_name("left")
            if left and left.type == "identifier":
                name = left.text.decode('utf-8')
                if name not in vars_found:
                    vars_found.append(name)
        
        # JS Lexical declaration: const x = ...
        elif node.type in ("lexical_declaration", "variable_declaration"):
            for child in node.children:
                if child.type == "variable_declarator":
                    name_node = child.child_by_field_name("name")
                    if name_node and name_node.type == "identifier":
                        name = name_node.text.decode('utf-8')
                        if name not in vars_found:
                            vars_found.append(name)

        # Skip walking into nested scopes (they have their own local variables)
        if node != scope_node and node.type in ("function_definition", "method_definition", "arrow_function"):
            return

        for child in node.children:
            walk(child)

    walk(scope_node)
    return vars_found


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

    file_path = get_config().resolve_workspace_path(file_path)
    try:
        with open(file_path, "rb") as f:
            content = f.read()

        parser = _make_parser(language)
        tree = parser.parse(content)

        target_line = line_number - 1
        scopes = _find_enclosing_scopes(tree.root_node, target_line, language)

        if not scopes:
            return "Global scope or no enclosing function found."

        # Innermost scope
        inner_scope = scopes[-1]
        name_node = inner_scope.child_by_field_name("name")
        # For arrow functions, name might be in the parent assignment, but we'll stick to anonymous for now
        scope_name = name_node.text.decode('utf-8') if name_node else "anonymous"
        
        params = _extract_params(inner_scope)
        local_vars = _extract_local_variables(inner_scope, target_line)
        
        # Remove params from local_vars to avoid duplication
        local_vars = [v for v in local_vars if v not in params]

        report = [f"Scope: {scope_name} ({inner_scope.type.replace('_', ' ')})"]
        report.append(f"Parameters: {', '.join(params) if params else 'None'}")
        report.append(f"Local Variables: {', '.join(local_vars) if local_vars else 'None'}")

        # Handle outer scopes
        if len(scopes) > 1:
            outer_vars: list[str] = []
            for outer in scopes[:-1]:
                outer_vars.extend(_extract_params(outer))
                outer_vars.extend(_extract_local_variables(outer, target_line))
            
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
