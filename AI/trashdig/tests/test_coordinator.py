import pytest
import asyncio
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
    config.max_parallel_tasks = 3
    return config

@patch("trashdig.agents.coordinator.create_stack_scout_agent")
@patch("trashdig.agents.coordinator.create_web_route_mapper_agent")
@patch("trashdig.agents.coordinator.create_hunter_agent")
@patch("trashdig.agents.coordinator.create_skeptic_agent")
@patch("trashdig.agents.coordinator.create_validator_agent")
def test_coordinator_init(mock_create_val, mock_create_skep, mock_create_hunt, mock_create_web, mock_create_stack, mock_config):
    coord = Coordinator(mock_config)
    assert coord.stack_scout is not None
    assert coord.web_route_mapper is not None
    assert coord.hunter is not None
    assert coord.skeptic is not None
    assert coord.validator is not None
    assert coord.task_queue == []

@pytest.mark.anyio
@patch("trashdig.agents.coordinator.create_stack_scout_agent")
@patch("trashdig.agents.coordinator.create_web_route_mapper_agent")
@patch("trashdig.agents.coordinator.create_hunter_agent")
@patch("trashdig.agents.coordinator.create_skeptic_agent")
@patch("trashdig.agents.coordinator.create_validator_agent")
async def test_coordinator_run_loop_scan(mock_create_val, mock_create_skep, mock_create_hunt, mock_create_web, mock_create_stack, mock_config):
    mock_stack = MagicMock()
    mock_stack.scan = AsyncMock(return_value={
        "mapping": {"src/main.py": {"is_high_value": True}},
        "hypotheses": [{"target": "src/api.py", "description": "XSS", "confidence": 0.9}],
        "tech_stack": "Python/FastAPI",
        "is_web_app": True
    })
    mock_create_stack.return_value = mock_stack
    
    mock_web = MagicMock()
    mock_web.map_routes = AsyncMock(return_value={
        "attack_surface": [{"route": "/api", "method": "GET", "handler": "main.py"}]
    })
    mock_create_web.return_value = mock_web
    
    coord = Coordinator(mock_config)
    task = Task(TaskType.SCAN, ".")
    coord.spawn_task(task)
    
    await coord.run_loop()
    
    assert task.status == TaskStatus.COMPLETED
    assert coord.tech_stack == "Python/FastAPI"
    assert len(coord.attack_surface) == 1
    assert len(coord.completed_tasks) == 1
    assert mock_stack.scan.called
    assert mock_web.map_routes.called

@pytest.mark.anyio
@patch("trashdig.agents.coordinator.create_stack_scout_agent")
@patch("trashdig.agents.coordinator.create_web_route_mapper_agent")
@patch("trashdig.agents.coordinator.create_hunter_agent")
@patch("trashdig.agents.coordinator.create_skeptic_agent")
@patch("trashdig.agents.coordinator.create_validator_agent")
async def test_coordinator_handle_hunt(mock_create_val, mock_create_skep, mock_create_hunt, mock_create_web, mock_create_stack, mock_config):
    mock_hunter = MagicMock()
    finding = Finding(
        title="SQLi", description="desc", severity="High", 
        vulnerable_code="code", file_path="test.py", 
        impact="impact", exploitation_path="path", remediation="rem"
    )
    mock_hunter.hunt_vulnerabilities = AsyncMock()
    mock_hunter.hunt_vulnerabilities.side_effect = [
        {
            "findings": [finding],
            "hypotheses": [{"target": "other.py", "description": "trace", "confidence": 0.5}]
        },
        {
            "findings": [],
            "hypotheses": []
        }
    ]
    mock_create_hunt.return_value = mock_hunter
    
    coord = Coordinator(mock_config)
    task = Task(TaskType.HUNT, "test.py")
    coord.spawn_task(task)
    
    coord._handle_verify = AsyncMock()
    
    await coord.run_loop()
    
    assert len(coord.findings) == 1
    assert coord.findings[0].title == "SQLi"
    assert any(t.type == TaskType.VERIFY for t in coord.completed_tasks)
    assert any(t.target == "other.py" for t in coord.completed_tasks)

