import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from trashdig.agents.coordinator import Coordinator
from trashdig.config import Config
from trashdig.agents.types import Task, TaskType, TaskStatus
from trashdig.findings import Finding

@pytest.fixture
def mock_config():
    config = MagicMock(spec=Config)
    config.agents = MagicMock()
    config.agents.get.return_value = None
    return config

@patch("trashdig.agents.coordinator.create_archaeologist_agent")
@patch("trashdig.agents.coordinator.create_hunter_agent")
@patch("trashdig.agents.coordinator.create_validator_agent")
def test_coordinator_init(mock_create_val, mock_create_hunt, mock_create_arch, mock_config):
    coord = Coordinator(mock_config)
    assert coord.archaeologist is not None
    assert coord.hunter is not None
    assert coord.validator is not None
    assert coord.task_queue == []

@pytest.mark.anyio
@patch("trashdig.agents.coordinator.create_archaeologist_agent")
@patch("trashdig.agents.coordinator.create_hunter_agent")
@patch("trashdig.agents.coordinator.create_validator_agent")
async def test_coordinator_run_loop_scan(mock_create_val, mock_create_hunt, mock_create_arch, mock_config):
    mock_arch = MagicMock()
    mock_arch.scan_project = AsyncMock(return_value={
        "mapping": {"src/main.py": {"is_high_value": True}},
        "hypotheses": [{"target": "src/api.py", "description": "XSS", "confidence": 0.9}],
        "tech_stack": "Python/FastAPI"
    })
    mock_create_arch.return_value = mock_arch
    
    coord = Coordinator(mock_config)
    task = Task(TaskType.SCAN, ".")
    coord.spawn_task(task)
    
    await coord.run_loop()
    
    assert task.status == TaskStatus.COMPLETED
    assert coord.tech_stack == "Python/FastAPI"
    # Should have spawned HUNT tasks for hypothesis and high-value target (if auto_hunt set)
    # By default auto_hunt is False in task context
    assert len(coord.completed_tasks) == 1
    # Check if hypothesis task is in queue (though run_loop emptied it)
    # We can check if it was added to queue during run_loop
    assert mock_arch.scan_project.called

@pytest.mark.anyio
@patch("trashdig.agents.coordinator.create_archaeologist_agent")
@patch("trashdig.agents.coordinator.create_hunter_agent")
@patch("trashdig.agents.coordinator.create_validator_agent")
async def test_coordinator_handle_hunt(mock_create_val, mock_create_hunt, mock_create_arch, mock_config):
    mock_hunter = MagicMock()
    finding = Finding(
        title="SQLi", description="desc", severity="High", 
        vulnerable_code="code", file_path="test.py", 
        impact="impact", exploitation_path="path", remediation="rem"
    )
    mock_hunter.hunt_vulnerabilities = AsyncMock(return_value=[finding])
    mock_create_hunt.return_value = mock_hunter
    
    coord = Coordinator(mock_config)
    task = Task(TaskType.HUNT, "test.py")
    coord.spawn_task(task)
    
    # We need to mock _handle_verify to avoid calling validator
    coord._handle_verify = AsyncMock()
    
    await coord.run_loop()
    
    assert len(coord.findings) == 1
    assert coord.findings[0].title == "SQLi"
    # Verify task should have been spawned
    assert any(t.type == TaskType.VERIFY for t in coord.completed_tasks) or coord.task_queue

@pytest.mark.anyio
@patch("trashdig.agents.coordinator.create_archaeologist_agent")
@patch("trashdig.agents.coordinator.create_hunter_agent")
@patch("trashdig.agents.coordinator.create_validator_agent")
async def test_coordinator_api_methods(mock_create_val, mock_create_hunt, mock_create_arch, mock_config):
    mock_arch = MagicMock()
    mock_arch.scan_project = AsyncMock(return_value={"mapping": {"file.py": "summary"}})
    mock_create_arch.return_value = mock_arch
    
    mock_hunter = MagicMock()
    mock_hunter.hunt_vulnerabilities = AsyncMock(return_value=[])
    mock_create_hunt.return_value = mock_hunter
    
    mock_validator = MagicMock()
    mock_validator.verify_finding = AsyncMock(return_value={"status": "Verified", "poc_code": "poc"})
    mock_create_val.return_value = mock_validator
    
    coord = Coordinator(mock_config)
    
    # Test run_archaeologist
    res = await coord.run_archaeologist("path")
    assert res == {"file.py": "summary"}
    
    # Test run_hunter
    findings = await coord.run_hunter(["file.py"])
    assert findings == []
    
    # Test verify_finding
    finding = Finding(
        title="SQLi", description="desc", severity="High", 
        vulnerable_code="code", file_path="test.py", 
        impact="impact", exploitation_path="path", remediation="rem"
    )
    with patch("trashdig.findings.Finding.save", MagicMock()):
        verify_res = await coord.verify_finding(finding)
        assert verify_res["status"] == "Verified"
        assert finding.verification_status == "Verified"
