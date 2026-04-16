from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from trashdig.agents.validator import ValidatorAgent, create_validator_agent
from trashdig.config import AgentConfig


@pytest.mark.anyio
@patch("trashdig.agents.coordinator.run_agent", new_callable=AsyncMock)
async def test_validator_run(mock_run):
    text_response = (
        '```json\n'
        '{"status": "Verified", "poc_code": "python poc.py", "reasoning": "Confirmed"}\n'
        '```'
    )

    mock_run.return_value = text_response

    agent = ValidatorAgent(name="validator", model="gemini-2.0-flash")
    text = await mock_run(agent, "Verify finding", "session", MagicMock())

    assert "Verified" in text
    assert "python poc.py" in text
    mock_run.assert_called_once()


@patch("trashdig.agents.validator.load_prompt")
@patch("google.adk.agents.LlmAgent.__init__")
def test_create_validator_agent(mock_init, mock_load):
    mock_load.return_value = "instruction"
    mock_init.return_value = None

    config = AgentConfig(model="test-model")
    agent = create_validator_agent(config)

    assert agent is not None
