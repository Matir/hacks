import subprocess
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from trashdig.config import Config
from trashdig.tools import (
    bash_tool,
    container_bash_tool,
    find_references,
    get_ast_summary,
    get_scope_info,
    get_symbol_definition,
    query_cwe_database,
    ripgrep_search,
    semgrep_scan,
    trace_variable,
    trace_variable_semantic,
    web_fetch,
)
from trashdig.utils import set_binary_stub


@pytest.fixture(autouse=True)
def mock_cfg():
    with patch("trashdig.config.get_config") as mock:
        mock.return_value = Config(require_sandbox=False)
        yield mock

@patch("subprocess.run")
def test_ripgrep_search(mock_run):
    mock_run.return_value = MagicMock(stdout="file:1:1:content", stderr="", returncode=0)
    
    result = ripgrep_search("pattern", "path")
    assert result == "file:1:1:content"
    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert "rg" in args
    assert "pattern" in args
    assert "path" in args

@patch("subprocess.run")
def test_ripgrep_search_not_found(mock_run):
    mock_run.side_effect = FileNotFoundError
    result = ripgrep_search("pattern")
    assert "not found in PATH" in result

@patch("subprocess.run")
def test_semgrep_scan(mock_run):
    mock_run.return_value = MagicMock(stdout='{"results": []}', stderr="", returncode=0)
    
    result = semgrep_scan("path")
    assert result == '{"results": []}'
    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert "semgrep" in args
    assert "path" in args

@patch("subprocess.run")
def test_semgrep_scan_timeout(mock_run):
    mock_run.side_effect = subprocess.TimeoutExpired(cmd=["semgrep"], timeout=120)
    result = semgrep_scan("path")
    assert "timed out" in result

@patch("trashdig.tools.base._get_ts_language")
@patch("tree_sitter.Parser")
def test_get_ast_summary(mock_parser_class, mock_get_lang):
    mock_lang = MagicMock()
    mock_get_lang.return_value = mock_lang
    
    mock_parser = MagicMock()
    mock_parser_class.return_value = mock_parser
    
    mock_tree = MagicMock()
    mock_parser.parse.return_value = mock_tree
    
    mock_node = MagicMock()
    mock_node.type = "function_definition"
    mock_name_node = MagicMock()
    mock_name_node.text = b"test_func"
    mock_node.child_by_field_name.return_value = mock_name_node
    
    mock_tree.root_node.children = [mock_node]
    
    with patch("builtins.open", MagicMock()):
        result = get_ast_summary("test.py", "python")
        assert "Function definition: test_func" in result

def test_get_ast_summary_unsupported_lang():
    result = get_ast_summary("test.py", "unsupported")
    assert "not supported" in result

@patch("trashdig.tools.get_symbol_definition.ripgrep_search")
def test_get_symbol_definition(mock_rg):
    mock_rg.return_value = "def test_func():\n    pass"
    result = get_symbol_definition("test_func")
    assert "def test_func():" in result
    assert mock_rg.call_count > 0

@patch("trashdig.tools.find_references.ripgrep_search")
def test_find_references(mock_rg):
    mock_rg.return_value = "file:10:5:test_func()"
    result = find_references("test_func")
    assert "file:10:5:test_func()" in result
    args = mock_rg.call_args[0]
    assert "\\btest_func\\b" in args[0]

@patch("subprocess.run")
def test_bash_tool(mock_run):
    mock_run.return_value = MagicMock(stdout="output", stderr="error", returncode=0)
    result = bash_tool("ls")
    assert "STDOUT:\noutput" in result
    assert "STDERR:\nerror" in result
    assert "Exit Code: 0" in result

@patch("subprocess.run")
def test_container_bash_tool_docker_available(mock_run):
    set_binary_stub("docker", True)
    # Mock docker run ...
    mock_run.return_value = MagicMock(stdout="container output", stderr="", returncode=0)
    
    result = container_bash_tool("ls")
    assert "STDOUT:\ncontainer output" in result
    assert "Exit Code: 0" in result
    assert mock_run.call_count == 1
    # Check that docker run was called
    args = mock_run.call_args[0][0]
    assert "docker" in args
    assert "run" in args
    assert "--rm" in args

@patch("subprocess.run")
def test_container_bash_tool_no_docker(mock_run):
    set_binary_stub("docker", False)
    # Mock fallback to bash_tool
    mock_run.return_value = MagicMock(stdout="host output", stderr="", returncode=0)
    
    result = container_bash_tool("ls")
    assert "Warning: Docker not found" in result
    assert "STDOUT:\nhost output" in result
    assert mock_run.call_count == 1

@patch("json.load")
@patch("builtins.open")
def test_query_cwe_database(mock_open, mock_json_load):
    mock_json_load.return_value = [
        {
            "cwe_id": "CWE-79",
            "title": "XSS",
            "description": "Cross-site Scripting",
            "examples": [{"language": "python", "vulnerable_code": "print(userInput)"}]
        }
    ]
    
    result = query_cwe_database("XSS")
    assert "CWE-79: XSS" in result
    assert "Cross-site Scripting" in result
    assert "Vulnerable Example (python):" in result

def test_query_cwe_database_no_results():
    with patch("builtins.open", MagicMock()), patch("json.load", return_value=[]):
        result = query_cwe_database("nonexistent")
        assert "No results found" in result

@patch("trashdig.tools.base._get_ts_language")
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
        assert "Function: target_func" in result
        assert "Parameters: param1" in result

@patch("trashdig.tools.base._get_ts_language")
@patch("tree_sitter.Parser")
def test_trace_variable_semantic(mock_parser_class, mock_get_lang):
    mock_lang = MagicMock()
    mock_get_lang.return_value = mock_lang
    mock_parser = MagicMock()
    mock_parser_class.return_value = mock_parser
    mock_tree = MagicMock()
    mock_parser.parse.return_value = mock_tree
    
    mock_node = MagicMock()
    mock_node.type = "identifier"
    mock_node.text = b"my_var"
    mock_node.start_point = (5, 0)
    mock_node.parent.type = "assignment"
    mock_node.children = []
    
    mock_tree.root_node.children = [mock_node]
    
    with patch("builtins.open", MagicMock()):
        result = trace_variable_semantic("my_var", "test.py", "python")
        assert "Line 6: ASSIGNMENT/DEFINITION" in result

@patch("trashdig.tools.trace_variable.ripgrep_search")
def test_trace_variable(mock_rg):
    mock_rg.return_value = "line 5: my_var = 1"
    result = trace_variable("my_var", "test.py")
    assert "line 5: my_var = 1" in result

@pytest.mark.anyio
@patch("aiohttp.ClientSession.get")
async def test_web_fetch(mock_get):
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.text = AsyncMock(return_value="<html><body><h1>Hello</h1></body></html>")
    
    # aiohttp uses async context managers
    mock_get.return_value.__aenter__.return_value = mock_response
    
    result = await web_fetch("http://example.com")
    assert "Hello" in result
