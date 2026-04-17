import os
import sys
from unittest.mock import ANY, MagicMock, patch

import pytest

from trashdig.sandbox import NullSandbox, get_sandbox
from trashdig.sandbox.bx import BxSandbox
from trashdig.sandbox.minijail import MinijailSandbox
from trashdig.utils import clear_binary_stubs, set_binary_stub


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
            env=ANY,
            check=False
        )

@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Minijail only on Linux")
def test_minijail_sandbox_init():
    set_binary_stub("minijail0", True)
    sandbox = MinijailSandbox(workspace_dir="/tmp/test")
    assert sandbox.minijail_path == "/stub/bin/minijail0"

@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Minijail only on Linux")
@patch("subprocess.run")
@patch("os.path.exists")
def test_minijail_sandbox_run(mock_exists, mock_run):
    set_binary_stub("minijail0", True)
    mock_exists.return_value = True
    mock_run.return_value = MagicMock(stdout="sandboxed", returncode=0)

    sandbox = MinijailSandbox(workspace_dir="/tmp/test", network=False)
    result = sandbox.run(["ls", "-la"])

    assert result.stdout == "sandboxed"
    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]

    assert "/stub/bin/minijail0" in args
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
def test_get_sandbox_macos_bx_available():
    set_binary_stub("bx", True)
    try:
        sandbox = get_sandbox(workspace_dir="/tmp/test", require_sandbox=True)
        assert isinstance(sandbox, BxSandbox)
    finally:
        clear_binary_stubs()

@patch("sys.platform", "darwin")
def test_get_sandbox_macos_bx_missing_strict_require():
    set_binary_stub("bx", False)
    try:
        with pytest.raises(RuntimeError, match="BxSandbox"):
            get_sandbox(workspace_dir="/tmp/test", require_sandbox=True)
    finally:
        clear_binary_stubs()

@patch("sys.platform", "darwin")
def test_get_sandbox_macos_bx_missing_graceful_fallback(caplog):
    set_binary_stub("bx", False)
    try:
        sandbox = get_sandbox(workspace_dir="/tmp/test", require_sandbox=False)
        assert isinstance(sandbox, NullSandbox)
        assert "BxSandbox not available" in caplog.text
    finally:
        clear_binary_stubs()

@patch("sys.platform", "linux")
def test_get_sandbox_linux_minijail():
    set_binary_stub("minijail0", True)
    sandbox = get_sandbox(workspace_dir="/tmp/test")
    assert isinstance(sandbox, MinijailSandbox)

@patch("sys.platform", "linux")
def test_get_sandbox_linux_no_minijail_fallback():
    set_binary_stub("minijail0", False)
    sandbox = get_sandbox(workspace_dir="/tmp/test", require_sandbox=False)
    assert isinstance(sandbox, NullSandbox)
