from typing import Any

import trashdig.config as _config_module
from trashdig.metadata.languages import get_language_metadata
from trashdig.sandbox.landlock_tool import landlock_tool

from .base import _get_ts_language, _make_parser, artifact_tool


@artifact_tool(max_chars=5000)
@landlock_tool()
def get_ast_summary(file_path: str, language: str = "python", tool_context: Any = None) -> str:
    """Generates a simplified AST summary of a file using tree-sitter.

    Args:
        file_path: Path to the file to analyze.
        language: Programming language of the file (python, javascript, go, csharp).
        tool_context: ADK context (injected).

    Returns:
        A text representation of the AST nodes (functions, classes, etc.).
    """
    ts_lang = _get_ts_language(language)
    metadata = get_language_metadata(language)

    if not ts_lang or not metadata:
        return f"Error: Language '{language}' not supported for AST analysis."

    file_path = _config_module.get_config().resolve_workspace_path(file_path)
    try:
        with open(file_path, "rb") as f:
            content = f.read()

        parser = _make_parser(language)
        assert parser is not None  # ts_lang already verified non-None above
        tree = parser.parse(content)

        summary: list[str] = []

        def walk(node: Any, depth: int = 0) -> None:
            indent = "  " * depth
            is_definition = False
            name = "anonymous"
            display_type = node.type.replace("_", " ").capitalize()

            if node.type in metadata.definition_types:
                is_definition = True
                name_node = node.child_by_field_name("name")
                if not name_node:
                    # In some languages/nodes, name might be a different field
                    # e.g. Go 'declarator', C# 'identifier'
                    for field in ("declarator", "identifier"):
                        name_node = node.child_by_field_name(field)
                        if name_node:
                            break
                if name_node:
                    name = name_node.text.decode("utf-8")

            # JavaScript arrow functions: const foo = () => {}
            elif (
                language in ("javascript", "typescript", "js", "ts")
                and node.type == "lexical_declaration"
            ):
                # Look for variable_declarator with arrow_function
                for child in node.children:
                    if child.type == "variable_declarator":
                        name_node = child.child_by_field_name("name")
                        value_node = child.child_by_field_name("value")
                        if value_node and value_node.type == "arrow_function":
                            is_definition = True
                            display_type = "Arrow function"
                            if name_node:
                                name = name_node.text.decode("utf-8")

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
        return "\n".join(summary) if summary else "No top-level definitions found."

    except Exception as e:
        return f"Error analyzing AST: {str(e)}"
