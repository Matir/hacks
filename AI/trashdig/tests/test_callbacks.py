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
    mock_coordinator._active_agents = 0
    cb = TrashDigCallback.get_instance(mock_coordinator)
    ctx = MagicMock(spec=CallbackContext)
    req = MagicMock()
    req.contents = [genai_types.Content(parts=[genai_types.Part(text="Test Prompt")])]

    await cb.on_before_model(ctx, req)
    assert cb._last_prompt == "Test Prompt"


async def test_callback_on_before_model_captures_only_latest_turn(mock_coordinator):
    """llm_request.contents carries the full running history on every call.
    Only the newest entry — this turn's actual new input — must be captured,
    not the whole transcript (which would always start with turn 1's prompt).
    """
    mock_coordinator._active_agents = 0
    cb = TrashDigCallback.get_instance(mock_coordinator)
    ctx = MagicMock(spec=CallbackContext)

    req = MagicMock()
    req.contents = [genai_types.Content(parts=[genai_types.Part(text="First turn prompt")])]
    await cb.on_before_model(ctx, req)
    assert cb._last_prompt == "First turn prompt"

    # Turn 2: history now includes turn 1's exchange plus a tool result with
    # no text part, followed by the new user-visible text for this turn.
    req.contents = [
        genai_types.Content(role="user", parts=[genai_types.Part(text="First turn prompt")]),
        genai_types.Content(role="model", parts=[genai_types.Part(text="First turn response")]),
        genai_types.Content(role="user", parts=[genai_types.Part(text="Second turn prompt")]),
    ]
    await cb.on_before_model(ctx, req)
    assert cb._last_prompt == "Second turn prompt"


async def test_callback_on_before_model_awaits_pause(mock_coordinator):
    """Every model call must check the pause gate before proceeding, not just
    the coarse per-phase checkpoints in Coordinator — this is the fix for
    "Pause & Steer" taking effect mid-turn instead of only between phases.
    """
    mock_coordinator._active_agents = 0
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
    mock_coordinator._active_agents = 0
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
    resp.partial = False

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


async def test_callback_on_after_model_skips_partial_chunks(mock_coordinator):
    """Streaming chunks (partial=True) must not be logged or accounted for;
    only the final, fully-assembled response should be recorded."""
    mock_coordinator._active_agents = 0
    cb = TrashDigCallback.get_instance(mock_coordinator)

    ctx = MagicMock(spec=CallbackContext)
    ctx.agent_name = "test_agent"

    resp = MagicMock(spec=LlmResponse)
    resp.content = genai_types.Content(parts=[genai_types.Part(text="Resp")])
    resp.partial = True

    await cb.on_after_model(ctx, resp)

    mock_coordinator._cost_tracker.record_usage.assert_not_called()
    mock_coordinator._on_stats.assert_not_called()
    mock_coordinator.db.log_conversation.assert_not_called()


async def test_callback_on_after_model_skips_empty_trailing_echo(mock_coordinator):
    """ADK's Gemini streaming aggregator can yield a trailing event with
    partial=False, finish_reason set, and empty content — its text was
    already flushed into an earlier event. This echo must not overwrite the
    real logged response with a blank one, nor double-count usage."""
    mock_coordinator._active_agents = 0
    cb = TrashDigCallback.get_instance(mock_coordinator)

    ctx = MagicMock(spec=CallbackContext)
    ctx.agent_name = "test_agent"

    resp = MagicMock(spec=LlmResponse)
    resp.content = None
    resp.partial = False
    usage = MagicMock()
    usage.prompt_token_count = 10
    usage.candidates_token_count = 5
    resp.usage_metadata = usage

    await cb.on_after_model(ctx, resp)

    mock_coordinator._cost_tracker.record_usage.assert_not_called()
    mock_coordinator._on_stats.assert_not_called()
    mock_coordinator.db.log_conversation.assert_not_called()


async def test_callback_on_after_model_logs_content_with_unset_partial(mock_coordinator):
    """The real assembled-text event from the streaming aggregator leaves
    `partial` unset (None) rather than explicitly False; it must still be
    logged and accounted for."""
    mock_coordinator._active_agents = 0
    cb = TrashDigCallback.get_instance(mock_coordinator)

    ctx = MagicMock(spec=CallbackContext)
    ctx.agent_name = "test_agent"

    resp = MagicMock(spec=LlmResponse)
    resp.content = genai_types.Content(parts=[genai_types.Part(text="Full response")])
    resp.partial = None
    usage = MagicMock()
    usage.prompt_token_count = 10
    usage.candidates_token_count = 5
    resp.usage_metadata = usage

    await cb.on_after_model(ctx, resp)

    mock_coordinator._cost_tracker.record_usage.assert_called_once()
    mock_coordinator.db.log_conversation.assert_called_once()
    call_args = mock_coordinator.db.log_conversation.call_args[0]
    assert "Full response" in call_args


