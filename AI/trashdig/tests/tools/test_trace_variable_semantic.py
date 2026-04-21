from unittest.mock import MagicMock, patch

from trashdig.tools.trace_variable_semantic import trace_variable_semantic


@patch("trashdig.tools.base._get_ts_language")
@patch("tree_sitter.Parser")
def test_trace_variable_semantic(mock_parser_class, mock_get_lang):
    mock_lang = MagicMock()
    mock_get_lang.return_value = mock_lang
    mock_parser = MagicMock()
    mock_parser_class.return_value = mock_parser
    mock_tree = MagicMock()
    mock_parser.parse.return_value = mock_tree

    mock_node = MagicMock()
    mock_node.type = "identifier"
    mock_node.text = b"my_var"
    mock_node.start_point = (5, 0)
    mock_node.parent.type = "assignment"
    mock_node.children = []

    mock_tree.root_node.children = [mock_node]

    with patch("builtins.open", MagicMock()):
        result = trace_variable_semantic("my_var", "test.py", "python")
        assert "Line 6: ASSIGNMENT/DEFINITION" in result
