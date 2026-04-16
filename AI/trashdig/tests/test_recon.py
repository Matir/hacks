import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from trashdig.agents.recon import (
    StackScoutAgent,
    WebRouteMapperAgent,
    create_stack_scout_agent,
    create_web_route_mapper_agent,
)
from trashdig.config import Config


@pytest.fixture
def mock_config():
    config = MagicMock(spec=Config)
    config.get_agent_config.return_value = MagicMock(model="test-model", provider="google")
    return config

@pytest.mark.anyio
@patch("trashdig.agents.coordinator.run_agent", new_callable=AsyncMock)
async def test_stack_scout_run(mock_run, mock_config):
    agent = StackScoutAgent(name="stack_scout", model="test-model")
    
    text_response = json.dumps({
        "tech_stack": "Node.js/Express",
        "is_web_app": True,
        "mapping": {"src/main.py": {"summary": "entry point", "is_high_value": True}},
        "hypotheses": []
    })
    
    mock_run.return_value = text_response
    
    # In actual usage, we call run_agent
    text = await mock_run(agent, "Analyze project", "session", MagicMock())
    data = json.loads(text)
    
    assert data["tech_stack"] == "Node.js/Express"
    assert data["is_web_app"] is True
    assert "src/main.py" in data["mapping"]

@pytest.mark.anyio
@patch("trashdig.agents.coordinator.run_agent", new_callable=AsyncMock)
async def test_web_route_mapper_run(mock_run, mock_config):
    agent = WebRouteMapperAgent(name="web_route_mapper", model="test-model")
    
    text_response = json.dumps({
        "attack_surface": [{"route": "/api", "method": "GET", "handler": "main.py"}]
    })
    
    mock_run.return_value = text_response
    
    text = await mock_run(agent, "Map routes", "session", MagicMock())
    data = json.loads(text)
    
    assert len(data["attack_surface"]) == 1
    assert data["attack_surface"][0]["route"] == "/api"

@patch("trashdig.agents.recon.load_prompt")
@patch("google.adk.agents.LlmAgent.__init__")
def test_create_stack_scout_agent(mock_init, mock_load, mock_config):
    mock_load.return_value = "instruction"
    mock_init.return_value = None
    agent = create_stack_scout_agent(config=mock_config.get_agent_config("stack_scout"))
    assert agent is not None

@patch("trashdig.agents.recon.load_prompt")
@patch("google.adk.agents.LlmAgent.__init__")
def test_create_web_route_mapper_agent(mock_init, mock_load, mock_config):
    mock_load.return_value = "instruction"
    mock_init.return_value = None
    agent = create_web_route_mapper_agent(config=mock_config.get_agent_config("web_route_mapper"))
    assert agent is not None
