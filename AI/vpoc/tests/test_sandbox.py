import pytest
from unittest.mock import MagicMock, patch
from core.sandbox import SandboxRunner, SandboxResult
from core.models import ServerConfig

@pytest.fixture
def sandbox_runner():
    config = ServerConfig(require_gvisor=False)
    with patch("docker.from_env") as mock_docker:
        mock_client = mock_docker.return_value
        # Mock version to avoid constructor errors
        mock_client.version.return_value = {"ApiVersion": "1.41"}
        runner = SandboxRunner(config)
        # Store mock_client on runner for easy access in tests
        runner._mock_client = mock_client
        return runner

@pytest.mark.asyncio
async def test_run_poc_success(sandbox_runner):
    mock_container = MagicMock()
    mock_container.status = "exited"
    mock_container.wait.return_value = {"StatusCode": 0}
    mock_container.logs.return_value = b"success output"
    
    sandbox_runner._mock_client.containers.run.return_value = mock_container
    
    result = await sandbox_runner.run_poc("test-image")
    
    assert isinstance(result, SandboxResult)
    assert result.exit_code == 0
    assert "success output" in result.stdout
    sandbox_runner._mock_client.containers.run.assert_called_once()
    mock_container.remove.assert_called_once()

def test_check_gvisor(sandbox_runner):
    sandbox_runner._mock_client.info.return_value = {"Runtimes": {"runsc": {}}}
    
    sandbox_runner.config.runtime = "runsc"
    assert sandbox_runner.check_gvisor() is True
    
    sandbox_runner._mock_client.info.return_value = {"Runtimes": {"runc": {}}}
    assert sandbox_runner.check_gvisor() is False
