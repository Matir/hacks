import os
from unittest.mock import MagicMock, patch

import pytest

from trashdig.config import Config
from trashdig.tools.trace_variable_semantic import trace_variable_semantic


@pytest.fixture(autouse=True)
def mock_workspace(tmp_path):
    c = MagicMock(spec=Config)
    c.workspace_root = str(tmp_path)
    c.resolve_workspace_path.side_effect = os.path.abspath

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

def test_trace_variable_semantic_rust_real(tmp_path):
    code = """
let x = "danger";
Command::new("sh").spawn(x);
"""
    f = tmp_path / "sample.rs"
    f.write_text(code)

    result = trace_variable_semantic("x", str(f), "rust")

    assert "Line 2: ASSIGNMENT/DEFINITION" in result
    assert "Line 3: SINK ARGUMENT" in result

def test_trace_variable_semantic_php_real(tmp_path):
    code = """
<?php
$x = $_GET['x'];
system($x);
?>
"""
    f = tmp_path / "sample.php"
    f.write_text(code)

    result = trace_variable_semantic("x", str(f), "php")

    # PHP identifier is '$x' in the AST?
    # Actually, tree-sitter-php might use 'variable_name' or just 'variable'
    # Let's check.
    assert "Line 3: ASSIGNMENT/DEFINITION" in result
    assert "Line 4: SINK ARGUMENT" in result

def test_trace_variable_semantic_not_found(tmp_path):
    f = tmp_path / "sample.py"
    f.write_text("a = 1")
    result = trace_variable_semantic("x", str(f), "python")
    assert "Variable 'x' not found" in result

def test_trace_variable_semantic_unsupported():
    result = trace_variable_semantic("x", "test.py", "unsupported")
    assert "not supported" in result
