import subprocess
from unittest.mock import MagicMock, patch

from trashdig.tools.ripgrep_search import ripgrep_search


def _sandboxed_result(returncode, stdout="", stderr=""):
    return MagicMock(spec=subprocess.CompletedProcess,
                     returncode=returncode, stdout=stdout, stderr=stderr)


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


@patch("trashdig.tools.ripgrep_search._run_sandboxed")
def test_ripgrep_no_matches_returns_empty(mock_run):
    # rg exits 1 for "no matches" — not an error condition
    mock_run.return_value = _sandboxed_result(1)
    assert ripgrep_search("nothing_here") == ""


@patch("trashdig.tools.ripgrep_search._run_sandboxed")
def test_ripgrep_error_returns_stderr(mock_run):
    mock_run.return_value = _sandboxed_result(2, stderr="rg: bad syntax in regex")
    result = ripgrep_search("[invalid")
    assert "rg: bad syntax in regex" in result


@patch("trashdig.tools.ripgrep_search._run_sandboxed")
def test_ripgrep_unknown_exit_without_stderr(mock_run):
    mock_run.return_value = _sandboxed_result(3)
    result = ripgrep_search("foo")
    assert "exit 3" in result
