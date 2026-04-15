import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from trashdig.agents.skeptic import SkepticAgent, create_skeptic_agent, load_prompt
from trashdig.config import AgentConfig
from trashdig.engine.engine import EngineResult


def test_load_prompt():
    with patch("builtins.open", MagicMock(return_value=MagicMock(__enter__=lambda self: MagicMock(read=lambda: "test prompt")))):
        prompt = load_prompt("fake_path.md")
        assert prompt == "test prompt"


@pytest.mark.anyio
@patch("trashdig.engine.engine.Engine.run", new_callable=AsyncMock)
async def test_skeptic_run(mock_engine_run):
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
    from trashdig.engine.engine import Engine
    engine = Engine()
    result = await engine.run(agent, "Review finding")

    assert "is_valid" in result.text
    assert "Looks legit" in result.text
    mock_engine_run.assert_called_once()


@patch("trashdig.agents.skeptic.load_prompt")
@patch("google.adk.agents.LlmAgent.__init__")
def test_create_skeptic_agent(mock_init, mock_load):
    mock_load.return_value = "instruction"
    mock_init.return_value = None

    config = AgentConfig(model="test-model")
    agent = create_skeptic_agent(config)

    assert agent is not None
