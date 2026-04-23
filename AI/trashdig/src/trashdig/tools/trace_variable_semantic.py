from typing import Any

from trashdig.metadata.languages import (
    get_language_metadata,
)
from trashdig.metadata.languages import (
    get_ts_language as _get_ts_language,
)
from trashdig.metadata.languages import make_parser as _make_parser
from trashdig.sandbox.landlock_tool import landlock_tool

from .base import artifact_tool, get_config


@artifact_tool(max_chars=5000)
@landlock_tool()
def trace_variable_semantic(variable_name: str, file_path: str, language: str = "python") -> str:
    """Traces a variable through a file using AST awareness.

    Args:
        variable_name: Name of the variable.
        file_path: Path to the file.
        language: Programming language.

    Returns:
        A list of usages and their categories.
    """
    file_path = get_config().resolve_workspace_path(file_path)
    ts_lang = _get_ts_language(language)
    metadata = get_language_metadata(language)
    if not ts_lang or not metadata:
        return f"Error: Language '{language}' not supported."

    try:
        with open(file_path, "rb") as f:
            content = f.read()

        parser = _make_parser(language)
        if parser is None:
            return f"Error: Could not create parser for {language}"
        tree = parser.parse(content)

        usages: list[str] = []

        def walk(node: Any) -> None:
            """Recursively traverses the AST to find variable usages.

            Args:
                node: The current node in the traversal.
            """
            is_match = False
            if node.type in metadata.identifier_types:
                text = node.text.decode("utf-8")
                # PHP variables start with $, but user might pass name without $
                if text == variable_name or text == f"${variable_name}":
                    # Avoid double-counting (e.g. PHP variable_name vs name child)
                    if not (
                        node.parent and node.parent.type in metadata.identifier_types
                    ):
                        is_match = True

            if is_match:
                # Determine category by looking at parent/grandparent
                category = "USAGE"
                p = node.parent
                while p and p != tree.root_node:
                    if p.type in metadata.assignment_types:
                        # Ensure it's the left side
                        left = p.child_by_field_name("left")
                        if not left:
                            left = p.child_by_field_name("name")
                        if not left:
                            left = p.child_by_field_name("declarator")
                        if not left:
                            left = p.child_by_field_name("pattern")

                        # If we matched the left side (or a descendant of it)
                        if left and (left == node or any(c == node for c in left.children)):
                            category = "ASSIGNMENT/DEFINITION"
                        break
                    if p.type in metadata.argument_types:
                        category = "SINK ARGUMENT"
                        break
                    # Don't go too far up
                    if p.type in metadata.definition_types or p.type in metadata.scope_types:
                        break
                    p = p.parent

                usages.append(f"Line {node.start_point[0] + 1}: {category}")

            for child in node.children:
                walk(child)

        walk(tree.root_node)
        return "\n".join(usages) if usages else f"Variable '{variable_name}' not found."

    except Exception as e:
        return f"Error tracing variable: {str(e)}"