async def test_callback_on_after_model_detects_safety_refusal(mock_coordinator):
    """A response blocked mid-generation (finish_reason=SAFETY, no content)
    must be logged, recorded with a [REFUSED: ...] marker, and must stop
    the agent by setting escalate — the same signal exit_loop uses."""
    mock_coordinator._active_agents = 0
    cb = TrashDigCallback.get_instance(mock_coordinator)

    ctx = MagicMock(spec=CallbackContext)
    ctx.agent_name = "hunter"
    ctx.actions = MagicMock()

    usage = MagicMock()
    usage.prompt_token_count = 20
    usage.candidates_token_count = 0

    resp = MagicMock(spec=LlmResponse)
    resp.content = None
    resp.partial = False
    resp.finish_reason = genai_types.FinishReason.SAFETY
    resp.error_code = None
    resp.usage_metadata = usage

    await cb.on_after_model(ctx, resp)

    assert ctx.actions.escalate is True
    mock_coordinator.log.assert_called_once()
    assert "hunter" in mock_coordinator.log.call_args[0][0]

    # Token accounting still happens — the refused call still cost tokens.
    mock_coordinator._cost_tracker.record_usage.assert_called_once()

    mock_coordinator.db.log_conversation.assert_called_once()
    call_args = mock_coordinator.db.log_conversation.call_args[0]
    assert "[REFUSED: SAFETY]" in call_args[3]


async def test_callback_on_after_model_detects_prompt_blocked_via_error_code(mock_coordinator):
    """A prompt blocked before generation started carries no finish_reason —
    ADK's LlmResponse.create() reports it via error_code instead — and must
    still be detected as a refusal."""
    mock_coordinator._active_agents = 0
    cb = TrashDigCallback.get_instance(mock_coordinator)

    ctx = MagicMock(spec=CallbackContext)
    ctx.agent_name = "skeptic"
    ctx.actions = MagicMock()

    resp = MagicMock(spec=LlmResponse)
    resp.content = None
    resp.partial = False
    resp.finish_reason = None
    resp.error_code = genai_types.BlockedReason.PROHIBITED_CONTENT
    resp.usage_metadata = None

    await cb.on_after_model(ctx, resp)

    assert ctx.actions.escalate is True
    mock_coordinator.db.log_conversation.assert_called_once()
    call_args = mock_coordinator.db.log_conversation.call_args[0]
    assert "[REFUSED: PROHIBITED_CONTENT]" in call_args[3]


async def test_callback_on_after_model_max_tokens_is_not_a_refusal(mock_coordinator):
    """finish_reason=MAX_TOKENS also accompanies empty content but is not a
    refusal — it must fall through to the existing empty-echo skip, not
    trigger refusal logging or escalate."""
    mock_coordinator._active_agents = 0
    cb = TrashDigCallback.get_instance(mock_coordinator)

    ctx = MagicMock(spec=CallbackContext)
    ctx.agent_name = "hunter"
    ctx.actions = MagicMock()

    resp = MagicMock(spec=LlmResponse)
    resp.content = None
    resp.partial = False
    resp.finish_reason = genai_types.FinishReason.MAX_TOKENS
    resp.error_code = genai_types.FinishReason.MAX_TOKENS
    resp.usage_metadata = None

    await cb.on_after_model(ctx, resp)

    assert ctx.actions.escalate is not True
    mock_coordinator._cost_tracker.record_usage.assert_not_called()
    mock_coordinator.db.log_conversation.assert_not_called()


async def test_callback_on_before_model_injects_pending_hint(mock_coordinator):
    """A queued hint must be appended to the request as a high-priority
    user message, and the state must flip to STEERING while it's injected.
    """
    mock_coordinator.pop_pending_hints.return_value = ["Focus on the SQL sink in db.py"]
    mock_coordinator._active_agents = 0
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
    mock_coordinator._active_agents = 0
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
    mock_coordinator._active_agents = 0
    cb = TrashDigCallback.get_instance(mock_coordinator)

    ctx = MagicMock(spec=CallbackContext)
    ctx.agent_name = "test_agent"

    usage = MagicMock()
    usage.prompt_token_count = 10
    usage.candidates_token_count = 5

    resp = MagicMock(spec=LlmResponse)
    resp.content = genai_types.Content(parts=[genai_types.Part(text="Response")])
    resp.usage_metadata = usage
    resp.partial = False

    await cb.on_after_model(ctx, resp)

    assert mock_coordinator._state == EngineState.RUNNING


async def test_callback_on_model_error(mock_coordinator):
    mock_coordinator._active_agents = 0
    cb = TrashDigCallback.get_instance(mock_coordinator)
    ctx = MagicMock(spec=CallbackContext)
    ctx.agent_name = "test_agent"

    await cb.on_model_error(ctx, MagicMock(), Exception("Test Error"))

    # Check error signaling
    mock_coordinator._on_llm_error.assert_called_once()

