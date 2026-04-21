from unittest.mock import patch

from trashdig.tools.find_references import find_references


@patch("trashdig.tools.find_references.ripgrep_search")
def test_find_references(mock_rg):
    mock_rg.return_value = "file:10:5:test_func()"
    result = find_references("test_func")
    assert "file:10:5:test_func()" in result
    args = mock_rg.call_args[0]
    assert "\\btest_func\\b" in args[0]
