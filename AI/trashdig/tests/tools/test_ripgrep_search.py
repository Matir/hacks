from unittest.mock import MagicMock, patch
from trashdig.tools.ripgrep_search import ripgrep_search

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
