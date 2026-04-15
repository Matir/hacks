import pytest
import os
import json
import tempfile
from unittest.mock import MagicMock, patch, AsyncMock, ANY
from trashdig.agents.hunter import HunterAgent, create_hunter_agent
from trashdig.config import AgentConfig
from trashdig.engine.engine import EngineResult


@pytest.mark.anyio
@patch("trashdig.agents.hunter.read_file_content")
@patch("trashdig.engine.engine.Engine.run", new_callable=AsyncMock)
async def test_hunter_hunt_vulnerabilities(mock_engine_run, mock_read):
    mock_read.return_value = "vulnerable code"
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

    with tempfile.TemporaryDirectory() as tmpdir:
        findings_dir = os.path.join(tmpdir, "findings")
        os.makedirs(findings_dir)

        agent = HunterAgent(name="hunter", model="gemini-2.0-flash")
        results = await agent.hunt_vulnerabilities(["test.py"], project_root=tmpdir)

        findings = results["findings"]
        hypotheses = results["hypotheses"]

        assert len(findings) == 1
        assert findings[0].title == "SQL Injection"
        assert len(hypotheses) == 1
        assert hypotheses[0]["target"] == "other.py"
        assert os.path.exists(findings_dir)
        assert len(os.listdir(findings_dir)) == 1
        mock_engine_run.assert_called_once()


@pytest.mark.anyio
@patch("trashdig.agents.hunter.read_file_content")
@patch("trashdig.engine.engine.Engine.run", new_callable=AsyncMock)
async def test_hunter_hunt_vulnerabilities_json_error(mock_engine_run, mock_read):
    mock_read.return_value = "code"
    mock_engine_run.return_value = EngineResult(
        text="not valid json",
        input_tokens=10,
        output_tokens=5,
        tool_calls=[]
    )

    agent = HunterAgent(name="hunter", model="gemini-2.0-flash")
    results = await agent.hunt_vulnerabilities(["test.py"], project_root=".")

    # JSON parse error is swallowed with continue; results come back empty
    assert results["findings"] == []
    assert results["hypotheses"] == []


@pytest.mark.anyio
@patch("trashdig.agents.hunter.read_file_content")
@patch("trashdig.engine.engine.Engine.run", new_callable=AsyncMock)
async def test_hunter_conversation_logging(mock_engine_run, mock_read):
    mock_read.return_value = "code"
    text_response = '{"findings": [], "hypotheses": []}'
    mock_engine_run.return_value = EngineResult(
        text=text_response,
        input_tokens=123,
        output_tokens=456,
        tool_calls=[{"name": "trace", "args": {}}]
    )

    mock_log_fn = MagicMock()
    agent = HunterAgent(name="hunter", model="gemini-2.0-flash")
    await agent.hunt_vulnerabilities(["test.py"], conversation_log_fn=mock_log_fn)

    mock_log_fn.assert_called_once_with(
        "hunter",
        ANY,
        text_response,
        [{"name": "trace", "args": {}}],
        123,
        456
    )


@patch("trashdig.agents.hunter.load_prompt")
@patch("google.adk.agents.LlmAgent.__init__")
def test_create_hunter_agent(mock_init, mock_load):
    mock_load.return_value = "instruction"
    mock_init.return_value = None

    config = AgentConfig(model="test-model")
    agent = create_hunter_agent(config)

    assert agent is not None
