import pytest
import json
from unittest.mock import MagicMock, patch, AsyncMock
from trashdig.agents.coordinator import Coordinator
from trashdig.config import Config
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
@patch("trashdig.agents.coordinator.run_agent", new_callable=AsyncMock)
async def test_coordinator_run_recon(mock_run_agent, mock_create_val, mock_create_skep, mock_create_hunt, mock_create_web, mock_create_stack, mock_config):
    mock_create_stack.return_value = create_mock_agent("stack_scout")
    mock_create_web.return_value = create_mock_agent("web_route_mapper")
    mock_create_hunt.return_value = create_mock_agent("hunter")
    mock_create_skep.return_value = create_mock_agent("skeptic")
    mock_create_val.return_value = create_mock_agent("validator")

    coord = Coordinator(mock_config)
    
    # Mock StackScout result text
    res_stack = json.dumps({"tech_stack": "Python", "is_web_app": True, "mapping": {"a.py": {"is_high_value": True}}, "hypotheses": []})
    # Mock WebRouteMapper result text
    res_web = json.dumps({"attack_surface": [{"endpoint": "/", "method": "GET"}]})
    
    mock_run_agent.side_effect = [res_stack, res_web]
    
    await coord.run_recon(".")
    
    assert coord.tech_stack == "Python"
    assert len(coord.attack_surface) == 1
    assert mock_run_agent.call_count == 2

@pytest.mark.anyio
@patch("trashdig.agents.coordinator.create_stack_scout_agent")
@patch("trashdig.agents.coordinator.create_web_route_mapper_agent")
@patch("trashdig.agents.coordinator.create_hunter_agent")
@patch("trashdig.agents.coordinator.create_skeptic_agent")
@patch("trashdig.agents.coordinator.create_validator_agent")
@patch("trashdig.agents.coordinator.run_agent", new_callable=AsyncMock)
async def test_coordinator_run_hunter(mock_run_agent, mock_create_val, mock_create_skep, mock_create_hunt, mock_create_web, mock_create_stack, mock_config):
    mock_create_hunt.return_value = create_mock_agent("hunter")
    mock_create_stack.return_value = create_mock_agent("stack_scout")
    mock_create_web.return_value = create_mock_agent("web_route_mapper")
    mock_create_skep.return_value = create_mock_agent("skeptic")
    mock_create_val.return_value = create_mock_agent("validator")
    
    coord = Coordinator(mock_config)
    
    res_hunter = json.dumps({"findings": [{"title": "SQLi", "description": "desc", "severity": "High", "vulnerable_code": "code", "file_path": "test.py", "impact": "i", "exploitation_path": "e", "remediation": "r"}], "hypotheses": []})
    mock_run_agent.return_value = res_hunter
    
    with patch("trashdig.agents.utils.read_file_content", return_value="content"):
        findings = await coord.run_hunter(["test.py"])
    
    assert len(findings) == 1
    assert findings[0].title == "SQLi"
    assert mock_run_agent.called

@pytest.mark.anyio
@patch("trashdig.agents.coordinator.create_stack_scout_agent")
@patch("trashdig.agents.coordinator.create_web_route_mapper_agent")
@patch("trashdig.agents.coordinator.create_hunter_agent")
@patch("trashdig.agents.coordinator.create_skeptic_agent")
@patch("trashdig.agents.coordinator.create_validator_agent")
@patch("trashdig.agents.coordinator.run_agent", new_callable=AsyncMock)
async def test_coordinator_verify_finding(mock_run_agent, mock_create_val, mock_create_skep, mock_create_hunt, mock_create_web, mock_create_stack, mock_config):
    mock_create_stack.return_value = create_mock_agent("stack_scout")
    mock_create_web.return_value = create_mock_agent("web_route_mapper")
    mock_create_hunt.return_value = create_mock_agent("hunter")
    mock_create_skep.return_value = create_mock_agent("skeptic")
    mock_create_val.return_value = create_mock_agent("validator")

    coord = Coordinator(mock_config)
    
    # 1. Skeptic: Survived
    res_skep = json.dumps({"is_valid": True})
    # 2. Validator: Verified
    res_val = json.dumps({"status": "Verified", "poc_code": "poc"})
    
    mock_run_agent.side_effect = [res_skep, res_val]
    
    finding = Finding(
        title="SQLi", description="desc", severity="High", 
        vulnerable_code="code", file_path="test.py", 
        impact="impact", exploitation_path="path", remediation="rem"
    )
    
    with patch("trashdig.findings.Finding.save", MagicMock()), \
         patch("trashdig.agents.utils.read_file_content", return_value="content"):
        verify_res = await coord.verify_finding(finding)
        assert verify_res["status"] == "Verified"
        assert finding.verification_status == "Verified"
        assert mock_run_agent.call_count == 2
