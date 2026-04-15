import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from trashdig.tools import get_ast_summary, container_bash_tool
from trashdig.agents.recon import StackScoutAgent
from trashdig.agents.coordinator import Coordinator
from trashdig.config import Config
from trashdig.engine.engine import EngineResult

from google.adk.agents import LlmAgent

async def maybe_await(coro_or_val):
    if asyncio.iscoroutine(coro_or_val):
        return await coro_or_val
    return coro_or_val

def create_mock_agent(name="dummy"):
    return LlmAgent(
        name=name,
        model="gemini-2.0-flash",
        instruction="instruction",
        description="description"
    )

@pytest.mark.anyio
async def test_get_ast_summary_no_definitions():
    """Test get_ast_summary with a file containing no classes or functions."""
    with patch("builtins.open", MagicMock()):
        with patch("trashdig.tools._get_ts_language", return_value=MagicMock()):
            with patch("tree_sitter.Parser") as mock_parser_class:
                mock_parser = mock_parser_class.return_value
                mock_tree = mock_parser.parse.return_value
                mock_tree.root_node.children = [] # No children
                
                result = await maybe_await(get_ast_summary("empty.py", "python"))
                assert result == "No top-level definitions found."

@pytest.mark.anyio
@patch("subprocess.run")
@patch("trashdig.tools.bash_tool")
async def test_container_bash_tool_docker_missing(mock_bash, mock_run):
    """Test container_bash_tool falls back to host bash_tool when Docker is missing."""
    # Mock Docker not found
    mock_run.side_effect = FileNotFoundError
    mock_bash.return_value = "host_output"
    
    # container_bash_tool is decorated with artifact_tool, so it might return a coroutine
    # if tool_context is passed, but here it returns a string.
    result = await maybe_await(container_bash_tool("ls"))
    assert "[Warning: Docker not found. Falling back to host bash_tool]" in result
    assert "host_output" in result
    mock_bash.assert_called_once_with("ls", 60)

@pytest.mark.anyio
async def test_stack_scout_malformed_json():
    """Test StackScoutAgent handles malformed JSON response from LLM."""
    with patch("trashdig.agents.recon.load_prompt", return_value="instruction"):
        agent = StackScoutAgent(name="test", model="test-model", instruction="test")

        with patch("trashdig.engine.engine.Engine.run", new_callable=AsyncMock) as mock_engine_run, \
             patch("trashdig.agents.recon.get_project_structure", return_value=[]), \
             patch("trashdig.agents.recon.detect_frameworks", return_value={}):
            mock_engine_run.return_value = EngineResult(
                text="This is not JSON",
                input_tokens=10,
                output_tokens=5,
                tool_calls=[]
            )
            result = await agent.scan(".")
            assert "error" in result or "mapping" in result

@pytest.mark.anyio
async def test_coordinator_init_validation(tmp_path):
    """Test Coordinator initialization with mocks passing Pydantic validation."""
    mock_config = MagicMock(spec=Config)
    mock_config.agents = {}
    mock_config.get_agent_config.return_value = MagicMock(model="gemini-2.0-flash")
    # Use a real string for db_path to avoid urlparse error with MagicMock
    db_file = tmp_path / "test.db"
    mock_config.db_path = str(db_file)
    
    with patch("trashdig.agents.coordinator.create_stack_scout_agent", return_value=create_mock_agent("stack_scout")), \
         patch("trashdig.agents.coordinator.create_web_route_mapper_agent", return_value=create_mock_agent("web_route_mapper")), \
         patch("trashdig.agents.coordinator.create_hunter_agent", return_value=create_mock_agent("hunter")), \
         patch("trashdig.agents.coordinator.create_skeptic_agent", return_value=create_mock_agent("skeptic")), \
         patch("trashdig.agents.coordinator.create_validator_agent", return_value=create_mock_agent("validator")):
        
        coord = Coordinator(mock_config)
        assert coord.hunter is not None