def test_callback_on_before_tool(mock_coordinator):
    mock_coordinator._active_agents = 0
    cb = TrashDigCallback.get_instance(mock_coordinator)
    tool = MagicMock(spec=BaseTool)
    tool.name = "test_tool"

    cb.on_before_tool(tool, {"arg1": "val1"}, MagicMock())

    # Check state update
    assert mock_coordinator._state == EngineState.WAITING_FOR_TOOLS

    # Check logging to TUI
    mock_coordinator.log.assert_called_once()
    assert "test_tool" in mock_coordinator.log.call_args[0][0]


def test_callback_on_after_tool_logs_success(mock_coordinator):
    """A successful tool response is logged plainly, not flagged as a failure."""
    mock_coordinator._active_agents = 0
    cb = TrashDigCallback.get_instance(mock_coordinator)
    tool = MagicMock(spec=BaseTool)
    tool.name = "read_file"
    tool_context = MagicMock()
    tool_context.agent_name = "hunter"

    cb.on_after_tool(tool, {"file_path": "foo.py"}, tool_context, "def foo(): pass")

    mock_coordinator.log.assert_called_once()
    logged = mock_coordinator.log.call_args[0][0]
    assert "read_file" in logged
    assert "bold red" not in logged


def test_callback_on_after_tool_flags_string_error_convention(mock_coordinator):
    """Trashdig tools (read_file, bash_tool, web_fetch, ...) signal failure by
    returning a string starting with "Error" rather than raising — this must
    be flagged in the console, distinctly from a normal response."""
    mock_coordinator._active_agents = 0
    cb = TrashDigCallback.get_instance(mock_coordinator)
    tool = MagicMock(spec=BaseTool)
    tool.name = "read_file"
    tool_context = MagicMock()
    tool_context.agent_name = "hunter"

    cb.on_after_tool(tool, {"file_path": "missing.py"}, tool_context, "Error reading file missing.py: not found")

    mock_coordinator.log.assert_called_once()
    logged = mock_coordinator.log.call_args[0][0]
    assert "bold red" in logged
    assert "read_file" in logged


def test_callback_on_after_tool_flags_error_dict_convention(mock_coordinator):
    """ADK's own FunctionTool reports failures like missing args as
    {"error": ...} rather than a string — this must also be flagged."""
    mock_coordinator._active_agents = 0
    cb = TrashDigCallback.get_instance(mock_coordinator)
    tool = MagicMock(spec=BaseTool)
    tool.name = "some_tool"
    tool_context = MagicMock()
    tool_context.agent_name = "hunter"

    cb.on_after_tool(tool, {}, tool_context, {"error": "missing mandatory parameter"})

    mock_coordinator.log.assert_called_once()
    logged = mock_coordinator.log.call_args[0][0]
    assert "bold red" in logged


def test_callback_on_tool_error_logs_and_does_not_swallow(mock_coordinator):
    """A raised tool exception must be flagged in the console, and the
    callback must return None so ADK re-raises rather than silently
    continuing with a fabricated response."""
    mock_coordinator._active_agents = 0
    cb = TrashDigCallback.get_instance(mock_coordinator)
    tool = MagicMock(spec=BaseTool)
    tool.name = "container_bash_tool"
    tool_context = MagicMock()
    tool_context.agent_name = "hunter"

    result = cb.on_tool_error(tool, {"command": "ls"}, tool_context, RuntimeError("docker daemon unreachable"))

    assert result is None
    mock_coordinator.log.assert_called_once()
    logged = mock_coordinator.log.call_args[0][0]
    assert "bold red" in logged
    assert "container_bash_tool" in logged
    assert "docker daemon unreachable" in logged


def test_callback_attach_to(mock_coordinator):
    mock_coordinator._active_agents = 0
    cb = TrashDigCallback.get_instance(mock_coordinator)
    # Use a mock that spec-es LlmAgent so isinstance works
    agent = MagicMock(spec=LlmAgent)

    cb.attach_to(agent)

    assert agent.before_tool_callback == cb.on_before_tool
    assert agent.after_tool_callback == cb.on_after_tool
    assert agent.on_tool_error_callback == cb.on_tool_error
    assert agent.after_model_callback == cb.on_after_model
    assert agent.on_model_error_callback == cb.on_model_error
    assert agent.before_agent_callback == cb.on_before_agent
    assert agent.after_agent_callback == cb.on_after_agent

def test_callback_agent_lifecycle(mock_coordinator):
    mock_coordinator._active_agents = 0
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
    mock_coordinator._active_agents = 0
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
    mock_coordinator._active_agents = 0
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
    mock_coordinator._active_agents = 0
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
    mock_coordinator._active_agents = 0
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
    mock_coordinator._active_agents = 0
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
