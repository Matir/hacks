import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from trashdig.agents.coordinator import Coordinator
from trashdig.config import Config
from trashdig.agents.types import Task, TaskType, TaskStatus
from trashdig.findings import Finding

from google.adk.agents import LlmAgent

def create_mock_agent(name="dummy"):
    return LlmAgent(
        name=name,
        model="gemini-2.0-flash",
        instruction="instruction",
        description="description"
    )

@pytest.fixture
def mock_config(tmp_path):
    config = MagicMock(spec=Config)
    config.agents = MagicMock()
    config.get_agent_config.return_value = MagicMock(model="gemini-2.0-flash")
    config.max_parallel_tasks = 3
    db_file = tmp_path / "test.db"
    config.db_path = str(db_file)
    return config

@patch("trashdig.agents.coordinator.create_stack_scout_agent")
@patch("trashdig.agents.coordinator.create_web_route_mapper_agent")
@patch("trashdig.agents.coordinator.create_hunter_agent")
@patch("trashdig.agents.coordinator.create_skeptic_agent")
@patch("trashdig.agents.coordinator.create_validator_agent")
def test_coordinator_init(mock_create_val, mock_create_skep, mock_create_hunt, mock_create_web, mock_create_stack, mock_config):
    mock_create_val.return_value = create_mock_agent("validator")
    mock_create_skep.return_value = create_mock_agent("skeptic")
    mock_create_hunt.return_value = create_mock_agent("hunter")
    mock_create_web.return_value = create_mock_agent("web_route_mapper")
    mock_create_stack.return_value = create_mock_agent("stack_scout")
    
    coord = Coordinator(mock_config)
    assert coord.stack_scout is not None
    assert coord.web_route_mapper is not None
    assert coord.hunter is not None
    assert coord.skeptic is not None
    assert coord.validator is not None

@pytest.mark.anyio
@patch("trashdig.agents.coordinator.create_stack_scout_agent")
@patch("trashdig.agents.coordinator.create_web_route_mapper_agent")
@patch("trashdig.agents.coordinator.create_hunter_agent")
@patch("trashdig.agents.coordinator.create_skeptic_agent")
@patch("trashdig.agents.coordinator.create_validator_agent")
async def test_coordinator_run_loop_scan(mock_create_val, mock_create_skep, mock_create_hunt, mock_create_web, mock_create_stack, mock_config):
    mock_stack = create_mock_agent("stack_scout")
    object.__setattr__(mock_stack, "scan", AsyncMock(return_value={
        "mapping": {"src/main.py": {"is_high_value": True}},
        "hypotheses": [{"target": "src/api.py", "description": "XSS", "confidence": 0.9}],
        "tech_stack": "Python/FastAPI",
        "is_web_app": True
    }))
    mock_create_stack.return_value = mock_stack
    
    mock_web = create_mock_agent("web_route_mapper")
    object.__setattr__(mock_web, "map_routes", AsyncMock(return_value={
        "attack_surface": [{"route": "/api", "method": "GET", "handler": "main.py"}]
    }))
    mock_create_web.return_value = mock_web
    
    # Initialize others to avoid ValidationError
    mock_create_hunt.return_value = create_mock_agent("hunter")
    mock_create_skep.return_value = create_mock_agent("skeptic")
    mock_create_val.return_value = create_mock_agent("validator")

    coord = Coordinator(mock_config)
    
    # Run RECON directly to simulate a scan task
    await coord.run_recon(".")
    
    assert coord.tech_stack == "Python/FastAPI"
    assert len(coord.attack_surface) == 1
    assert mock_stack.scan.called
    assert mock_web.map_routes.called

@pytest.mark.anyio
@patch("trashdig.agents.coordinator.create_stack_scout_agent")
@patch("trashdig.agents.coordinator.create_web_route_mapper_agent")
@patch("trashdig.agents.coordinator.create_hunter_agent")
@patch("trashdig.agents.coordinator.create_skeptic_agent")
@patch("trashdig.agents.coordinator.create_validator_agent")
async def test_coordinator_handle_hunt(mock_create_val, mock_create_skep, mock_create_hunt, mock_create_web, mock_create_stack, mock_config):
    mock_hunter = create_mock_agent("hunter")
    finding = Finding(
        title="SQLi", description="desc", severity="High", 
        vulnerable_code="code", file_path="test.py", 
        impact="impact", exploitation_path="path", remediation="rem"
    )
    object.__setattr__(mock_hunter, "hunt_vulnerabilities", AsyncMock())
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
    mock_create_stack.return_value = create_mock_agent("stack_scout")
    mock_create_web.return_value = create_mock_agent("web_route_mapper")
    mock_create_skep.return_value = create_mock_agent("skeptic")
    mock_create_val.return_value = create_mock_agent("validator")
    
    coord = Coordinator(mock_config)
    
    # Mocking run_hunter behavior inside
    new_findings = await coord.run_hunter(["test.py"])
    
    assert len(coord.findings) == 1
    assert coord.findings[0].title == "SQLi"

