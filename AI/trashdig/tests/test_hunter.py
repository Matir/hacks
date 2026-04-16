import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from trashdig.agents.hunter import HunterAgent, create_hunter_agent
from trashdig.config import AgentConfig


@pytest.mark.anyio
@patch("trashdig.agents.coordinator.run_agent", new_callable=AsyncMock)
async def test_hunter_run(mock_run):
    text_response = json.dumps({
        "findings": [{
            "title": "SQL Injection",
            "description": "desc",
            "severity": "High",
            "vulnerable_code": "code",
            "impact": "impact",
            "exploitation_path": "path",
            "remediation": "rem",
        }],
        "hypotheses": [{
            "target": "other.py",
            "description": "need to trace x",
            "confidence": 0.8,
        }],
    })

    mock_run.return_value = text_response

    agent = HunterAgent(name="hunter", model="gemini-2.0-flash")
    text = await mock_run(agent, "Analyze test.py", "session", MagicMock())

    assert "SQL Injection" in text
    data = json.loads(text)
    assert len(data["findings"]) == 1
    mock_run.assert_called_once()


@patch("trashdig.agents.hunter.load_prompt")
@patch("google.adk.agents.LlmAgent.__init__")
def test_create_hunter_agent(mock_init, mock_load):
    mock_load.return_value = "instruction"
    mock_init.return_value = None

    config = AgentConfig(model="test-model")
    agent = create_hunter_agent(config)

    assert agent is not None
