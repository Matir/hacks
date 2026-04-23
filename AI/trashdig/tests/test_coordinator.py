import json
from unittest.mock import MagicMock, patch

import pytest
from google.adk.agents import LlmAgent

from trashdig.agents.coordinator import Coordinator
from trashdig.config import AgentConfig, Config
from trashdig.findings import Finding
from trashdig.services.database import get_database


@pytest.fixture
def mock_config(tmp_path):
    config = MagicMock(spec=Config)
    config.agents = {}
    config.max_parallel_tasks = 3

    agent_cfg = MagicMock(spec=AgentConfig)
    agent_cfg.model = "gemini-2.0-flash"
    agent_cfg.provider = "google"

    config.get_agent_config.return_value = agent_cfg
    config.db_path = str(tmp_path / "test.db")
    return config

def create_mock_agent(name):
    # LlmAgent is a Pydantic model, initialize it properly
    return LlmAgent(name=name, model="gemini-2.0-flash", instruction="test", tools=[])

@patch("trashdig.agents.coordinator.create_code_investigator_agent", autospec=True)
@patch("trashdig.agents.coordinator.create_stack_scout_agent", autospec=True)
@patch("trashdig.agents.coordinator.create_web_route_mapper_agent", autospec=True)
@patch("trashdig.agents.coordinator.create_hunter_agent", autospec=True)
@patch("trashdig.agents.coordinator.create_skeptic_agent", autospec=True)
@patch("trashdig.agents.coordinator.create_validator_agent", autospec=True)
@patch("trashdig.agents.utils.load_prompt", autospec=True, return_value="test prompt")
def test_coordinator_init(mock_load, mock_create_val, mock_create_skep, mock_create_hunt, mock_create_web, mock_create_stack, mock_create_investigator, mock_config):
    mock_create_investigator.return_value = create_mock_agent("code_investigator")
    mock_create_stack.return_value = create_mock_agent("stack_scout")
    mock_create_web.return_value = create_mock_agent("web_route_mapper")
    mock_create_hunt.return_value = create_mock_agent("hunter")
    mock_create_skep.return_value = create_mock_agent("skeptic")
    mock_create_val.return_value = create_mock_agent("validator")

    coord = Coordinator(mock_config)
    assert coord.stack_scout is not None
    assert coord.web_route_mapper is not None
    assert coord.hunter is not None
    assert coord.skeptic is not None
    assert coord.validator is not None

    # Verify Code Investigator call occurred
    assert mock_create_investigator.called

    assert isinstance(coord.session_id, str)

@patch("trashdig.agents.coordinator.create_stack_scout_agent", autospec=True)
@patch("trashdig.agents.coordinator.create_web_route_mapper_agent", autospec=True)
@patch("trashdig.agents.coordinator.create_hunter_agent", autospec=True)
@patch("trashdig.agents.coordinator.create_skeptic_agent", autospec=True)
@patch("trashdig.agents.coordinator.create_validator_agent", autospec=True)
@patch("trashdig.agents.utils.load_prompt", autospec=True, return_value="test prompt")
@patch("trashdig.agents.coordinator.run_agent", autospec=True)
async def test_coordinator_run_recon(mock_run_agent, mock_load, mock_create_val, mock_create_skep, mock_create_hunt, mock_create_web, mock_create_stack, mock_config):
    mock_create_stack.return_value = create_mock_agent("stack_scout")
    mock_create_web.return_value = create_mock_agent("web_route_mapper")
    mock_create_hunt.return_value = create_mock_agent("hunter")
    mock_create_skep.return_value = create_mock_agent("skeptic")
    mock_create_val.return_value = create_mock_agent("validator")

    # Mock run_agent to return a JSON string
    mock_run_agent.return_value = json.dumps({
        "mapping": {"file.py": {"summary": "test"}},
        "hypotheses": [{"target": "file.py", "description": "test"}]
    })

    coord = Coordinator(mock_config)
    # Simulate an agent tool call saving results
    coord.scan_results = {"file.py": {"summary": "test"}}

    res = await coord.run_recon(".")
    assert res == {"file.py": {"summary": "test"}}
    assert mock_run_agent.called

