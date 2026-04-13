import pytest
import os
import json
import tempfile
from unittest.mock import MagicMock, patch, AsyncMock
from trashdig.agents.hunter import HunterAgent, create_hunter_agent, load_prompt
from trashdig.config import AgentConfig

@pytest.mark.anyio
@patch("trashdig.agents.hunter.read_file_content")
async def test_hunter_hunt_vulnerabilities(mock_read):
    mock_read.return_value = "vulnerable code"
    
    with tempfile.TemporaryDirectory() as tmpdir:
        findings_dir = os.path.join(tmpdir, "findings")
        os.makedirs(findings_dir)
        
        with patch.object(HunterAgent, "run_async", new_callable=AsyncMock) as mock_run:
            mock_response = MagicMock()
            mock_response.text = json.dumps({
                "findings": [{
                    "title": "SQL Injection",
                    "description": "desc",
                    "severity": "High",
                    "vulnerable_code": "code",
                    "impact": "impact",
                    "exploitation_path": "path",
                    "remediation": "rem"
                }],
                "hypotheses": [{
                    "target": "other.py",
                    "description": "need to trace x",
                    "confidence": 0.8
                }]
            })
            mock_run.return_value = mock_response
            
            agent = HunterAgent(name="hunter", model="gemini-2.0-flash")
            results = await agent.hunt_vulnerabilities(["test.py"], project_root=tmpdir)
            
            findings = results["findings"]
            hypotheses = results["hypotheses"]
            
            assert len(findings) == 1
            assert findings[0].title == "SQL Injection"
            assert len(hypotheses) == 1
            assert hypotheses[0]["target"] == "other.py"
            assert os.path.exists(findings_dir)
            # Check if a file was saved in findings_dir
            assert len(os.listdir(findings_dir)) == 1

@patch("trashdig.agents.hunter.load_prompt")
@patch("google.adk.agents.LlmAgent.__init__")
def test_create_hunter_agent(mock_init, mock_load):
    mock_load.return_value = "instruction"
    mock_init.return_value = None
    
    config = AgentConfig(model="test-model")
    agent = create_hunter_agent(config)
    
    assert agent is not None
