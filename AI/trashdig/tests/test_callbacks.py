from unittest.mock import MagicMock

import google.genai.types as genai_types
import pytest
from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_response import LlmResponse

from trashdig.agents.callbacks import TrashDigCallback
from trashdig.agents.types import EngineState


@pytest.fixture(autouse=True)
def reset_callback_singleton():
    TrashDigCallback._reset()
    yield
    TrashDigCallback._reset()

@pytest.fixture
def mock_coordinator():
    coord = MagicMock()
    coord.project_path = "test_project"
    coord._db = MagicMock()
    coord._cost_tracker = MagicMock()
    coord._state = EngineState.IDLE
    # Mock _agent_by_name to return a mock agent with a model
    agent = MagicMock()
    agent.model = "gemini-2.0-flash"
    coord._agent_by_name.return_value = agent
    return coord

def test_callback_on_after_model(mock_coordinator):
    cb = TrashDigCallback.get_instance(mock_coordinator)
    
    ctx = MagicMock(spec=CallbackContext)
    ctx.agent_name = "test_agent"
    ctx.session_id = "test_session"
    
    # Mock UsageMetadata to avoid Pydantic validation issues with field names
    usage = MagicMock()
    usage.prompt_token_count = 100
    usage.candidates_token_count = 50
    
    resp = MagicMock(spec=LlmResponse)
    resp.content = genai_types.Content(parts=[genai_types.Part(text="Response")])
    resp.usage_metadata = usage
    
    cb.on_after_model(ctx, resp)
    
    # Check cost tracker update
    mock_coordinator._cost_tracker.record_usage.assert_called_once_with(
        "gemini-2.0-flash", 100, 50
    )
    
    # Check TUI signaling
    mock_coordinator._on_stats.assert_called_once_with(
        100, 50, new_msg=True, model_name="gemini-2.0-flash"
    )
    
    # Check DB logging
    mock_coordinator.db.log_conversation.assert_called_once()

def test_callback_on_before_tool(mock_coordinator):
    cb = TrashDigCallback.get_instance(mock_coordinator)
    tool = MagicMock()
    tool.name = "test_tool"
    
    cb.on_before_tool(tool, {"arg1": "val1"}, MagicMock())
    
    # Check state update
    assert mock_coordinator._state == EngineState.WAITING_FOR_TOOLS
    
    # Check logging to TUI
    mock_coordinator.log.assert_called_once()
    assert "test_tool" in mock_coordinator.log.call_args[0][0]

def test_callback_attach_to(mock_coordinator):
    cb = TrashDigCallback.get_instance(mock_coordinator)
    # Use a mock that spec-es LlmAgent so isinstance works
    agent = MagicMock(spec=LlmAgent)
    
    cb.attach_to(agent)
    
    assert agent.before_tool_callback == cb.on_before_tool
    assert agent.after_model_callback == cb.on_after_model
    assert agent.on_model_error_callback == cb.on_model_error
    assert agent.before_agent_callback == cb.on_before_agent
    assert agent.after_agent_callback == cb.on_after_agent

def test_callback_agent_lifecycle(mock_coordinator):
    cb = TrashDigCallback.get_instance(mock_coordinator)
    ctx = MagicMock(spec=CallbackContext)
    
    cb.on_before_agent(context=ctx, agent=None)
    assert mock_coordinator._state == EngineState.RUNNING
    
    cb.on_after_agent(context=ctx, agent=None)
    assert mock_coordinator._state == EngineState.IDLE
