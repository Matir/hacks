from unittest.mock import MagicMock, patch
from trashdig.tools.bash_tool import bash_tool

@patch("subprocess.run")
def test_bash_tool(mock_run):
    mock_run.return_value = MagicMock(stdout="output", stderr="error", returncode=0)
    result = bash_tool("ls")
    assert "STDOUT:\noutput" in result
    assert "STDERR:\nerror" in result
    assert "Exit Code: 0" in result
