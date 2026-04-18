from typing import Any

from trashdig.metadata.languages import get_language_metadata
from trashdig.sandbox.landlock_tool import landlock_tool

from .base import _get_ts_language, _make_parser, artifact_tool, get_config


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
        assert parser is not None  # ts_lang already verified non-None above
        tree = parser.parse(content)

        usages: list[str] = []

        def walk(node: Any) -> None:
            """Recursively traverses the AST to find variable usages.

            Args:
                node: The current node in the traversal.
            """
            if node.type == "identifier" and node.text.decode("utf-8") == variable_name:
                parent = node.parent
                category = "USAGE"
                if parent:
                    if parent.type in metadata.assignment_types:
                        category = "ASSIGNMENT/DEFINITION"
                    elif parent.type == "argument_list":
                        category = "SINK ARGUMENT"

                usages.append(f"Line {node.start_point[0] + 1}: {category}")

            for child in node.children:
                walk(child)

        walk(tree.root_node)
        return "\n".join(usages) if usages else f"Variable '{variable_name}' not found."

    except Exception as e:
        return f"Error tracing variable: {str(e)}"
