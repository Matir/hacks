import pytest
import json
import subprocess
from unittest.mock import MagicMock, patch, AsyncMock
from trashdig.tools import get_ast_summary, container_bash_tool
from trashdig.agents.recon import StackScoutAgent
from trashdig.agents.coordinator import Coordinator
from trashdig.agents.types import Task, TaskType, TaskStatus
from trashdig.config import Config
from trashdig.engine.engine import EngineResult

def test_get_ast_summary_no_definitions():
    """Test get_ast_summary with a file containing no classes or functions."""
    with patch("builtins.open", MagicMock()):
        with patch("trashdig.tools._get_ts_language", return_value=MagicMock()):
            with patch("tree_sitter.Parser") as mock_parser_class:
                mock_parser = mock_parser_class.return_value
                mock_tree = mock_parser.parse.return_value
                mock_tree.root_node.children = [] # No children
                
                result = get_ast_summary("empty.py", "python")
                assert result == "No top-level definitions found."

@patch("subprocess.run")
@patch("trashdig.tools.bash_tool")
def test_container_bash_tool_docker_missing(mock_bash, mock_run):
    """Test container_bash_tool falls back to host bash_tool when Docker is missing."""
    # Mock Docker not found
    mock_run.side_effect = FileNotFoundError
    mock_bash.return_value = "host_output"
    
    result = container_bash_tool("ls")
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
            assert result["error"] == "Failed to parse StackScout response"



@pytest.mark.anyio
async def test_coordinator_task_failure():
    """Test Coordinator continues processing other tasks if one fails."""
    mock_config = MagicMock(spec=Config)
    mock_config.agents = {}
    mock_config.max_parallel_tasks = 3
    
    with patch("trashdig.agents.coordinator.create_stack_scout_agent"), \
         patch("trashdig.agents.coordinator.create_web_route_mapper_agent"), \
         patch("trashdig.agents.coordinator.create_hunter_agent"), \
         patch("trashdig.agents.coordinator.create_skeptic_agent"), \
         patch("trashdig.agents.coordinator.create_validator_agent"):
        
        coord = Coordinator(mock_config)
        
        task1 = Task(TaskType.SCAN, "target1")
        task2 = Task(TaskType.SCAN, "target2")
        
        coord.spawn_task(task1)
        coord.spawn_task(task2)
        
        # Mock _handle_scan to fail for task1 and succeed for task2
        async def mock_handle(task):
            if task.target == "target1":
                raise ValueError("Scan failed")
            # task2 succeeds implicitly
            
        coord._handle_scan = AsyncMock(side_effect=mock_handle)
        
        await coord.run_loop()
        
        assert task1.status == TaskStatus.FAILED
        assert task2.status == TaskStatus.COMPLETED
        assert len(coord.completed_tasks) == 1
        assert coord.completed_tasks[0].target == "target2"
