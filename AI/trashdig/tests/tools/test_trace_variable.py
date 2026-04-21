from unittest.mock import patch

from trashdig.tools.trace_variable import trace_variable


@patch("trashdig.tools.trace_variable.ripgrep_search")
def test_trace_variable(mock_rg):
    mock_rg.return_value = "line 5: my_var = 1"
    result = trace_variable("my_var", "test.py")
    assert "line 5: my_var = 1" in result
