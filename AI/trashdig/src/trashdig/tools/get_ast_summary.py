from typing import Any

import trashdig.config as _config_module
from trashdig.metadata.languages import (
    get_language_metadata,
)
from trashdig.metadata.languages import (
    get_ts_language as _get_ts_language,
)
from trashdig.metadata.languages import make_parser as _make_parser
from trashdig.sandbox.landlock_tool import landlock_tool

from .base import artifact_tool


def _get_node_name(node: Any) -> str:
    """Extract name from a definition node."""
    name_node = node.child_by_field_name("name")
    if not name_node:
        for field in ("declarator", "identifier"):
            name_node = node.child_by_field_name(field)
            if name_node:
                break
    return name_node.text.decode("utf-8") if name_node else "anonymous"


def _is_js_arrow_func(node: Any, language: str) -> tuple[bool, str]:
    """Check if node is a JS arrow function definition."""
    if language not in ("javascript", "typescript", "js", "ts"):
        return False, "anonymous"
    if node.type != "lexical_declaration":
        return False, "anonymous"

    for child in node.children:
        if child.type == "variable_declarator":
            val = child.child_by_field_name("value")
            if val and val.type == "arrow_function":
                name_node = child.child_by_field_name("name")
                name = name_node.text.decode("utf-8") if name_node else "anonymous"
                return True, name
    return False, "anonymous"


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
        if parser is None:
            return f"Error: Could not create parser for {language}"
        tree = parser.parse(content)

        summary: list[str] = []

        def walk(node: Any, depth: int = 0) -> None:
            indent = "  " * depth
            is_def = False
            name = "anonymous"
            display_type = node.type.replace("_", " ").capitalize()

            if node.type in metadata.definition_types:
                is_def = True
                name = _get_node_name(node)
            else:
                is_def, name = _is_js_arrow_func(node, language)
                if is_def:
                    display_type = "Arrow function"

            if is_def:
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
