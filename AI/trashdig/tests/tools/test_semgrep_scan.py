import subprocess
from unittest.mock import MagicMock, patch

from trashdig.tools.semgrep_scan import semgrep_scan


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


@patch("trashdig.tools.semgrep_scan.is_binary_available", return_value=False)
def test_semgrep_not_installed_returns_error(mock_avail):
    result = semgrep_scan("path")
    assert "not installed" in result
    assert "semgrep" in result
