from unittest.mock import MagicMock, patch

from trashdig.config import Config
from trashdig.tools.container_bash_tool import _DEFAULT_IMAGE_ALLOWLIST, container_bash_tool
from trashdig.utils import set_binary_stub


@patch("subprocess.run")
def test_container_bash_tool_docker_available(mock_run):
    set_binary_stub("docker", True)
    mock_run.return_value = MagicMock(stdout="container output", stderr="", returncode=0)

    result = container_bash_tool("ls")
    assert "STDOUT:\ncontainer output" in result
    assert "Exit Code: 0" in result
    assert mock_run.call_count == 1
    args = mock_run.call_args[0][0]
    assert "docker" in args
    assert "run" in args
    assert "--rm" in args


@patch("subprocess.run")
def test_container_bash_tool_no_docker(mock_run):
    set_binary_stub("docker", False)
    mock_run.return_value = MagicMock(stdout="host output", stderr="", returncode=0)

    result = container_bash_tool("ls")
    assert "Warning: Docker not found" in result
    assert "STDOUT:\nhost output" in result
    assert mock_run.call_count == 1


@patch("trashdig.tools.container_bash_tool.bash_tool", autospec=True)
def test_container_bash_tool_docker_missing_fallback(mock_bash):
    set_binary_stub("docker", False)
    mock_bash.return_value = "host_output"

    result = container_bash_tool("ls")
    assert "[Warning: Docker not found. Falling back to host bash_tool]" in result
    assert "host_output" in result
    mock_bash.assert_called_once_with("ls", 60)


def test_disallowed_image_returns_error():
    result = container_bash_tool("ls", image="evilcorp/backdoor:latest")
    assert "not in the allowlist" in result
    assert "evilcorp/backdoor:latest" in result


def test_default_image_is_allowed():
    # python:3.11-slim is the default — must pass the allowlist check and reach Docker
    set_binary_stub("docker", True)
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="ok", stderr="", returncode=0)
        result = container_bash_tool("echo hi", image="python:3.11-slim")
    assert "not in the allowlist" not in result


def test_image_with_registry_prefix_allowed():
    # Base name after the last slash is "python", which is in the allowlist
    set_binary_stub("docker", True)
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="ok", stderr="", returncode=0)
        result = container_bash_tool("echo hi", image="docker.io/library/python:3.12")
    assert "not in the allowlist" not in result


def test_custom_allowlist_from_config():
    cfg = Config()
    cfg.data["container_image_allowlist"] = ["mycompany"]
    with patch("trashdig.tools.container_bash_tool.get_config", return_value=cfg):
        set_binary_stub("docker", True)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="ok", stderr="", returncode=0)
            result = container_bash_tool("ls", image="mycompany:latest")
    assert "not in the allowlist" not in result


def test_default_allowlist_contents():
    for name in ("python", "node", "golang", "ruby", "ubuntu", "debian", "alpine"):
        assert name in _DEFAULT_IMAGE_ALLOWLIST
