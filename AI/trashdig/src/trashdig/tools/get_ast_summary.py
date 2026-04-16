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
        root_node = tree.root_node
        
        for node in root_node.children:
            if node.type in ("function_definition", "class_definition", "method_definition"):
                name_node = node.child_by_field_name("name")
                name = name_node.text.decode('utf-8') if name_node else "anonymous"
                summary.append(f"{node.type.replace('_', ' ').capitalize()}: {name}")
                
        return "\n".join(summary) if summary else "No top-level definitions found."

    except Exception as e:
        return f"Error analyzing AST: {str(e)}"
