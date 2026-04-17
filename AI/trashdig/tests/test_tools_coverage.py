import json
import sqlite3
from unittest.mock import MagicMock, patch

import pytest

from trashdig.agents.types import TaskType
from trashdig.tools.detect_frameworks import detect_frameworks
from trashdig.tools.exit_loop import exit_loop
from trashdig.tools.get_next_hypothesis import get_next_hypothesis
from trashdig.tools.get_project_structure import get_project_structure
from trashdig.tools.read_file import read_file
from trashdig.tools.save_findings import save_findings
from trashdig.tools.save_hypotheses import save_hypotheses
from trashdig.tools.update_hypothesis_status import update_hypothesis_status
from trashdig.tools.get_ast_summary import get_ast_summary
from trashdig.tools.get_scope_info import get_scope_info
from trashdig.config import Config
from google.adk.tools import ToolContext


@pytest.fixture(autouse=True)
def mock_cfg():
    c = Config(config_path="")
    c.data["require_sandbox"] = False
    with patch("trashdig.config.get_config", autospec=True, return_value=c), \
         patch("trashdig.config._GLOBAL_CONFIG", c):
        yield c

@pytest.fixture
def mock_db():
    db = MagicMock()
    with patch("trashdig.tools.save_findings.get_database", autospec=True, return_value=db), \
         patch("trashdig.tools.save_hypotheses.get_database", autospec=True, return_value=db):
        yield db

def test_save_findings(mock_db):
    findings = [
        {"title": "SQLi", "severity": "High", "file_path": "a.py"},
        {"title": "XSS"}
    ]
    res = save_findings(json.dumps(findings), "/tmp/proj")
    assert "Saved 2 findings" in res
    assert mock_db.save_finding.call_count == 2

def test_save_findings_single_object(mock_db):
    finding = {"title": "SQLi"}
    res = save_findings(json.dumps(finding), "/tmp/proj")
    assert "Saved 1 findings" in res
    mock_db.save_finding.assert_called_once()

def test_save_findings_error():
    res = save_findings("invalid json", "/tmp/proj")
    assert "Error saving findings" in res

def test_save_hypotheses(mock_db):
    hypos = [
        {"target": "a.py", "description": "desc1", "confidence": 0.9},
        {"target": "b.py", "description": "desc2"}
    ]
    res = save_hypotheses(json.dumps(hypos), "/tmp/proj")
    assert "Saved 2 hypotheses" in res
    assert mock_db.save_hypothesis.call_count == 2
    
    # Verify TaskType.HUNT was used
    args = mock_db.save_hypothesis.call_args_list[0][0]
    assert args[1].type == TaskType.HUNT

def test_save_hypotheses_error():
    res = save_hypotheses("invalid json", "/tmp/proj")
    assert "Error saving hypotheses" in res

def test_update_hypothesis_status(tmp_path):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE hypotheses (task_id TEXT, status TEXT, updated_at TEXT)")
    conn.execute("INSERT INTO hypotheses (task_id, status) VALUES ('task1', 'pending')")
    conn.commit()
    conn.close()

    res = update_hypothesis_status("task1", "completed", db_path=str(db_path))
    assert "updated to completed" in res

    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT status FROM hypotheses WHERE task_id='task1'").fetchone()
    assert row[0] == "completed"
    conn.close()

def test_update_hypothesis_status_error():
    res = update_hypothesis_status("task1", "completed", db_path="/nonexistent/path/db.db")
    assert "Error updating database" in res

def test_get_next_hypothesis(tmp_path):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE hypotheses (task_id TEXT, project_path TEXT, status TEXT, confidence REAL)")
    conn.execute("INSERT INTO hypotheses (task_id, project_path, status, confidence) VALUES ('t1', '/p', 'pending', 0.8)")
    conn.execute("INSERT INTO hypotheses (task_id, project_path, status, confidence) VALUES ('t2', '/p', 'pending', 0.9)")
    conn.commit()
    conn.close()

    res = get_next_hypothesis("/p", db_path=str(db_path))
    data = json.loads(res)
    assert data["task_id"] == "t2" # Highest confidence