@patch("trashdig.agents.coordinator.create_stack_scout_agent", autospec=True)
@patch("trashdig.agents.coordinator.create_web_route_mapper_agent", autospec=True)
@patch("trashdig.agents.coordinator.create_hunter_agent", autospec=True)
@patch("trashdig.agents.coordinator.create_skeptic_agent", autospec=True)
@patch("trashdig.agents.coordinator.create_validator_agent", autospec=True)
@patch("trashdig.agents.utils.load_prompt", autospec=True, return_value="test prompt")
@patch("trashdig.agents.coordinator.run_agent", autospec=True)
async def test_coordinator_run_hunter(mock_run_agent, mock_load, mock_create_val, mock_create_skep, mock_create_hunt, mock_create_web, mock_create_stack, mock_config):
    mock_create_stack.return_value = create_mock_agent("stack_scout")
    mock_create_web.return_value = create_mock_agent("web_route_mapper")
    mock_create_hunt.return_value = create_mock_agent("hunter")
    mock_create_skep.return_value = create_mock_agent("skeptic")
    mock_create_val.return_value = create_mock_agent("validator")

    mock_run_agent.return_value = json.dumps({
        "findings": [{"title": "SQLi", "severity": "High", "description": "desc"}],
        "hypotheses": []
    })

    coord = Coordinator(mock_config)
    finding = Finding(
        title="SQLi", description="desc", severity="High",
        vulnerable_code="code", file_path="test.py",
        impact="impact", exploitation_path="path", remediation="rem"
    )
    coord.findings = [finding]

    findings = await coord.run_hunter(["test.py"])
    assert len(findings) == 1
    assert findings[0].title == "SQLi"

@patch("trashdig.agents.coordinator.create_stack_scout_agent", autospec=True)
@patch("trashdig.agents.coordinator.create_web_route_mapper_agent", autospec=True)
@patch("trashdig.agents.coordinator.create_hunter_agent", autospec=True)
@patch("trashdig.agents.coordinator.create_skeptic_agent", autospec=True)
@patch("trashdig.agents.coordinator.create_validator_agent", autospec=True)
@patch("trashdig.agents.utils.load_prompt", autospec=True, return_value="test prompt")
@patch("trashdig.agents.coordinator.run_agent", autospec=True)
async def test_coordinator_verify_finding(mock_run_agent, mock_load, mock_create_val, mock_create_skep, mock_create_hunt, mock_create_web, mock_create_stack, mock_config):
    mock_create_stack.return_value = create_mock_agent("stack_scout")
    mock_create_web.return_value = create_mock_agent("web_route_mapper")
    mock_create_hunt.return_value = create_mock_agent("hunter")
    mock_create_skep.return_value = create_mock_agent("skeptic")
    mock_create_val.return_value = create_mock_agent("validator")

    # First call for skeptic (is_valid=True), second for validator
    mock_run_agent.side_effect = [
        json.dumps({"is_valid": True}),
        json.dumps({"status": "Verified", "poc_code": "poc code"})
    ]

    coord = Coordinator(mock_config)

    finding = Finding(
        title="SQLi", description="desc", severity="High",
        vulnerable_code="code", file_path="test.py",
        impact="impact", exploitation_path="path", remediation="rem"
    )
    finding.verification_status = "Verified"
    finding.poc = "poc code"

    res = await coord.verify_finding(finding)
    assert res["status"] == "Verified"
    assert res["poc_code"] == "poc code"

def test_coordinator_state_tools(mock_config, tmp_path):
    db_path = str(tmp_path / "test_trashdig.db")
    db = get_database(db_path)
    with patch("trashdig.agents.coordinator.create_stack_scout_agent", autospec=True, return_value=create_mock_agent("s")), \
         patch("trashdig.agents.coordinator.create_web_route_mapper_agent", autospec=True, return_value=create_mock_agent("w")), \
         patch("trashdig.agents.coordinator.create_hunter_agent", autospec=True, return_value=create_mock_agent("h")), \
         patch("trashdig.agents.coordinator.create_skeptic_agent", autospec=True, return_value=create_mock_agent("sk")), \
         patch("trashdig.agents.coordinator.create_validator_agent", autospec=True, return_value=create_mock_agent("v")), \
         patch("trashdig.agents.utils.load_prompt", autospec=True, return_value="test prompt"), \
         patch("trashdig.agents.coordinator.get_database", autospec=True, return_value=db):

        mock_config.db_path = db_path
        coord = Coordinator(mock_config)

        # Test _save_project_profile
        msg = coord._save_project_profile("Python", {"mapping": {"a.py": {}}, "attack_surface": []})
        assert "successfully" in msg
        assert coord.tech_stack == "Python"
        assert "a.py" in coord.scan_results

        # Test _save_finding
        finding_data = {
            "title": "XSS", "description": "desc", "severity": "High",
            "vulnerable_code": "code", "file_path": "a.py",
            "impact": "i", "exploitation_path": "p", "remediation": "r"
        }
        msg = coord._save_finding(finding_data)
        assert "saved" in msg
        assert len(coord.findings) == 1
        assert coord.findings[0].title == "XSS"
