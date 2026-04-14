import pytest
import json
from unittest.mock import MagicMock, patch, AsyncMock
from trashdig.agents.recon import StackScoutAgent, WebRouteMapperAgent, create_stack_scout_agent, create_web_route_mapper_agent
from trashdig.config import Config, AgentConfig

@pytest.fixture
def mock_config():
    config = MagicMock(spec=Config)
    agent_config = AgentConfig(model="test-model", provider="google")
    config.get_agent_config.return_value = agent_config
    config.provider = "google"
    return config

def test_create_stack_scout_agent(mock_config):
    with patch("trashdig.agents.recon.load_prompt", return_value="StackScout Prompt"):
        agent = create_stack_scout_agent(config=mock_config.get_agent_config("stack_scout"))
        assert agent.name == "stack_scout"
        assert agent.model == "test-model"

def test_create_web_route_mapper_agent(mock_config):
    with patch("trashdig.agents.recon.load_prompt", return_value="WebRouteMapper Prompt"):
        agent = create_web_route_mapper_agent(config=mock_config.get_agent_config("web_route_mapper"))
        assert agent.name == "web_route_mapper"
        assert agent.model == "test-model"

@pytest.mark.anyio
@patch("trashdig.agents.recon.get_project_structure")
@patch("trashdig.agents.recon.detect_frameworks")
async def test_stack_scout_scan(mock_detect, mock_get_struct, mock_config):
    mock_get_struct.return_value = ["src/main.py", "package.json"]
    mock_detect.return_value = {"web_frameworks": ["Express"]}
    
    agent = StackScoutAgent(name="stack_scout", model="test-model")
    mock_engine = MagicMock()
    mock_result = MagicMock()
    mock_result.text = json.dumps({
        "tech_stack": "Node.js/Express",
        "is_web_app": True,
        "mapping": {"src/main.py": {"summary": "entry point", "is_high_value": True}},
        "hypotheses": []
    })
    mock_result.tool_calls = []
    mock_result.input_tokens = 10
    mock_result.output_tokens = 20
    mock_engine.run = AsyncMock(return_value=mock_result)
    
    results = await agent.scan(root_path=".", engine=mock_engine)
    
    assert results["tech_stack"] == "Node.js/Express"
    assert results["is_web_app"] is True
    assert "src/main.py" in results["mapping"]
    assert mock_engine.run.called

@pytest.mark.anyio
async def test_web_route_mapper_map_routes(mock_config):
    agent = WebRouteMapperAgent(name="web_route_mapper", model="test-model")
    mock_engine = MagicMock()
    mock_result = MagicMock()
    mock_result.text = json.dumps({
        "attack_surface": [{"route": "/api", "method": "GET", "handler": "main.py"}]
    })
    mock_result.tool_calls = []
    mock_result.input_tokens = 5
    mock_result.output_tokens = 15
    mock_engine.run = AsyncMock(return_value=mock_result)
    
    results = await agent.map_routes(root_path=".", engine=mock_engine)
    
    assert len(results["attack_surface"]) == 1
    assert results["attack_surface"][0]["route"] == "/api"
    assert mock_engine.run.called