def test_get_next_hypothesis_none(tmp_path):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE hypotheses (task_id TEXT, project_path TEXT, status TEXT, confidence REAL)")
    conn.commit()
    conn.close()

    res = get_next_hypothesis("/p", db_path=str(db_path))
    assert res == "None"

def test_get_next_hypothesis_error():
    res = get_next_hypothesis("/p", db_path="/nonexistent/db.db")
    assert "Error accessing database" in res

def test_read_file(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("hello world")
    assert read_file(str(f)) == "hello world"

def test_read_file_error():
    res = read_file("/nonexistent/file")
    assert "Error reading file" in res

@patch("trashdig.tools.get_project_structure._get_struct", autospec=True)
def test_get_project_structure(mock_get_struct):
    mock_get_struct.return_value = ["a.py", "b.py"]
    res = get_project_structure(".")
    assert res == "a.py\nb.py"

@patch("trashdig.tools.detect_frameworks._get_struct", autospec=True)
@patch("trashdig.tools.detect_frameworks._detect", autospec=True)
def test_detect_frameworks(mock_detect, mock_get_struct):
    mock_get_struct.return_value = ["package.json"]
    mock_detect.return_value = {"web": ["Express"]}
    res = detect_frameworks(".")
    assert json.loads(res) == {"web": ["Express"]}

def test_exit_loop():
    mock_ctx = MagicMock(spec=ToolContext)
    mock_ctx.actions = MagicMock()
    res = exit_loop(mock_ctx)
    assert res == "Loop exit requested."
    assert mock_ctx.actions.escalate is True

def test_exit_loop_no_actions():
    # Should not crash if actions attribute is missing
    res = exit_loop(object())
    assert res == "Loop exit requested."

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

@patch("trashdig.tools.get_ast_summary._get_ts_language", autospec=True)
@patch("trashdig.tools.get_ast_summary.get_language_metadata", autospec=True)
def test_get_ast_summary_error(mock_metadata, mock_ts_lang):
    mock_ts_lang.return_value = MagicMock()
    mock_metadata.return_value = MagicMock()
    with patch("builtins.open", side_effect=Exception("Disk error")):
        res = get_ast_summary("test.py", "python")
        assert "Error analyzing AST: Disk error" in res

def test_get_ast_summary_unsupported_lang():
    res = get_ast_summary("test.py", "unsupported")
    assert "not supported" in res

@patch("trashdig.tools.get_ast_summary._get_ts_language", autospec=True)
@patch("trashdig.tools.get_ast_summary.get_language_metadata", autospec=True)
@patch("trashdig.tools.get_ast_summary._make_parser", autospec=True)
def test_get_ast_summary_js_arrow(mock_parser_make, mock_metadata, mock_ts_lang):
    mock_ts_lang.return_value = MagicMock()
    meta = MagicMock()
    meta.definition_types = ["function_definition"]
    mock_metadata.return_value = meta
    
    parser = MagicMock()
    mock_parser_make.return_value = parser
    
    tree = MagicMock()
    parser.parse.return_value = tree
    
    # Mocking JS arrow function structure
    # const foo = () => {}
    # lexical_declaration -> variable_declarator -> name: foo, value: arrow_function
    node = MagicMock()
    node.type = "lexical_declaration"
    
    decl = MagicMock()
    decl.type = "variable_declarator"
    name_node = MagicMock()
    name_node.type = "identifier"
    name_node.text = b"foo"
    val_node = MagicMock()
    val_node.type = "arrow_function"
    
    decl.child_by_field_name.side_effect = lambda f: name_node if f == "name" else val_node if f == "value" else None
    node.children = [decl]
    tree.root_node.children = [node]

    with patch("builtins.open", MagicMock()):
        res = get_ast_summary("test.js", "javascript")
        assert "Arrow function: foo" in res

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
