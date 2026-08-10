import asyncio
from unittest.mock import MagicMock

import google.genai.types as genai_types
import pytest
from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_response import LlmResponse
from google.adk.tools.base_tool import BaseTool

from trashdig.agents.coordinator import Coordinator
from trashdig.agents.utils.callbacks import TrashDigCallback
from trashdig.agents.utils.types import EngineState
from trashdig.config import AgentConfig


@pytest.fixture(autouse=True)
def reset_callback_singleton():
    TrashDigCallback._reset()
    yield
    TrashDigCallback._reset()


def _make_agent_config(max_turns=None):
    cfg = MagicMock(spec=AgentConfig)
    cfg.max_turns = max_turns
    return cfg


@pytest.fixture
def mock_coordinator():
    coord = MagicMock(spec=Coordinator)
    coord.on_stats_event = MagicMock()
    coord.on_task_event = MagicMock()
    coord.project_path = "test_project"
    coord._db = MagicMock()
    coord._cost_tracker = MagicMock()
    coord._state = EngineState.IDLE
    coord.pop_pending_hints.return_value = []
    # Default: no turn limit for any agent
    coord.config.get_agent_config.return_value = _make_agent_config(max_turns=None)
    # Mock _agent_by_name to return a mock agent with a model
    agent = MagicMock(spec=LlmAgent)
    agent.model = "gemini-2.0-flash"
    coord._agent_by_name.return_value = agent
    return coord

async def test_callback_on_before_model(mock_coordinator):
    cb = TrashDigCallback.get_instance(mock_coordinator)
    ctx = MagicMock(spec=CallbackContext)
    req = MagicMock()
    req.contents = [genai_types.Content(parts=[genai_types.Part(text="Test Prompt")])]

    await cb.on_before_model(ctx, req)
    assert cb._last_prompt == "Test Prompt"

async def test_callback_on_before_model_awaits_pause(mock_coordinator):
    """Every model call must check the pause gate before proceeding, not just
    the coarse per-phase checkpoints in Coordinator — this is the fix for
    "Pause & Steer" taking effect mid-turn instead of only between phases.
    """
    cb = TrashDigCallback.get_instance(mock_coordinator)
    ctx = MagicMock(spec=CallbackContext)
    req = MagicMock()
    req.contents = []

    await cb.on_before_model(ctx, req)

    mock_coordinator.check_pause.assert_awaited_once()


async def test_callback_on_before_model_blocks_while_paused():
    """A real asyncio.Event-backed check_pause() must actually block the
    callback until resumed, proving the gate is load-bearing and not just
    called-and-ignored.
    """
    coord = MagicMock(spec=Coordinator)
    coord.project_path = "test_project"
    coord._state = EngineState.IDLE
    coord.pop_pending_hints.return_value = []
    coord.config.get_agent_config.return_value = _make_agent_config(max_turns=None)

    # Use a real asyncio.Event so we can assert blocking behaviour precisely,
    # mirroring Coordinator.check_pause(): await self._pause_event.wait().
    real_event = asyncio.Event()

    async def check_pause():
        await real_event.wait()

    coord.check_pause = check_pause

    cb = TrashDigCallback.get_instance(coord)
    ctx = MagicMock(spec=CallbackContext)
    req = MagicMock()
    req.contents = []

    task = asyncio.ensure_future(cb.on_before_model(ctx, req))
    await asyncio.sleep(0)
    assert not task.done(), "on_before_model must block while paused"

    real_event.set()
    await task
    assert task.done()


async def test_callback_on_after_model(mock_coordinator):
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

    await cb.on_after_model(ctx, resp)

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

async def test_callback_on_before_model_injects_pending_hint(mock_coordinator):
    """A queued hint must be appended to the request as a high-priority
    user message, and the state must flip to STEERING while it's injected.
    """
    mock_coordinator.pop_pending_hints.return_value = ["Focus on the SQL sink in db.py"]
    cb = TrashDigCallback.get_instance(mock_coordinator)
    ctx = MagicMock(spec=CallbackContext)
    req = MagicMock()
    req.contents = []

    await cb.on_before_model(ctx, req)

    assert len(req.contents) == 1
    injected_text = req.contents[0].parts[0].text
    assert "Focus on the SQL sink in db.py" in injected_text
    assert mock_coordinator._state == EngineState.STEERING


async def test_callback_on_before_model_no_hint_no_injection(mock_coordinator):
    """No pending hints → request contents must be left untouched."""
    cb = TrashDigCallback.get_instance(mock_coordinator)
    ctx = MagicMock(spec=CallbackContext)
    req = MagicMock()
    req.contents = []

    await cb.on_before_model(ctx, req)

    assert req.contents == []


async def test_callback_on_after_model_reverts_steering_to_running(mock_coordinator):
    """After a steering hint injection, the next on_after_model call must
    restore RUNNING, mirroring the WAITING_FOR_TOOLS revert."""
    mock_coordinator._state = EngineState.STEERING
    cb = TrashDigCallback.get_instance(mock_coordinator)

    ctx = MagicMock(spec=CallbackContext)
    ctx.agent_name = "test_agent"

    usage = MagicMock()
    usage.prompt_token_count = 10
    usage.candidates_token_count = 5

    resp = MagicMock(spec=LlmResponse)
    resp.content = genai_types.Content(parts=[genai_types.Part(text="Response")])
    resp.usage_metadata = usage

    await cb.on_after_model(ctx, resp)

    assert mock_coordinator._state == EngineState.RUNNING


