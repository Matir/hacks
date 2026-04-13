import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from core.agent_manager import AgentManager
from core.models import Finding, ProjectConfig, FindingStatus
from core.storage import StorageManager

@pytest.fixture
def agent_manager():
    config = ProjectConfig(project_id="p1", name="test", enable_validation=True)
    storage = MagicMock(spec=StorageManager)
    manager = AgentManager(config, storage)
    return manager

@pytest.mark.asyncio
async def test_enqueue_finding(agent_manager):
    finding = Finding(id=1, project_id="p1", vuln_type="RCE", file_path="f", line_number=1, severity="H", discovery_tool="t", evidence="e")
    finding.priority_score = 100.0
    
    await agent_manager.enqueue_finding(finding)
    assert agent_manager.queue.qsize() == 1
    
    item = await agent_manager.queue.get()
    assert item.finding.id == 1
    assert item.priority_score == -100.0 # Negated for max-priority

@pytest.mark.asyncio
async def test_process_finding_lifecycle(agent_manager):
    finding = Finding(id=1, project_id="p1", vuln_type="RCE", file_path="f", line_number=1, severity="H", discovery_tool="t", evidence="e")
    
    # Mock runner and agents
    # poc_runner.run() is an async call that returns an async generator
    async def mock_run_gen():
        yield "event"
        
    mock_runner = MagicMock()
    mock_runner.agent = MagicMock()
    # Runner.run is a coroutine returning an async generator
    mock_runner.run = AsyncMock(return_value=mock_run_gen())
    
    with patch.object(agent_manager, "get_or_create_runner", new_callable=AsyncMock) as mock_get_runner:
        mock_get_runner.return_value = mock_runner
        
        await agent_manager._process_finding(finding)
        
        # Verify status updates
        # Expected calls: POC_GENERATING, POC_READY, VALIDATING, VALIDATED
        assert agent_manager.storage.update_finding_status.call_count >= 4
        agent_manager.storage.update_finding_status.assert_any_call(1, FindingStatus.POC_GENERATING)
        agent_manager.storage.update_finding_status.assert_any_call(1, FindingStatus.VALIDATED)
