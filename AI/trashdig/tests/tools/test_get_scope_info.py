from unittest.mock import MagicMock, patch

from trashdig.tools.get_scope_info import get_scope_info


@patch("trashdig.metadata.languages.get_ts_language")
@patch("tree_sitter.Parser")
def test_get_scope_info(mock_parser_class, mock_get_lang):
    mock_lang = MagicMock()
    mock_get_lang.return_value = mock_lang
    mock_parser = MagicMock()
    mock_parser_class.return_value = mock_parser
    mock_tree = MagicMock()
    mock_parser.parse.return_value = mock_tree

    mock_func_node = MagicMock()
    mock_func_node.type = "function_definition"
    mock_func_node.start_point = (10, 0)
    mock_func_node.end_point = (20, 0)

    mock_name_node = MagicMock()
    mock_name_node.text = b"target_func"
    mock_func_node.child_by_field_name.return_value = mock_name_node

    mock_params_node = MagicMock()
    mock_param = MagicMock()
    mock_param.type = "identifier"
    mock_param.text = b"param1"
    mock_params_node.children = [mock_param]

    # Second call to child_by_field_name returns params
    mock_func_node.child_by_field_name.side_effect = [mock_name_node, mock_params_node]

    mock_tree.root_node.children = [mock_func_node]

    with patch("builtins.open", MagicMock()):
        result = get_scope_info("test.py", 15, "python")
        assert "Scope: target_func" in result
        assert "Parameters: param1" in result

def test_get_scope_info_unsupported_lang():
    res = get_scope_info("test.py", 10, "unsupported")
    assert "not supported" in res

@patch("trashdig.tools.get_scope_info._get_ts_language", autospec=True)
@patch("trashdig.tools.get_scope_info.get_language_metadata", autospec=True)
def test_get_scope_info_error(mock_metadata, mock_ts_lang):
    mock_ts_lang.return_value = MagicMock()
    mock_metadata.return_value = MagicMock()
    # Mocking open to raise an exception
    with patch("builtins.open", side_effect=Exception("Disk error")):
        res = get_scope_info("test.py", 10, "python")
        assert "Error analyzing scope: Disk error" in res

@patch("trashdig.tools.get_scope_info._get_ts_language", autospec=True)
@patch("trashdig.tools.get_scope_info.get_language_metadata", autospec=True)
@patch("trashdig.tools.get_scope_info._make_parser", autospec=True)
def test_get_scope_info_complex_params(mock_parser_make, mock_metadata, mock_ts_lang):
    mock_ts_lang.return_value = MagicMock()
    meta = MagicMock()
    meta.scope_types = ["function_definition"]
    meta.parameter_types = ["typed_parameter", "parameter_declaration"]
    meta.skip_symbols = []
    mock_metadata.return_value = meta

    parser = MagicMock()
    mock_parser_make.return_value = parser
    tree = MagicMock()
    parser.parse.return_value = tree

    func_node = MagicMock()
    func_node.type = "function_definition"
    func_node.start_point = (0, 0)
    func_node.end_point = (10, 0)

    params_node = MagicMock()
    # One simple identifier
    p1 = MagicMock()
    p1.type = "identifier"
    p1.text = b"a"
    # One complex parameter
    p2 = MagicMock()
    p2.type = "typed_parameter"
    p2_inner = MagicMock()
    p2_inner.type = "identifier"
    p2_inner.text = b"b"
    p2.children = [p2_inner]

    params_node.children = [p1, p2]
    func_node.child_by_field_name.side_effect = lambda f: params_node if f == "parameters" else None

    tree.root_node.children = [func_node]

    with patch("builtins.open", MagicMock()):
        res = get_scope_info("test.py", 5, "python")
        assert "Parameters: a, b" in res

@patch("trashdig.tools.get_scope_info._get_ts_language", autospec=True)
@patch("trashdig.tools.get_scope_info.get_language_metadata", autospec=True)
@patch("trashdig.tools.get_scope_info._make_parser", autospec=True)
def test_get_scope_info_nested(mock_parser_make, mock_metadata, mock_ts_lang):
    mock_ts_lang.return_value = MagicMock()
    meta = MagicMock()
    meta.scope_types = ["function_definition"]
    meta.assignment_types = ["assignment"]
    meta.parameter_types = []
    meta.skip_symbols = []
    meta.name = "python"
    mock_metadata.return_value = meta

    parser = MagicMock()
    mock_parser_make.return_value = parser
    tree = MagicMock()
    parser.parse.return_value = tree

    # Outer function
    outer = MagicMock()
    outer.type = "function_definition"
    outer.start_point = (0, 0)
    outer.end_point = (20, 0)
    outer_name = MagicMock()
    outer_name.text = b"outer"

    # Local var in outer
    assign = MagicMock()
    assign.type = "assignment"
    assign.start_point = (5, 0)
    left = MagicMock()
    left.type = "identifier"
    left.text = b"v1"
    assign.child_by_field_name.return_value = left
    assign.children = []

    # Inner function
    inner = MagicMock()
    inner.type = "function_definition"
    inner.start_point = (10, 0)
    inner.end_point = (15, 0)
    inner_name = MagicMock()
    inner_name.text = b"inner"
    inner.children = []

    outer.children = [assign, inner]
    tree.root_node.children = [outer]

    outer.child_by_field_name.side_effect = lambda f: outer_name if f == "name" else None
    inner.child_by_field_name.side_effect = lambda f: inner_name if f == "name" else None

    with patch("builtins.open", MagicMock()):
        # Analyzing line 12 (inside inner)
        res = get_scope_info("test.py", 12, "python")
        assert "Scope: inner" in res
        assert "Outer Variables: v1" in res
