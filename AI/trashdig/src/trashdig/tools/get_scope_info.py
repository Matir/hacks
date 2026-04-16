from typing import Any

from .base import _get_ts_language, _make_parser, get_config


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

        # Simple implementation: Find the parent function/method and extract parameters
        # In a real implementation, we'd walk up and find assignments too.
        # Tree-sitter line numbers are 0-indexed.
        target_line = line_number - 1
        
        def find_enclosing_function(node: Any) -> Any | None:
            """Helper to find the function node enclosing a line number.

            Args:
                node: The starting node for traversal.

            Returns:
                The enclosing function node or None.
            """
            if (
                node.type in ("function_definition", "method_definition")
                and node.start_point[0] <= target_line <= node.end_point[0]
            ):
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
        params: list[str] = []
        if params_node:
            # Simple parameter extraction
            for p in params_node.children:
                if p.type in ("identifier", "typed_parameter", "parameter_declaration"):
                    params.append(p.text.decode('utf-8'))

        return f"Function: {func_name}\nParameters: {', '.join(params) if params else 'None'}"

    except Exception as e:
        return f"Error analyzing scope: {str(e)}"
