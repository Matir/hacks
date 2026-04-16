"""Tests for cross-file taint analysis (trace_taint_cross_file and helpers)."""

import os
import tempfile
from unittest.mock import patch

import pytest

from trashdig.config import Config
from trashdig.tools import trace_taint_cross_file
from trashdig.tools.base import _make_parser
from trashdig.tools.trace_taint_cross_file import (
    _node_contains_identifier,
    _extract_callee_name,
    _find_calls_passing_variable,
    _find_returns_variable,
    _find_function_files,
    _resolve_param_name,
)

@pytest.fixture(autouse=True)
def mock_cfg():
    with patch("trashdig.config.get_config") as mock:
        mock.return_value = Config(require_sandbox=False)
        yield mock


# ---------------------------------------------------------------------------
# Helpers – _node_contains_identifier, _extract_callee_name
# ---------------------------------------------------------------------------

def _parse_python(src: bytes):
    parser = _make_parser("python")
    return parser.parse(src)


def test_node_contains_identifier_found():
    tree = _parse_python(b"user_id + 1")
    assert _node_contains_identifier(tree.root_node, "user_id")


def test_node_contains_identifier_not_found():
    tree = _parse_python(b"other_var + 1")
    assert not _node_contains_identifier(tree.root_node, "user_id")


def test_extract_callee_name_simple():
    tree = _parse_python(b"fetch(user_id)")
    # The root -> expression_statement -> call
    call_node = tree.root_node.children[0].children[0]
    assert call_node.type == "call"
    callee_node = call_node.children[0]
    assert _extract_callee_name(callee_node) == "fetch"


def test_extract_callee_name_attribute():
    tree = _parse_python(b"cursor.execute(query)")
    call_node = tree.root_node.children[0].children[0]
    callee_node = call_node.children[0]
    assert _extract_callee_name(callee_node) == "execute"


# ---------------------------------------------------------------------------
# _find_calls_passing_variable
# ---------------------------------------------------------------------------

def test_find_calls_passing_variable_simple():
    src = b"result = fetch(user_id)\n"
    calls = _find_calls_passing_variable("user_id", src, "python")
    assert len(calls) == 1
    callee, idx, line = calls[0]
    assert callee == "fetch"
    assert idx == 0
    assert line == 1


def test_find_calls_passing_variable_second_arg():
    src = b"run(cmd, user_id, timeout=5)\n"
    calls = _find_calls_passing_variable("user_id", src, "python")
    assert any(c[0] == "run" and c[1] == 1 for c in calls)


def test_find_calls_passing_variable_sink():
    src = b"os.system(user_input)\n"
    calls = _find_calls_passing_variable("user_input", src, "python")
    assert len(calls) == 1
    callee, idx, line = calls[0]
    assert callee == "system"
    assert idx == 0


def test_find_calls_passing_variable_no_match():
    src = b"print('hello')\n"
    calls = _find_calls_passing_variable("user_id", src, "python")
    assert calls == []


def test_find_calls_passing_variable_multiple():
    src = b"a(x)\nb(x)\nc(y)\n"
    calls = _find_calls_passing_variable("x", src, "python")
    callees = [c[0] for c in calls]
    assert "a" in callees
    assert "b" in callees
    assert "c" not in callees


# ---------------------------------------------------------------------------
# _find_returns_variable
# ---------------------------------------------------------------------------

def test_find_returns_variable_found():
    src = b"def f(x):\n    return x\n"
    lines = _find_returns_variable("x", src, "python")
    assert 2 in lines


def test_find_returns_variable_not_found():
    src = b"def f(x):\n    return 42\n"
    lines = _find_returns_variable("x", src, "python")
    assert lines == []


# ---------------------------------------------------------------------------
# _find_function_files
# ---------------------------------------------------------------------------

def test_find_function_files_found():
    with tempfile.TemporaryDirectory() as tmp:
        target = os.path.join(tmp, "db.py")
        with open(target, "w") as f:
            f.write("def fetch_user(user_id):\n    pass\n")

        result = _find_function_files("fetch_user", tmp, "python")
        assert "db.py" in result


def test_find_function_files_not_found():
    with tempfile.TemporaryDirectory() as tmp:
        result = _find_function_files("nonexistent_func", tmp, "python")
        assert result == []


# ---------------------------------------------------------------------------
# _resolve_param_name
# ---------------------------------------------------------------------------

def test_resolve_param_name():
    with tempfile.TemporaryDirectory() as tmp:
        src_file = os.path.join(tmp, "db.py")
        with open(src_file, "wb") as f:
            f.write(b"def fetch_user(conn, user_id):\n    pass\n")

        # user_id is at index 1 (excluding self — but no self here so it's raw index 1)
        name = _resolve_param_name("fetch_user", 1, src_file, "python")
        assert name == "user_id"


def test_resolve_param_name_first():
    with tempfile.TemporaryDirectory() as tmp:
        src_file = os.path.join(tmp, "lib.py")
        with open(src_file, "wb") as f:
            f.write(b"def process(data, timeout=30):\n    pass\n")

        name = _resolve_param_name("process", 0, src_file, "python")
        assert name == "data"


def test_resolve_param_name_out_of_range():
    with tempfile.TemporaryDirectory() as tmp:
        src_file = os.path.join(tmp, "lib.py")
        with open(src_file, "wb") as f:
            f.write(b"def f(x):\n    pass\n")

        assert _resolve_param_name("f", 5, src_file, "python") is None