@pytest.mark.anyio
@patch("trashdig.agents.coordinator.create_stack_scout_agent")
@patch("trashdig.agents.coordinator.create_web_route_mapper_agent")
@patch("trashdig.agents.coordinator.create_hunter_agent")
@patch("trashdig.agents.coordinator.create_skeptic_agent")
@patch("trashdig.agents.coordinator.create_validator_agent")
async def test_coordinator_api_methods(mock_create_val, mock_create_skep, mock_create_hunt, mock_create_web, mock_create_stack, mock_config):
    mock_stack = MagicMock()
    mock_stack.scan = AsyncMock(return_value={"mapping": {"file.py": "summary"}})
    mock_create_stack.return_value = mock_stack
    
    mock_hunter = MagicMock()
    mock_hunter.hunt_vulnerabilities = AsyncMock(return_value={"findings": [], "hypotheses": []})
    mock_create_hunt.return_value = mock_hunter
    
    mock_skeptic = MagicMock()
    mock_skeptic.debunk_finding = AsyncMock(return_value={"is_valid": True, "skeptic_notes": "Passed"})
    mock_create_skep.return_value = mock_skeptic

    mock_validator = MagicMock()
    mock_validator.verify_finding = AsyncMock(return_value={"status": "Verified", "poc_code": "poc"})
    mock_create_val.return_value = mock_validator
    
    coord = Coordinator(mock_config)
    
    # Test run_recon
    res = await coord.run_recon("path")
    assert res == {"file.py": "summary"}
    
    # Test run_hunter
    findings = await coord.run_hunter(["file.py"])
    assert findings == []
    
    # Test verify_finding (Survived skeptic)
    finding = Finding(
        title="SQLi", description="desc", severity="High", 
        vulnerable_code="code", file_path="test.py", 
        impact="impact", exploitation_path="path", remediation="rem"
    )
    with patch("trashdig.findings.Finding.save", MagicMock()):
        verify_res = await coord.verify_finding(finding)
        assert verify_res["status"] == "Verified"
        assert finding.verification_status == "Verified"
        assert mock_skeptic.debunk_finding.called
        assert mock_validator.verify_finding.called

@pytest.mark.anyio
@patch("trashdig.agents.coordinator.create_stack_scout_agent")
@patch("trashdig.agents.coordinator.create_web_route_mapper_agent")
@patch("trashdig.agents.coordinator.create_hunter_agent")
@patch("trashdig.agents.coordinator.create_skeptic_agent")
@patch("trashdig.agents.coordinator.create_validator_agent")
async def test_coordinator_verify_debunked(mock_create_val, mock_create_skep, mock_create_hunt, mock_create_web, mock_create_stack, mock_config):
    mock_skeptic = MagicMock()
    mock_skeptic.debunk_finding = AsyncMock(return_value={"is_valid": False, "skeptic_notes": "False Positive"})
    mock_create_skep.return_value = mock_skeptic

    mock_validator = MagicMock()
    mock_create_val.return_value = mock_validator
    
    coord = Coordinator(mock_config)
    finding = Finding(
        title="SQLi", description="desc", severity="High", 
        vulnerable_code="code", file_path="test.py", 
        impact="impact", exploitation_path="path", remediation="rem"
    )
    with patch("trashdig.findings.Finding.save", MagicMock()):
        verify_res = await coord.verify_finding(finding)
        assert verify_res["status"] == "Debunked"
        assert finding.verification_status == "Debunked"
        assert mock_skeptic.debunk_finding.called
        assert not mock_validator.verify_finding.called

@patch("trashdig.agents.coordinator.create_stack_scout_agent")
@patch("trashdig.agents.coordinator.create_web_route_mapper_agent")
@patch("trashdig.agents.coordinator.create_hunter_agent")
@patch("trashdig.agents.coordinator.create_skeptic_agent")
@patch("trashdig.agents.coordinator.create_validator_agent")
def test_coordinator_on_conversation(mock_create_val, mock_create_skep, mock_create_hunt, mock_create_web, mock_create_stack, mock_config):
    mock_db = MagicMock()
    with patch("trashdig.agents.coordinator.ProjectDatabase", return_value=mock_db):
        coord = Coordinator(mock_config)
        coord._on_conversation(
            "test_agent", "test prompt", "test response", [{"name": "tool"}], 10, 20
        )
        mock_db.log_conversation.assert_called_once_with(
            coord.project_path, "test_agent", "test prompt", "test response", [{"name": "tool"}], 10, 20
        )

@pytest.mark.anyio
@patch("trashdig.agents.coordinator.create_stack_scout_agent")
@patch("trashdig.agents.coordinator.create_web_route_mapper_agent")
@patch("trashdig.agents.coordinator.create_hunter_agent")
@patch("trashdig.agents.coordinator.create_skeptic_agent")
@patch("trashdig.agents.coordinator.create_validator_agent")
async def test_coordinator_parallel_execution(mock_create_val, mock_create_skep, mock_create_hunt, mock_create_web, mock_create_stack, mock_config):
    coord = Coordinator(mock_config)
    
    # Track concurrent execution
    active_count = 0
    max_observed_active = 0
    
    async def mock_handle(task):
        nonlocal active_count, max_observed_active
        active_count += 1
        max_observed_active = max(max_observed_active, active_count)
        await asyncio.sleep(0.1) # Simulate delay
        active_count -= 1

    coord._handle_scan = AsyncMock(side_effect=mock_handle)
    
    # Spawn 5 tasks, semaphore limit is 3
    for i in range(5):
        coord.spawn_task(Task(TaskType.SCAN, f"target{i}"))
    
    await coord.run_loop()
    
    # Should have run at least 2 tasks in parallel (up to 3)
    assert max_observed_active >= 2
    assert len(coord.completed_tasks) == 5
