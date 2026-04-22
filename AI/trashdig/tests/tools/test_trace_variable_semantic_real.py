import os
from unittest.mock import MagicMock, patch

import pytest

from trashdig.config import Config
from trashdig.tools.trace_variable_semantic import trace_variable_semantic


@pytest.fixture(autouse=True)
def mock_workspace(tmp_path):
    c = MagicMock(spec=Config)
    c.workspace_root = str(tmp_path)
    c.resolve_workspace_path.side_effect = lambda x: os.path.abspath(x)

    with patch("trashdig.config.get_config", return_value=c), \
         patch("trashdig.tools.trace_variable_semantic.get_config", return_value=c):
        yield c

def test_trace_variable_semantic_python_real(tmp_path):
    code = """
x = 10
y = x + 5
print(x)
os.system(x)
"""
    f = tmp_path / "sample.py"
    f.write_text(code)

    result = trace_variable_semantic("x", str(f), "python")

    assert "Line 2: ASSIGNMENT/DEFINITION" in result
    assert "Line 3: USAGE" in result
    assert "Line 4: SINK ARGUMENT" in result # print(x) -> argument_list
    assert "Line 5: SINK ARGUMENT" in result # os.system(x) -> argument_list

def test_trace_variable_semantic_not_found(tmp_path):
    f = tmp_path / "sample.py"
    f.write_text("a = 1")
    result = trace_variable_semantic("x", str(f), "python")
    assert "Variable 'x' not found" in result

def test_trace_variable_semantic_unsupported():
    result = trace_variable_semantic("x", "test.py", "unsupported")
    assert "not supported" in result
