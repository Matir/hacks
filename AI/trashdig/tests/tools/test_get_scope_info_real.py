import os
from unittest.mock import MagicMock, patch

import pytest

from trashdig.config import Config
from trashdig.tools.get_scope_info import get_scope_info


@pytest.fixture(autouse=True)
def mock_workspace(tmp_path):
    c = MagicMock(spec=Config)
    c.workspace_root = str(tmp_path)
    c.resolve_workspace_path.side_effect = os.path.abspath

    with patch("trashdig.config.get_config", return_value=c), \
         patch("trashdig.tools.get_scope_info.get_config", return_value=c):
        yield c

def test_get_scope_info_python_real(tmp_path):
    code = """
global_var = 1

def outer_func(param1):
    local_var = 2

    def inner_func(param2):
        inner_var = 3
        # TARGET LINE
        pass

    inner_func(local_var)
"""
    f = tmp_path / "sample.py"
    f.write_text(code)

    # Line numbers in get_scope_info are 0-based in the tool logic?
    # Let's check the implementation.
    # Looking at get_scope_info.py:
    # line_number = int(line_number)
    # ...
    # if node.start_point[0] <= line_number <= node.end_point[0]:

    # "pass" is on line 10 (0-indexed: line 9)
    result = get_scope_info(str(f), 9, "python")

    assert "Scope: inner_func" in result
    assert "Parameters: param2" in result
    assert "Local Variables: inner_var" in result
    assert "Outer Variables: param1, local_var" in result

def test_get_scope_info_js_real(tmp_path):
    code = """
const globalVar = 1;

function outer(p1) {
    const v1 = 2;
    const inner = (p2) => {
        const v2 = 3;
        // TARGET
    };
}
"""
    f = tmp_path / "sample.js"
    f.write_text(code)

    # // TARGET is on line 8 (0-indexed: line 7)
    result = get_scope_info(str(f), 7, "javascript")

    assert "Scope: anonymous (arrow function)" in result
    assert "Parameters: p2" in result
    assert "Local Variables: v2" in result
    assert "Outer Variables: p1, v1" in result

def test_get_scope_info_c_real(tmp_path):
    code = """
void func(int p1) {
    int v1 = 1;
    {
        int v2 = 2;
        // TARGET
    }
}
"""
    f = tmp_path / "sample.c"
    f.write_text(code)

    # // TARGET is on line 6 (0-indexed: line 5)
    result = get_scope_info(str(f), 5, "c")

    assert "Scope: anonymous (compound statement)" in result
    assert "Local Variables: v2" in result
    assert "Outer Variables: p1, v1" in result

def test_get_scope_info_java_real(tmp_path):
    code = """
class Test {
    void method(int p1) {
        int v1 = 1;
        if (true) {
            int v2 = 2;
            // TARGET
        }
    }
}
"""
    f = tmp_path / "sample.java"
    f.write_text(code)

    # // TARGET is on line 7 (0-indexed: line 6)
    result = get_scope_info(str(f), 6, "java")

    assert "Scope: anonymous (block)" in result
    assert "Local Variables: v2" in result
    assert "Outer Variables: p1, v1" in result

def test_get_scope_info_ruby_real(tmp_path):
    code = """
def method(p1)
  v1 = 1
  [1, 2].each do |p2|
    v2 = 2
    # TARGET
  end
end
"""
    f = tmp_path / "sample.rb"
    f.write_text(code)

    # # TARGET is on line 6 (0-indexed: line 5)
    result = get_scope_info(str(f), 5, "ruby")

    assert "Scope: anonymous (do block)" in result
    assert "Parameters: p2" in result
    assert "Local Variables: v2" in result
    assert "Outer Variables: p1, v1" in result

def test_get_scope_info_no_scope(tmp_path):
    f = tmp_path / "sample.py"
    f.write_text("x = 1\ny = 2")

    result = get_scope_info(str(f), 0, "python")
    assert "Global scope or no enclosing function found." in result
