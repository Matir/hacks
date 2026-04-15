import pytest
from unittest.mock import MagicMock
from trashdig.agents.callbacks import TrashDigCallback
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_response import LlmResponse
import google.genai.types as genai_types

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
    coord._engine = MagicMock()
    coord._engine.total_messages = 0
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
    
    # Check engine message count update
    assert mock_coordinator._engine.total_messages == 1
    
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
    
    # Check logging to TUI
    mock_coordinator.log.assert_called_once()
    assert "test_tool" in mock_coordinator.log.call_args[0][0]

def test_callback_attach_to(mock_coordinator):
    cb = TrashDigCallback.get_instance(mock_coordinator)
    agent = MagicMock()
    
    cb.attach_to(agent)
    
    assert agent.before_tool_callback == cb.on_before_tool
    assert agent.after_model_callback == cb.on_after_model
    assert agent.on_model_error_callback == cb.on_model_error
