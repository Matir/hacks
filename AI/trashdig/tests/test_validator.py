import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from trashdig.agents.validator import ValidatorAgent, create_validator_agent, load_prompt
from trashdig.config import AgentConfig
from trashdig.engine.engine import EngineResult


def test_load_prompt():
    with patch("builtins.open", MagicMock(return_value=MagicMock(__enter__=lambda self: MagicMock(read=lambda: "test prompt")))):
        prompt = load_prompt("fake_path.md")
        assert prompt == "test prompt"


@pytest.mark.anyio
@patch("trashdig.engine.engine.Engine.run", new_callable=AsyncMock)
async def test_validator_run(mock_engine_run):
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
    from trashdig.engine.engine import Engine
    engine = Engine()
    result = await engine.run(agent, "Verify finding")

    assert "Verified" in result.text
    assert "python poc.py" in result.text
    mock_engine_run.assert_called_once()


@patch("trashdig.agents.validator.load_prompt")
@patch("google.adk.agents.LlmAgent.__init__")
def test_create_validator_agent(mock_init, mock_load):
    mock_load.return_value = "instruction"
    mock_init.return_value = None

    config = AgentConfig(model="test-model")
    agent = create_validator_agent(config)

    assert agent is not None
