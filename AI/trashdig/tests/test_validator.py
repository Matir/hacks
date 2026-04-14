import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from trashdig.agents.validator import ValidatorAgent, create_validator_agent, load_prompt
from trashdig.findings import Finding
from trashdig.config import AgentConfig


def test_load_prompt():
    with patch("builtins.open", MagicMock(return_value=MagicMock(__enter__=lambda self: MagicMock(read=lambda: "test prompt")))):
        prompt = load_prompt("fake_path.md")
        assert prompt == "test prompt"


@pytest.mark.anyio
@patch("trashdig.agents.validator.read_file_content")
@patch("trashdig.agents.validator.run_prompt", new_callable=AsyncMock)
async def test_validator_verify_finding(mock_run_prompt, mock_read):
    mock_read.return_value = "print('vulnerable_code')"
    mock_run_prompt.return_value = (
        '```json\n'
        '{"status": "Verified", "poc_code": "python poc.py", "reasoning": "Confirmed"}\n'
        '```'
    )

    agent = ValidatorAgent(name="validator", model="gemini-2.0-flash")
    finding = Finding(
        title="Test Finding",
        description="desc",
        severity="High",
        vulnerable_code="code",
        file_path="test.py",
        impact="impact",
        exploitation_path="path",
        remediation="rem",
    )

    result = await agent.verify_finding(finding)

    assert result["status"] == "Verified"
    assert result["poc_code"] == "python poc.py"
    mock_run_prompt.assert_called_once()


@pytest.mark.anyio
@patch("trashdig.agents.validator.read_file_content")
@patch("trashdig.agents.validator.run_prompt", new_callable=AsyncMock)
async def test_validator_verify_finding_json_error(mock_run_prompt, mock_read):
    mock_read.return_value = "code"
    mock_run_prompt.return_value = "invalid json"

    agent = ValidatorAgent(name="validator", model="gemini-2.0-flash")
    finding = Finding(
        title="Test Finding",
        description="desc",
        severity="High",
        vulnerable_code="code",
        file_path="test.py",
        impact="impact",
        exploitation_path="path",
        remediation="rem",
    )

    result = await agent.verify_finding(finding)

    assert result["status"] == "Unverified"
    assert "error" in result
    assert result["raw"] == "invalid json"


@patch("trashdig.agents.validator.load_prompt")
@patch("google.adk.agents.LlmAgent.__init__")
def test_create_validator_agent(mock_init, mock_load):
    mock_load.return_value = "instruction"
    mock_init.return_value = None

    config = AgentConfig(model="test-model")
    agent = create_validator_agent(config)

    assert agent is not None
