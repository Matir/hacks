from typing import Any

from .base import _get_ts_language, _make_parser, artifact_tool, get_config


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

    file_path = get_config().resolve_workspace_path(file_path)
    try:
        with open(file_path, "rb") as f:
            content = f.read()

        parser = _make_parser(language)
        tree = parser.parse(content)

        summary: list[str] = []

        def walk(node: Any, depth: int = 0) -> None:
            indent = "  " * depth
            is_definition = False
            name = "anonymous"
            display_type = node.type.replace('_', ' ').capitalize()

            if node.type in ("function_definition", "class_definition", "method_definition", "function_declaration"):
                is_definition = True
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = name_node.text.decode('utf-8')
            
            # JavaScript arrow functions: const foo = () => {}
            elif language in ("javascript", "typescript", "js", "ts") and node.type == "lexical_declaration":
                # Look for variable_declarator with arrow_function
                for child in node.children:
                    if child.type == "variable_declarator":
                        name_node = child.child_by_field_name("name")
                        value_node = child.child_by_field_name("value")
                        if value_node and value_node.type == "arrow_function":
                            is_definition = True
                            display_type = "Arrow function"
                            if name_node:
                                name = name_node.text.decode('utf-8')

            if is_definition:
                summary.append(f"{indent}{display_type}: {name}")
                # Walk children with increased depth
                for child in node.children:
                    walk(child, depth + 1)
            else:
                # Just keep walking
                for child in node.children:
                    walk(child, depth)

        walk(tree.root_node)
        return "\n".join(summary) if summary else "No definitions found."

    except Exception as e:
        return f"Error analyzing AST: {str(e)}"
