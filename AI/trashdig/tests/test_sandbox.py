import pytest
import sys
from unittest.mock import MagicMock, patch
from trashdig.sandbox import get_sandbox, NullSandbox
from trashdig.sandbox.minijail import MinijailSandbox

def test_null_sandbox():
    sandbox = NullSandbox(workspace_dir="/tmp/test")
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="ok", stderr="", returncode=0)
        result = sandbox.run(["ls"])
        assert result.stdout == "ok"
        mock_run.assert_called_once_with(
            ["ls"],
            capture_output=True,
            text=True,
            timeout=None,
            cwd="/tmp/test",
            env={},
            check=False
        )

@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Minijail only on Linux")
@patch("shutil.which")
def test_minijail_sandbox_init(mock_which):
    mock_which.return_value = "/usr/bin/minijail0"
    sandbox = MinijailSandbox(workspace_dir="/tmp/test")
    assert sandbox.minijail_path == "/usr/bin/minijail0"

@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Minijail only on Linux")
@patch("shutil.which")
@patch("subprocess.run")
@patch("os.path.exists")
def test_minijail_sandbox_run(mock_exists, mock_run, mock_which):
    mock_which.return_value = "/usr/bin/minijail0"
    mock_exists.return_value = True
    mock_run.return_value = MagicMock(stdout="sandboxed", returncode=0)
    
    sandbox = MinijailSandbox(workspace_dir="/tmp/test", network=False)
    result = sandbox.run(["ls", "-la"])
    
    assert result.stdout == "sandboxed"
    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    
    assert "/usr/bin/minijail0" in args
    assert "-v" in args
    assert "-d" in args
    assert "-p" in args
    assert "-r" in args
    assert "-e" in args # Network disabled
    assert "-U" in args
    assert "-b" in args
    # Check workspace mount
    assert "/tmp/test,/tmp/test,1" in args
    # Check some default allowlist mount
    assert "/bin,/bin,0" in args
    assert "--" in args
    assert "ls" in args
    assert "-la" in args

@patch("sys.platform", "darwin")
def test_get_sandbox_macos_fallback():
    # On MacOS, it should return NullSandbox if not required
    sandbox = get_sandbox(workspace_dir="/tmp/test", require_sandbox=False)
    assert isinstance(sandbox, NullSandbox)

@patch("sys.platform", "darwin")
def test_get_sandbox_macos_require_fails():
    with pytest.raises(RuntimeError, match="No sandbox implementation available"):
        get_sandbox(workspace_dir="/tmp/test", require_sandbox=True)

@patch("sys.platform", "linux")
@patch("shutil.which")
def test_get_sandbox_linux_minijail(mock_which):
    mock_which.return_value = "/usr/bin/minijail0"
    sandbox = get_sandbox(workspace_dir="/tmp/test")
    assert isinstance(sandbox, MinijailSandbox)

@patch("sys.platform", "linux")
@patch("shutil.which")
def test_get_sandbox_linux_no_minijail_fallback(mock_which):
    mock_which.return_value = None
    sandbox = get_sandbox(workspace_dir="/tmp/test", require_sandbox=False)
    assert isinstance(sandbox, NullSandbox)
