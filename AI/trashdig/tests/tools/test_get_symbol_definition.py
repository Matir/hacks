from unittest.mock import patch

from trashdig.tools.get_symbol_definition import get_symbol_definition


@patch("trashdig.tools.get_symbol_definition.ripgrep_search")
def test_get_symbol_definition(mock_rg):
    mock_rg.return_value = "def test_func():\n    pass"
    result = get_symbol_definition("test_func")
    assert "def test_func():" in result
    assert mock_rg.call_count > 0
