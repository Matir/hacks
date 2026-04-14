import pytest
from unittest.mock import MagicMock, patch, AsyncMock, ANY
from trashdig.agents.skeptic import SkepticAgent, create_skeptic_agent, load_prompt
from trashdig.findings import Finding
from trashdig.config import AgentConfig
from trashdig.engine.engine import EngineResult


def test_load_prompt():
    with patch("builtins.open", MagicMock(return_value=MagicMock(__enter__=lambda self: MagicMock(read=lambda: "test prompt")))):
        prompt = load_prompt("fake_path.md")
        assert prompt == "test prompt"


@pytest.mark.anyio
@patch("trashdig.agents.skeptic.read_file_content")
@patch("trashdig.engine.engine.Engine.run", new_callable=AsyncMock)
async def test_skeptic_debunk_finding_survived(mock_engine_run, mock_read):
    mock_read.return_value = "print('vulnerable_code')"
    text_response = (
        '```json\n'
        '{"is_valid": true, "skeptic_notes": "Looks legit", "confidence": 0.8}\n'
        '```'
    )
    mock_engine_run.return_value = EngineResult(
        text=text_response,
        input_tokens=150,
        output_tokens=75,
        tool_calls=[]
    )

    agent = SkepticAgent(name="skeptic", model="gemini-2.0-flash")
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

    result = await agent.debunk_finding(finding)

    assert result["is_valid"] is True
    assert result["skeptic_notes"] == "Looks legit"
    mock_engine_run.assert_called_once()


@pytest.mark.anyio
@patch("trashdig.agents.skeptic.read_file_content")
@patch("trashdig.engine.engine.Engine.run", new_callable=AsyncMock)
async def test_skeptic_debunk_finding_debunked(mock_engine_run, mock_read):
    mock_read.return_value = "print('vulnerable_code')"
    text_response = (
        '```json\n'
        '{"is_valid": false, "skeptic_notes": "False positive because of X", "confidence": 0.9}\n'
        '```'
    )
    mock_engine_run.return_value = EngineResult(
        text=text_response,
        input_tokens=150,
        output_tokens=75,
        tool_calls=[]
    )

    agent = SkepticAgent(name="skeptic", model="gemini-2.0-flash")
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

    result = await agent.debunk_finding(finding)

    assert result["is_valid"] is False
    assert result["skeptic_notes"] == "False positive because of X"
    mock_engine_run.assert_called_once()


@pytest.mark.anyio
@patch("trashdig.agents.skeptic.read_file_content")
@patch("trashdig.engine.engine.Engine.run", new_callable=AsyncMock)
async def test_skeptic_debunk_finding_json_error(mock_engine_run, mock_read):
    mock_read.return_value = "code"
    mock_engine_run.return_value = EngineResult(
        text="invalid json",
        input_tokens=10,
        output_tokens=5,
        tool_calls=[]
    )

    agent = SkepticAgent(name="skeptic", model="gemini-2.0-flash")
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

    result = await agent.debunk_finding(finding)

    assert result["is_valid"] is True # Failsafe
    assert "Error parsing response" in result["skeptic_notes"]


@patch("trashdig.agents.skeptic.load_prompt")
@patch("google.adk.agents.LlmAgent.__init__")
def test_create_skeptic_agent(mock_init, mock_load):
    mock_load.return_value = "instruction"
    mock_init.return_value = None

    config = AgentConfig(model="test-model")
    agent = create_skeptic_agent(config)

    assert agent is not None
