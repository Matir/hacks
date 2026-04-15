import pytest
import json
from unittest.mock import patch, AsyncMock
from trashdig.agents.hunter import HunterAgent, create_hunter_agent
from trashdig.config import AgentConfig
from trashdig.engine.engine import EngineResult


@pytest.mark.anyio
@patch("trashdig.engine.engine.Engine.run", new_callable=AsyncMock)
async def test_hunter_run(mock_engine_run):
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
    mock_engine_run.return_value = EngineResult(
        text=text_response,
        input_tokens=200,
        output_tokens=100,
        tool_calls=[]
    )

    agent = HunterAgent(name="hunter", model="gemini-2.0-flash")
    from trashdig.engine.engine import Engine
    engine = Engine()
    result = await engine.run(agent, "Analyze test.py")

    assert "SQL Injection" in result.text
    data = json.loads(result.text)
    assert len(data["findings"]) == 1
    mock_engine_run.assert_called_once()


@patch("trashdig.agents.hunter.load_prompt")
@patch("google.adk.agents.LlmAgent.__init__")
def test_create_hunter_agent(mock_init, mock_load):
    mock_load.return_value = "instruction"
    mock_init.return_value = None

    config = AgentConfig(model="test-model")
    agent = create_hunter_agent(config)

    assert agent is not None
