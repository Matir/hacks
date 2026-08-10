"""ADK-native callback handlers for TrashDig.

Bridges ADK's before_tool_callback / after_model_callback / on_model_error_callback
hooks to TrashDig's TUI logging, token accounting, cost tracking, and DB persistence.
This replaces the manual on_event/on_stats/on_error/conversation_log_fn parameters
that were previously threaded through every agent wrapper method.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types

from trashdig.agents.utils.types import EngineState
from trashdig.services.rate_limiter import get_rate_limiter

# Standard library and 3rd party imports are at the top.
# The following imports are for type hinting only and avoid circular dependencies.
if TYPE_CHECKING:
    from trashdig.agents.coordinator import Coordinator

logger = logging.getLogger(__name__)


class TrashDigCallback:
    """Single callback object wired to every agent in a scan session.

    Receives ADK hook calls and routes them to the Coordinator's TUI event
    system, token/cost tracking, and ProjectDatabase conversation log.

    This class implements a singleton pattern to ensure all agents in a
    session share the same accounting and logging logic.
    """

    _instance: TrashDigCallback | None = None

    def __init__(self, coordinator: Coordinator) -> None:
        """Initialise the callback manager.

        Note: Use get_instance() instead of direct instantiation in most cases.
        """
        self._c = coordinator
        self._last_prompt: str = ""
        # Keyed by (invocation_id, agent_name) rather than agent_name alone so
        # that concurrent runner.run_async() invocations (e.g. parallel hunter
        # segments sharing the "hunter" agent name) never share a counter.
        self._turn_counts: dict[tuple[str, str], int] = {}

    @classmethod
    def get_instance(cls, coordinator: Coordinator | None = None) -> TrashDigCallback:
        """Return the singleton instance, creating it if needed.

        Args:
            coordinator: The Coordinator instance to link.

        Returns:
            The singleton TrashDigCallback instance.
        """
        if cls._instance is None:
            if coordinator is None:
                raise ValueError("TrashDigCallback.get_instance() requires a coordinator on first call")
            cls._instance = cls(coordinator)
        elif coordinator is not None:
            # Allow updating the coordinator reference (useful for tests or resumption)
            cls._instance._c = coordinator
        return cls._instance

    @classmethod
    def _reset(cls) -> None:
        """Reset the singleton instance (for testing)."""
        cls._instance = None

    def reset_turn_counts(self) -> None:
        """Clear all turn counters.

        Counters are already scoped per-invocation (see `_turn_counts`), so
        this is just housekeeping to bound memory growth across a long-lived
        process; call it only from a single top-level, non-concurrent entry
        point (e.g. the start of a full scan), never from code paths that may
        run concurrently with other in-flight invocations.
        """
        self._turn_counts.clear()

    def attach_to(self, agent: Any) -> None:
        """Attach this callback manager to an ADK agent.

        Wires up the tool, model, and error hooks if the agent supports them.

        Args:
            agent: The ADK agent (LlmAgent, BaseAgent, etc.) to monitor.
        """
        # Wire agent-level callbacks (supported by BaseAgent)
        agent.before_agent_callback = self.on_before_agent
        agent.after_agent_callback = self.on_after_agent

        # Only LlmAgent supports these specific model/tool callbacks in its schema
        if isinstance(agent, LlmAgent):
            agent.before_tool_callback = self.on_before_tool
            agent.before_model_callback = self.on_before_model
            agent.after_model_callback = self.on_after_model
            agent.on_model_error_callback = self.on_model_error

    # ------------------------------------------------------------------
    # Agent lifecycle hooks
    # ------------------------------------------------------------------

    def on_before_agent(self, **kwargs: Any) -> None:
        """Update state to RUNNING when an agent starts."""
        self._c._state = EngineState.RUNNING
        if self._c.on_stats_event:
            self._c.on_stats_event()

    def on_after_agent(self, **kwargs: Any) -> None:
        """Update state to IDLE when an agent finishes."""
        self._c._state = EngineState.IDLE
        if self._c.on_stats_event:
            self._c.on_stats_event()

    # ------------------------------------------------------------------
    # Tool hook
    # ------------------------------------------------------------------

    def on_before_tool(
        self, tool: BaseTool, args: dict[str, Any], tool_context: ToolContext, **kwargs: Any
    ) -> dict | None:
        """Log tool invocations and update state to WAITING_FOR_TOOLS."""
        self._c._state = EngineState.WAITING_FOR_TOOLS
        if self._c.on_stats_event:
            self._c.on_stats_event()

        args_str = ", ".join(f"{k}={repr(v)[:60]}" for k, v in args.items())
        self._c.log(f"  [dim]→ {tool.name}({args_str})[/dim]")
        return None  # Never skip the actual tool call

    # ------------------------------------------------------------------
    # Model hooks
    # ------------------------------------------------------------------

    async def on_before_model(
        self, callback_context: CallbackContext, llm_request: LlmRequest, **kwargs: Any
    ) -> LlmResponse | None:
        """Block while paused, inject steering hints, enforce turn limits, capture prompt, and wait for rate-limit slot."""
        await self._c.check_pause()

        agent_name = getattr(callback_context, "agent_name", None) or "unknown"
        invocation_id = getattr(callback_context, "invocation_id", None) or "unknown"
        turn_key = (invocation_id, agent_name)
        self._turn_counts[turn_key] = self._turn_counts.get(turn_key, 0) + 1
        current = self._turn_counts[turn_key]

        max_turns = self._c.config.get_agent_config(agent_name).max_turns
        if max_turns is not None and current > max_turns:
            self._c.log(
                f"[bold red]Turn limit:[/bold red] {agent_name} reached "
                f"max_turns={max_turns} (turn {current}). Stopping."
            )
            logger.warning(
                "Agent %s exceeded max_turns=%d (turn %d); returning stop response.",
                agent_name, max_turns, current,
            )
            return LlmResponse(
                content=types.Content(
                    role="model",
                    parts=[types.Part(text=(
                        f"Turn limit of {max_turns} reached. "
                        "Stopping and returning control to the coordinator."
                    ))],
                ),
                finish_reason=types.FinishReason.STOP,
            )

        hints = self._c.pop_pending_hints()
        if hints:
            self._c._state = EngineState.STEERING
            hint_text = "\n".join(f"- {h}" for h in hints)
            self._c.log(f"[bold cyan]Steering:[/bold cyan] injecting hint into {agent_name}")
            llm_request.contents.append(
                types.Content(
                    role="user",
                    parts=[types.Part(text=(
                        "[HUMAN STEERING HINT — high priority, adjust course now]\n"
                        f"{hint_text}"
                    ))],
                )
            )

        limiter = get_rate_limiter()
        if limiter:
            await limiter.wait_for_request()

        prompt = ""
        if llm_request.contents:
            for content in llm_request.contents:
                if content.parts:
                    for part in content.parts:
                        if hasattr(part, "text") and part.text:
                            prompt += part.text + "\n"
        self._last_prompt = prompt.strip()

        self._c.log(f"[dim]→ LLM request ({agent_name})[/dim]")
        return None

    async def on_after_model(
        self, callback_context: CallbackContext, llm_response: LlmResponse, **kwargs: Any
    ) -> LlmResponse | None:
        """Record usage, cost, log conversation, and update rate limiter usage."""
        # Restore RUNNING state after tool call finishes and model resumes,
        # or after a steering hint has been injected into the request.
        if self._c._state in (EngineState.WAITING_FOR_TOOLS, EngineState.STEERING):
            self._c._state = EngineState.RUNNING

        ctx = callback_context
        resp = llm_response
        if not ctx or not resp:
            return None

        # In streaming mode, this callback fires once per partial chunk plus
        # a final non-partial chunk with the fully-assembled response and
        # usage metadata. Skip partials so accounting and logging happen
        # exactly once, on the complete response.
        if resp.partial:
            return None

        usage = resp.usage_metadata
        in_t = (getattr(usage, "prompt_token_count", None) or 0) if usage else 0
        out_t = (getattr(usage, "candidates_token_count", None) or 0) if usage else 0

        # Update rate limiter if present
        limiter = get_rate_limiter()
        if limiter:
            total_t = (getattr(usage, "total_token_count", None) or (in_t + out_t))
            await limiter.update_usage(total_t)

        agent_name = getattr(ctx, "agent_name", "unknown")
        agent = self._c._agent_by_name(agent_name)
        model_name = getattr(agent, "model", None) or "unknown"

        # Final accounting
        self._c._cost_tracker.record_usage(model_name, in_t, out_t)

        # Signaling hook for the TUI
        self._c._on_stats(in_t, out_t, new_msg=True, model_name=model_name)

        # Extract response text and tool calls for the DB log
        response_text = ""
        tool_calls: list[dict] = []
        if resp.content and resp.content.parts:
            for part in resp.content.parts:
                if hasattr(part, "text") and part.text:
                    response_text = part.text
                fc = getattr(part, "function_call", None)
                if fc and getattr(fc, "name", None):
                    tool_calls.append({
                        "name": fc.name,
                        "args": dict(getattr(fc, "args", None) or {}),
                    })

        self._c.db.log_conversation(
            self._c.project_path,
            agent_name,
            self._last_prompt,
            response_text,
            tool_calls,
            in_t,
            out_t,
        )

        # Full turn (prompt + response) goes to the logfile only — the TUI
        # log window only gets the compact "request" notice from on_before_model.
        logger.info(
            "LLM turn — agent=%s\n----- PROMPT -----\n%s\n----- RESPONSE -----\n%s",
            agent_name,
            self._last_prompt,
            response_text,
        )
        return None  # Never replace the model response

    async def on_model_error(
        self, callback_context: CallbackContext, llm_request: LlmRequest, error: Exception, **kwargs: Any
    ) -> LlmResponse | None:
        """Increment the LLM error counter on model API failures."""
        agent_name = getattr(callback_context, "agent_name", "unknown")
        logger.warning("Model error in agent %s: %s", agent_name, error)
        self._c._on_llm_error()
        return None  # Let the error propagate
