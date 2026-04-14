import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch, ANY
from trashdig.engine.engine import Engine, EngineState, EngineResult
import google.genai.types as genai_types

@pytest.fixture
def mock_agent():
    agent = MagicMock()
    agent.name = "test-agent"
    return agent

@pytest.fixture
def engine():
    return Engine(max_retries=1, retry_delay=0.1)

@pytest.mark.anyio
async def test_engine_run_success(engine, mock_agent):
    # Mock Runner.run_async to yield events
    mock_event = MagicMock()
    mock_event.content = genai_types.Content(
        role="model",
        parts=[genai_types.Part(text="Hello world")]
    )
    mock_event.is_final_response.return_value = True
    
    # Mock usage metadata
    usage = MagicMock()
    usage.prompt_token_count = 10
    usage.candidates_token_count = 5
    mock_event.usage_metadata = usage

    async def mock_run_async(*args, **kwargs):
        yield mock_event

    with patch("trashdig.engine.engine.Runner") as MockRunner:
        instance = MockRunner.return_value
        instance.run_async = mock_run_async
        
        result = await engine.run(mock_agent, "test prompt")
        
        assert result.text == "Hello world"
        assert result.input_tokens == 10
        assert result.output_tokens == 5
        assert result.status == EngineState.COMPLETED
        assert engine.total_input_tokens == 10
        assert engine.total_output_tokens == 5

@pytest.mark.anyio
async def test_engine_tool_calling_state(engine, mock_agent):
    # First event with function call
    event1 = MagicMock()
    # Use real types to avoid Pydantic ValidationError
    fc = genai_types.FunctionCall(name="test_tool", args={"arg1": "val1"})
    event1.content = genai_types.Content(
        role="model",
        parts=[genai_types.Part(function_call=fc)]
    )
    event1.is_final_response.return_value = False
    event1.usage_metadata = None
    event1.response = None
    event1.raw_response = None
    
    # Second event with final response
    event2 = MagicMock()
    event2.content = genai_types.Content(
        role="model",
        parts=[genai_types.Part(text="Result")]
    )
    event2.is_final_response.return_value = True
    event2.usage_metadata = None
    event2.response = None
    event2.raw_response = None

    async def mock_run_async(*args, **kwargs):
        yield event1
        # In actual ADK, there might be more events, but this tests our state transition
        assert engine.state == EngineState.WAITING_FOR_TOOLS
        yield event2

    with patch("trashdig.engine.engine.Runner") as MockRunner:
        instance = MockRunner.return_value
        instance.run_async = mock_run_async
        
        result = await engine.run(mock_agent, "test prompt")
        assert result.status == EngineState.COMPLETED
        assert engine.state == EngineState.COMPLETED
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0]["name"] == "test_tool"

@pytest.mark.anyio
async def test_engine_retry_on_failure(engine, mock_agent):
    # Mock Runner to fail once, then succeed
    mock_event = MagicMock()
    mock_event.content = genai_types.Content(
        role="model",
        parts=[genai_types.Part(text="Success")]
    )
    mock_event.is_final_response.return_value = True
    mock_event.usage_metadata = None
    mock_event.response = None
    mock_event.raw_response = None
    
    call_count = 0
    async def mock_run_async_fail_then_succeed(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("Transient error")
            if False: yield # Make it an async generator
        else:
            yield mock_event

    with patch("trashdig.engine.engine.Runner") as MockRunner:
        instance = MockRunner.return_value
        instance.run_async = mock_run_async_fail_then_succeed
        
        on_error = MagicMock()
        result = await engine.run(mock_agent, "test prompt", on_error=on_error)
        
        assert result.text == "Success"
        assert call_count == 2
        on_error.assert_called_once()

@pytest.mark.anyio
async def test_engine_max_retries_exceeded(engine, mock_agent):
    async def mock_run_async_always_fail(*args, **kwargs):
        if False: yield # Make it an async generator
        raise Exception("Permanent error")

    with patch("trashdig.engine.engine.Runner") as MockRunner:
        instance = MockRunner.return_value
        instance.run_async = mock_run_async_always_fail
        
        with pytest.raises(Exception, match="Permanent error"):
            await engine.run(mock_agent, "test prompt")
        
        assert engine.state == EngineState.FAILED

@pytest.mark.anyio
async def test_engine_context_compaction(mock_agent):
    # Setup engine with small context for testing
    engine = Engine(max_context_tokens=1000, compaction_threshold=0.5)
    
    mock_event = MagicMock()
    mock_event.content = genai_types.Content(
        role="model",
        parts=[genai_types.Part(text="Response")]
    )
    mock_event.is_final_response.return_value = True
    
    # Mock usage triggering compaction
    usage = MagicMock()
    usage.prompt_token_count = 600 # > 50% of 1000
    usage.candidates_token_count = 10
    mock_event.usage_metadata = usage

    async def mock_run_async(*args, **kwargs):
        yield mock_event

    with patch("trashdig.engine.engine.Runner") as MockRunner, \
         patch.object(engine, "_compact_history", new_callable=AsyncMock) as mock_compact:
        instance = MockRunner.return_value
        instance.run_async = mock_run_async
        
        await engine.run(mock_agent, "test prompt")
        
        # Verify compaction was called
        mock_compact.assert_called_once_with(mock_agent.name, "trashdig", ANY)