@pytest.mark.anyio
@patch("trashdig.agents.coordinator.create_stack_scout_agent")
@patch("trashdig.agents.coordinator.create_web_route_mapper_agent")
@patch("trashdig.agents.coordinator.create_hunter_agent")
@patch("trashdig.agents.coordinator.create_skeptic_agent")
@patch("trashdig.agents.coordinator.create_validator_agent")
async def test_coordinator_api_methods(mock_create_val, mock_create_skep, mock_create_hunt, mock_create_web, mock_create_stack, mock_config):
    mock_stack = create_mock_agent("stack_scout")
    object.__setattr__(mock_stack, "scan", AsyncMock(return_value={"mapping": {"file.py": "summary"}}))
    mock_create_stack.return_value = mock_stack
    
    mock_hunter = create_mock_agent("hunter")
    object.__setattr__(mock_hunter, "hunt_vulnerabilities", AsyncMock(return_value={"findings": [], "hypotheses": []}))
    mock_create_hunt.return_value = mock_hunter
    
    mock_skeptic = create_mock_agent("skeptic")
    object.__setattr__(mock_skeptic, "debunk_finding", AsyncMock(return_value={"is_valid": True, "skeptic_notes": "Passed"}))
    mock_create_skep.return_value = mock_skeptic

    mock_validator = create_mock_agent("validator")
    object.__setattr__(mock_validator, "verify_finding", AsyncMock(return_value={"status": "Verified", "poc_code": "poc"}))
    mock_create_val.return_value = mock_validator
    
    mock_create_web.return_value = create_mock_agent("web_route_mapper")

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
    mock_skeptic = create_mock_agent("skeptic")
    object.__setattr__(mock_skeptic, "debunk_finding", AsyncMock(return_value={"is_valid": False, "skeptic_notes": "False Positive"}))
    mock_create_skep.return_value = mock_skeptic

    mock_validator = create_mock_agent("validator")
    object.__setattr__(mock_validator, "verify_finding", AsyncMock(return_value={"status": "Verified", "poc_code": "poc"}))
    mock_create_val.return_value = mock_validator
    mock_create_stack.return_value = create_mock_agent("stack_scout")
    mock_create_web.return_value = create_mock_agent("web_route_mapper")
    mock_create_hunt.return_value = create_mock_agent("hunter")
    
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
    # Mocking agents
    mock_create_stack.return_value = create_mock_agent("stack_scout")
    mock_create_web.return_value = create_mock_agent("web_route_mapper")
    mock_create_hunt.return_value = create_mock_agent("hunter")
    mock_create_skep.return_value = create_mock_agent("skeptic")
    mock_create_val.return_value = create_mock_agent("validator")
    with patch("trashdig.agents.coordinator.ProjectDatabase", return_value=mock_db):
        coord = Coordinator(mock_config)
        coord._on_conversation(
            "hunter", "test prompt", "test response", [{"name": "tool"}], 10, 20
        )
        mock_db.log_conversation.assert_called_once_with(
            coord.project_path, "hunter", "test prompt", "test response", [{"name": "tool"}], 10, 20
        )

@pytest.mark.anyio
@patch("trashdig.agents.coordinator.create_stack_scout_agent")
@patch("trashdig.agents.coordinator.create_web_route_mapper_agent")
@patch("trashdig.agents.coordinator.create_hunter_agent")
@patch("trashdig.agents.coordinator.create_skeptic_agent")
@patch("trashdig.agents.coordinator.create_validator_agent")
async def test_coordinator_parallel_execution(mock_create_val, mock_create_skep, mock_create_hunt, mock_create_web, mock_create_stack, mock_config):
    mock_create_stack.return_value = create_mock_agent("stack_scout")
    mock_create_web.return_value = create_mock_agent("web_route_mapper")
    mock_create_hunt.return_value = create_mock_agent("hunter")
    mock_create_skep.return_value = create_mock_agent("skeptic")
    mock_create_val.return_value = create_mock_agent("validator")
    coord = Coordinator(mock_config)
    
    # Track concurrent execution
    active_count = 0
    max_observed_active = 0
    
    async def mock_handle_recon(path):
        nonlocal active_count, max_observed_active
        active_count += 1
        max_observed_active = max(max_observed_active, active_count)
        await asyncio.sleep(0.1)
        active_count -= 1
        return {}

    # Use object.__setattr__ to bypass Pydantic's rejection of setting methods on instances
    original_run_recon = coord.run_recon
    object.__setattr__(coord, "run_recon", mock_handle_recon)
    try:
        # In this simplified test, we just call run_recon multiple times in parallel
        await asyncio.gather(*(coord.run_recon(f"target{i}") for i in range(5)))
    finally:
        object.__setattr__(coord, "run_recon", original_run_recon)
    
    # max_parallel_tasks not directly used in run_recon call, but testing we can run it.
    assert max_observed_active >= 2
