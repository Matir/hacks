import pytest
from unittest.mock import MagicMock, patch, AsyncMock, ANY
from trashdig.agents.validator import ValidatorAgent, create_validator_agent, load_prompt
from trashdig.findings import Finding
from trashdig.config import AgentConfig
from trashdig.engine.engine import EngineResult


def test_load_prompt():
    with patch("builtins.open", MagicMock(return_value=MagicMock(__enter__=lambda self: MagicMock(read=lambda: "test prompt")))):
        prompt = load_prompt("fake_path.md")
        assert prompt == "test prompt"


@pytest.mark.anyio
@patch("trashdig.agents.validator.read_file_content")
@patch("trashdig.engine.engine.Engine.run", new_callable=AsyncMock)
async def test_validator_verify_finding(mock_engine_run, mock_read):
    mock_read.return_value = "print('vulnerable_code')"
    text_response = (
        '```json\n'
        '{"status": "Verified", "poc_code": "python poc.py", "reasoning": "Confirmed"}\n'
        '```'
    )
    mock_engine_run.return_value = EngineResult(
        text=text_response,
        input_tokens=150,
        output_tokens=75,
        tool_calls=[]
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
    mock_engine_run.assert_called_once()


@pytest.mark.anyio
@patch("trashdig.agents.validator.read_file_content")
@patch("trashdig.engine.engine.Engine.run", new_callable=AsyncMock)
async def test_validator_verify_finding_json_error(mock_engine_run, mock_read):
    mock_read.return_value = "code"
    mock_engine_run.return_value = EngineResult(
        text="invalid json",
        input_tokens=10,
        output_tokens=5,
        tool_calls=[]
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

    assert result["status"] == "Unverified"
    assert "error" in result
    assert result["raw"] == "invalid json"


@pytest.mark.anyio
@patch("trashdig.agents.validator.read_file_content")
@patch("trashdig.engine.engine.Engine.run", new_callable=AsyncMock)
async def test_validator_conversation_logging(mock_engine_run, mock_read):
    mock_read.return_value = "code"
    text_response = '{"status": "Unverified"}'
    mock_engine_run.return_value = EngineResult(
        text=text_response,
        input_tokens=123,
        output_tokens=456,
        tool_calls=[{"name": "bash", "args": {}}]
    )

    mock_log_fn = MagicMock()
    agent = ValidatorAgent(name="validator", model="gemini-2.0-flash")
    finding = Finding(title="f", description="d", severity="s", vulnerable_code="c", file_path="p", impact="i", exploitation_path="e", remediation="r")
    await agent.verify_finding(finding, conversation_log_fn=mock_log_fn)

    mock_log_fn.assert_called_once_with(
        "validator",
        ANY,
        text_response,
        [{"name": "bash", "args": {}}],
        123,
        456
    )


@patch("trashdig.agents.validator.load_prompt")
@patch("google.adk.agents.LlmAgent.__init__")
def test_create_validator_agent(mock_init, mock_load):
    mock_load.return_value = "instruction"
    mock_init.return_value = None

    config = AgentConfig(model="test-model")
    agent = create_validator_agent(config)

    assert agent is not None
