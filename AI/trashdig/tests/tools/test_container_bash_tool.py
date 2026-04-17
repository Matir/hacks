from unittest.mock import MagicMock, patch
from trashdig.tools.container_bash_tool import container_bash_tool
from trashdig.utils import set_binary_stub

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

@patch("trashdig.tools.container_bash_tool.bash_tool", autospec=True)
def test_container_bash_tool_docker_missing_fallback(mock_bash):
    """Test container_bash_tool falls back to host bash_tool when Docker is missing."""
    set_binary_stub("docker", False)
    mock_bash.return_value = "host_output"

    result = container_bash_tool("ls")
    assert "[Warning: Docker not found. Falling back to host bash_tool]" in result
    assert "host_output" in result
    mock_bash.assert_called_once_with("ls", 60)
