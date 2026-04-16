from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from trashdig.agents.skeptic import SkepticAgent, create_skeptic_agent
from trashdig.config import AgentConfig


@pytest.mark.anyio
@patch("trashdig.agents.coordinator.run_agent", new_callable=AsyncMock)
async def test_skeptic_run(mock_run):
    text_response = (
        '```json\n'
        '{"is_valid": true, "skeptic_notes": "Looks legit", "confidence": 0.8}\n'
        '```'
    )

    mock_run.return_value = text_response

    agent = SkepticAgent(name="skeptic", model="gemini-2.0-flash")
    text = await mock_run(agent, "Review finding", "session", MagicMock())

    assert "is_valid" in text
    assert "Looks legit" in text
    mock_run.assert_called_once()


@patch("trashdig.agents.skeptic.load_prompt")
@patch("google.adk.agents.LlmAgent.__init__")
def test_create_skeptic_agent(mock_init, mock_load):
    mock_load.return_value = "instruction"
    mock_init.return_value = None

    config = AgentConfig(model="test-model")
    agent = create_skeptic_agent(config)

    assert agent is not None