def test_resolve_param_name_skips_self():
    with tempfile.TemporaryDirectory() as tmp:
        src_file = os.path.join(tmp, "cls.py")
        with open(src_file, "wb") as f:
            f.write(b"class DB:\n    def execute(self, query):\n        pass\n")

        name = _resolve_param_name("execute", 0, src_file, "python")
        assert name == "query"


# ---------------------------------------------------------------------------
# trace_taint_cross_file – integration scenarios
# ---------------------------------------------------------------------------

def test_taint_reaches_sink_directly():
    """Variable passed directly to a known sink in the same file."""
    with tempfile.TemporaryDirectory() as tmp:
        src_file = os.path.join(tmp, "app.py")
        with open(src_file, "wb") as f:
            f.write(
                b"import os\n"
                b"def handle(user_input):\n"
                b"    os.system(user_input)\n"
            )

        result = trace_taint_cross_file(
            variable="user_input",
            source_file="app.py",
            project_root=tmp,
            language="python",
        )
        assert "SINK" in result
        assert "system" in result
        assert "POTENTIAL VULNERABILITY FOUND" in result


def test_taint_crosses_one_file_to_sink():
    """Variable flows from entry file into a callee that calls a sink."""
    with tempfile.TemporaryDirectory() as tmp:
        # Entry file: calls db_query(user_id)
        with open(os.path.join(tmp, "routes.py"), "wb") as f:
            f.write(
                b"from db import db_query\n"
                b"def get_user(user_id):\n"
                b"    return db_query(user_id)\n"
            )
        # Callee file: passes its param directly to execute (a sink)
        with open(os.path.join(tmp, "db.py"), "wb") as f:
            f.write(
                b"def db_query(uid):\n"
                b"    cursor.execute(uid)\n"
            )

        result = trace_taint_cross_file(
            variable="user_id",
            source_file="routes.py",
            project_root=tmp,
            language="python",
        )
        assert "SINK" in result
        assert "execute" in result
        assert "POTENTIAL VULNERABILITY FOUND" in result


def test_taint_safe_path():
    """Variable that is never passed to a sink should report safe."""
    with tempfile.TemporaryDirectory() as tmp:
        with open(os.path.join(tmp, "app.py"), "wb") as f:
            f.write(
                b"def handle(user_input):\n"
                b"    result = len(user_input)\n"
                b"    return result\n"
            )

        result = trace_taint_cross_file(
            variable="user_input",
            source_file="app.py",
            project_root=tmp,
            language="python",
        )
        assert "POTENTIAL VULNERABILITY FOUND" not in result
        assert "RESULT" in result


def test_taint_max_depth_respected():
    """Depth limit prevents infinite recursion through a chain of files."""
    with tempfile.TemporaryDirectory() as tmp:
        # a.py calls hop_b(x), b.py defines hop_b and calls hop_c(x), etc.
        # With max_depth=1 the tracer should stop after one hop.
        with open(os.path.join(tmp, "a.py"), "wb") as f:
            f.write(b"def start(x):\n    hop_b(x)\n")
        with open(os.path.join(tmp, "b.py"), "wb") as f:
            f.write(b"def hop_b(x):\n    hop_c(x)\n")
        with open(os.path.join(tmp, "c.py"), "wb") as f:
            f.write(b"def hop_c(x):\n    pass\n")

        result = trace_taint_cross_file(
            variable="x",
            source_file="a.py",
            project_root=tmp,
            language="python",
            max_depth=1,
        )
        assert "max depth" in result


def test_taint_cycle_detection():
    """Cycle between two files does not cause infinite recursion."""
    with tempfile.TemporaryDirectory() as tmp:
        with open(os.path.join(tmp, "a.py"), "wb") as f:
            f.write(b"def fa(x):\n    fb(x)\n")
        with open(os.path.join(tmp, "b.py"), "wb") as f:
            f.write(b"def fb(x):\n    fa(x)\n")

        result = trace_taint_cross_file(
            variable="x",
            source_file="a.py",
            project_root=tmp,
            language="python",
            max_depth=10,
        )
        assert "cycle detected" in result


def test_taint_external_library_call_noted():
    """Calls to symbols not found in the project are noted but don't crash."""
    with tempfile.TemporaryDirectory() as tmp:
        with open(os.path.join(tmp, "app.py"), "wb") as f:
            f.write(b"def handle(data):\n    some_external_lib_fn(data)\n")

        result = trace_taint_cross_file(
            variable="data",
            source_file="app.py",
            project_root=tmp,
            language="python",
        )
        # Should note the call but not crash
        assert "some_external_lib_fn" in result or "not found in project" in result


def test_taint_unsupported_language():
    """Unsupported language returns a graceful error, not an exception."""
    with tempfile.TemporaryDirectory() as tmp:
        with open(os.path.join(tmp, "app.rb"), "wb") as f:
            f.write(b"# ruby file\n")
        # _make_parser returns None for unsupported languages, trace should handle it
        result = trace_taint_cross_file(
            variable="x",
            source_file="app.rb",
            project_root=tmp,
            language="ruby",  # unsupported
        )
        # Should produce some output without crashing
        assert isinstance(result, str)