async def test_callback_on_model_error(mock_coordinator):
    cb = TrashDigCallback.get_instance(mock_coordinator)
    ctx = MagicMock(spec=CallbackContext)
    ctx.agent_name = "test_agent"

    await cb.on_model_error(ctx, MagicMock(), Exception("Test Error"))

    # Check error signaling
    mock_coordinator._on_llm_error.assert_called_once()

def test_callback_on_before_tool(mock_coordinator):
    cb = TrashDigCallback.get_instance(mock_coordinator)
    tool = MagicMock(spec=BaseTool)
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


# ---------------------------------------------------------------------------
# Turn limit tests
# ---------------------------------------------------------------------------

async def test_turn_limit_not_enforced_when_unset(mock_coordinator):
    """No turn limit configured → every call proceeds normally."""
    mock_coordinator.config.get_agent_config.return_value = _make_agent_config(max_turns=None)
    cb = TrashDigCallback.get_instance(mock_coordinator)

    ctx = MagicMock(spec=CallbackContext)
    ctx.agent_name = "hunter"
    req = MagicMock()
    req.contents = []

    for _ in range(50):
        result = await cb.on_before_model(ctx, req)
        assert result is None, "Expected None (no stop) when max_turns is unset"


async def test_turn_limit_allows_up_to_limit(mock_coordinator):
    """Calls up to max_turns are allowed; the (max_turns+1)-th is blocked."""
    mock_coordinator.config.get_agent_config.return_value = _make_agent_config(max_turns=3)
    cb = TrashDigCallback.get_instance(mock_coordinator)

    ctx = MagicMock(spec=CallbackContext)
    ctx.agent_name = "hunter"
    req = MagicMock()
    req.contents = []

    for turn in range(1, 4):
        result = await cb.on_before_model(ctx, req)
        assert result is None, f"Turn {turn} should be allowed (max_turns=3)"

    # 4th call must be blocked
    result = await cb.on_before_model(ctx, req)
    assert isinstance(result, LlmResponse), "Expected LlmResponse stop on turn 4"
    assert result.finish_reason == genai_types.FinishReason.STOP
    assert "3" in result.content.parts[0].text  # limit mentioned in message


async def test_turn_limit_per_agent_independent(mock_coordinator):
    """Turn counters are tracked independently per agent name."""
    def _cfg_for(agent_name):
        return _make_agent_config(max_turns=2)

    mock_coordinator.config.get_agent_config.side_effect = _cfg_for
    cb = TrashDigCallback.get_instance(mock_coordinator)

    req = MagicMock()
    req.contents = []

    ctx_a = MagicMock(spec=CallbackContext)
    ctx_a.agent_name = "hunter"
    ctx_b = MagicMock(spec=CallbackContext)
    ctx_b.agent_name = "skeptic"

    # Both agents: first two calls are fine
    assert await cb.on_before_model(ctx_a, req) is None
    assert await cb.on_before_model(ctx_b, req) is None
    assert await cb.on_before_model(ctx_a, req) is None
    assert await cb.on_before_model(ctx_b, req) is None

    # 3rd call for each is blocked
    result_a = await cb.on_before_model(ctx_a, req)
    result_b = await cb.on_before_model(ctx_b, req)
    assert isinstance(result_a, LlmResponse)
    assert isinstance(result_b, LlmResponse)


async def test_reset_turn_counts_clears_state(mock_coordinator):
    """reset_turn_counts() lets agents run again after being blocked."""
    mock_coordinator.config.get_agent_config.return_value = _make_agent_config(max_turns=1)
    cb = TrashDigCallback.get_instance(mock_coordinator)

    ctx = MagicMock(spec=CallbackContext)
    ctx.agent_name = "hunter"
    req = MagicMock()
    req.contents = []

    assert await cb.on_before_model(ctx, req) is None   # turn 1 — allowed
    blocked = await cb.on_before_model(ctx, req)        # turn 2 — blocked
    assert isinstance(blocked, LlmResponse)

    cb.reset_turn_counts()

    assert await cb.on_before_model(ctx, req) is None   # turn 1 again — allowed


async def test_turn_limit_independent_across_concurrent_invocations(mock_coordinator):
    """Two concurrent runs of the same agent (same name, different invocation_id)
    must not share a turn counter, and resetting one must not clobber the other.

    Regression test for the parallel-hunter race where a shared `agent_name`-keyed
    counter let one `run_hunter` segment's reset wipe another in-flight segment's
    turn count.
    """
    mock_coordinator.config.get_agent_config.return_value = _make_agent_config(max_turns=2)
    cb = TrashDigCallback.get_instance(mock_coordinator)

    req = MagicMock()
    req.contents = []

    ctx_seg1 = MagicMock(spec=CallbackContext)
    ctx_seg1.agent_name = "hunter"
    ctx_seg1.invocation_id = "invocation-segment-1"

    ctx_seg2 = MagicMock(spec=CallbackContext)
    ctx_seg2.agent_name = "hunter"
    ctx_seg2.invocation_id = "invocation-segment-2"

    # Segment 1 runs up to its limit.
    assert await cb.on_before_model(ctx_seg1, req) is None
    assert await cb.on_before_model(ctx_seg1, req) is None

    # Segment 2 starts concurrently (e.g. a fresh run_hunter call for another
    # parallel segment) and must start from turn 1, not inherit segment 1's count.
    assert await cb.on_before_model(ctx_seg2, req) is None

    # Segment 1 is now at its limit and must be blocked, unaffected by segment 2.
    blocked = await cb.on_before_model(ctx_seg1, req)
    assert isinstance(blocked, LlmResponse)

    # Segment 2 still has one turn left.
    assert await cb.on_before_model(ctx_seg2, req) is None
