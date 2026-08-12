import os
import tempfile
from unittest.mock import patch

import pytest

from trashdig.config import Config
from trashdig.metadata.languages import (
    JAVASCRIPT_METADATA,
    PYTHON_METADATA,
    make_parser,
)
from trashdig.tools.trace_taint_cross_file import (
    _extract_callee_name,
    _get_full_callee_path,
    _module_to_file_path,
    trace_taint_cross_file,
)


@pytest.fixture(autouse=True)
def mock_cfg():
    with patch("trashdig.config.get_config") as mock:
        c = Config()
        c.data["require_sandbox"] = False
        mock.return_value = c
        yield mock


def _parse(src, lang="python"):
    return make_parser(lang).parse(src)


def test_extract_callee_name_javascript():
    tree = _parse(b"await fetch(data);", "javascript")
    expr = tree.root_node.children[0]
    await_node = expr.children[0]
    call_node = await_node.children[1]
    callee = call_node.children[0]
    path = _get_full_callee_path(callee, JAVASCRIPT_METADATA)
    assert path == ["fetch"]


def test_extract_callee_name_member():
    tree = _parse(b"obj.method(x)", "python")
    call_node = tree.root_node.children[0].children[0]
    path = _get_full_callee_path(call_node.children[0], PYTHON_METADATA)
    assert path == ["obj", "method"]
    assert _extract_callee_name(call_node.children[0]) == "method"


def test_module_to_file_path():
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "api"))
        open(os.path.join(tmp, "api", "__init__.py"), "w").close()
        open(os.path.join(tmp, "api", "db.py"), "w").close()

        current_file = os.path.join(tmp, "main.py")
        assert _module_to_file_path("api.db", tmp, current_file) == "api/db.py"

        current_file = os.path.join(tmp, "api", "user.py")
        assert _module_to_file_path(".db", tmp, current_file) == "api/db.py"


def test_trace_taint_returns_and_aliases(mock_cfg):
    with tempfile.TemporaryDirectory() as tmp:
        mock_cfg.return_value.data["workspace_root"] = tmp

        # app.py
        app_code = b"""from db import query as q
def handle(user_id):
    a = q(user_id)
    os.system(a)
"""
        with open(os.path.join(tmp, "app.py"), "wb") as f:
            f.write(app_code)

        # db.py
        db_code = b"""
def query(uid):
    return uid
"""
        with open(os.path.join(tmp, "db.py"), "wb") as f:
            f.write(db_code)

        result = trace_taint_cross_file("user_id", "app.py", tmp, "python")
        assert "POTENTIAL VULNERABILITY FOUND" in result


def test_trace_taint_go(mock_cfg):
    with tempfile.TemporaryDirectory() as tmp:
        mock_cfg.return_value.data["workspace_root"] = tmp
        src = b"""
package main
import "os/exec"
func Handle(userInput string) {
    exec.Command(userInput)
}
"""
        with open(os.path.join(tmp, "main.go"), "wb") as f:
            f.write(src)
        result = trace_taint_cross_file("userInput", "main.go", tmp, "go")
        assert "SINK" in result or "exec.Command" in result
