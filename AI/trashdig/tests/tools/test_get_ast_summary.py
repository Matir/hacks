from unittest.mock import MagicMock, patch

from trashdig.tools.get_ast_summary import get_ast_summary


@patch("trashdig.metadata.languages.get_ts_language")
@patch("tree_sitter.Parser")
def test_get_ast_summary(mock_parser_class, mock_get_lang):
    mock_lang = MagicMock()
    mock_get_lang.return_value = mock_lang

    mock_parser = MagicMock()
    mock_parser_class.return_value = mock_parser

    mock_tree = MagicMock()
    mock_parser.parse.return_value = mock_tree

    mock_node = MagicMock()
    mock_node.type = "function_definition"
    mock_name_node = MagicMock()
    mock_name_node.text = b"test_func"
    mock_node.child_by_field_name.return_value = mock_name_node

    mock_tree.root_node.children = [mock_node]

    with patch("builtins.open", MagicMock()):
        result = get_ast_summary("test.py", "python")
        assert "Function definition: test_func" in result

def test_get_ast_summary_unsupported_lang():
    result = get_ast_summary("test.py", "unsupported")
    assert "not supported" in result

@patch("trashdig.tools.get_ast_summary._get_ts_language", autospec=True)
@patch("trashdig.tools.get_ast_summary.get_language_metadata", autospec=True)
def test_get_ast_summary_error(mock_metadata, mock_ts_lang):
    mock_ts_lang.return_value = MagicMock()
    mock_metadata.return_value = MagicMock()
    with patch("builtins.open", side_effect=Exception("Disk error")):
        res = get_ast_summary("test.py", "python")
        assert "Error analyzing AST: Disk error" in res

@patch("trashdig.tools.get_ast_summary._get_ts_language", autospec=True)
@patch("trashdig.tools.get_ast_summary.get_language_metadata", autospec=True)
@patch("trashdig.tools.get_ast_summary._make_parser", autospec=True)
def test_get_ast_summary_js_arrow(mock_parser_make, mock_metadata, mock_ts_lang):
    mock_ts_lang.return_value = MagicMock()
    meta = MagicMock()
    meta.definition_types = ["function_definition"]
    mock_metadata.return_value = meta

    parser = MagicMock()
    mock_parser_make.return_value = parser

    tree = MagicMock()
    parser.parse.return_value = tree

    # Mocking JS arrow function structure
    # const foo = () => {}
    # lexical_declaration -> variable_declarator -> name: foo, value: arrow_function
    node = MagicMock()
    node.type = "lexical_declaration"

    decl = MagicMock()
    decl.type = "variable_declarator"
    name_node = MagicMock()
    name_node.type = "identifier"
    name_node.text = b"foo"
    val_node = MagicMock()
    val_node.type = "arrow_function"

    decl.child_by_field_name.side_effect = lambda f: name_node if f == "name" else val_node if f == "value" else None
    node.children = [decl]
    tree.root_node.children = [node]

    with patch("builtins.open", MagicMock()):
        res = get_ast_summary("test.js", "javascript")
        assert "Arrow function: foo" in res

def test_get_ast_summary_no_definitions():
    """Test get_ast_summary with a file containing no classes or functions."""
    with patch("builtins.open", MagicMock()):
        with patch("trashdig.metadata.languages.get_ts_language", return_value=MagicMock()):

            with patch("tree_sitter.Parser") as mock_parser_class:
                mock_parser = mock_parser_class.return_value
                mock_tree = mock_parser.parse.return_value
                mock_tree.root_node.children = [] # No children

                result = get_ast_summary("empty.py", "python")
                assert result == "No top-level definitions found."
