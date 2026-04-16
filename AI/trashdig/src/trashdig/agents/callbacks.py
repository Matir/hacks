"""ADK-native callback handlers for TrashDig.

Bridges ADK's before_tool_callback / after_model_callback / on_model_error_callback
hooks to TrashDig's TUI logging, token accounting, cost tracking, and DB persistence.
This replaces the manual on_event/on_stats/on_error/conversation_log_fn parameters
that were previously threaded through every agent wrapper method.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Optional

from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext

from trashdig.agents.types import EngineState

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

    _instance: Optional[TrashDigCallback] = None

    def __init__(self, coordinator: "Coordinator") -> None:
        """Initialise the callback manager.
        
        Note: Use get_instance() instead of direct instantiation in most cases.
        """
        self._c = coordinator
        self._last_prompt: str = ""

    @classmethod
    def get_instance(cls, coordinator: Optional["Coordinator"] = None) -> TrashDigCallback:
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
        self, tool: BaseTool, args: dict[str, Any], ctx: ToolContext, **kwargs: Any
    ) -> Optional[dict]:
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

    def on_before_model(self, ctx: CallbackContext, req: LlmRequest, **kwargs: Any) -> Optional[LlmResponse]:
        """Capture the prompt before it is sent to the model."""
        prompt = ""
        if req.contents:
            for content in req.contents:
                if content.parts:
                    for part in content.parts:
                        if hasattr(part, "text") and part.text:
                            prompt += part.text + "\n"
        self._last_prompt = prompt.strip()
        return None

    def on_after_model(
        self, ctx: Optional[CallbackContext] = None, resp: Optional[LlmResponse] = None, **kwargs: Any
    ) -> Optional[LlmResponse]:
        """Record token usage, cost, log conversation, and trigger compaction."""
        # Restore RUNNING state after tool call finishes and model resumes
        if self._c._state == EngineState.WAITING_FOR_TOOLS:
            self._c._state = EngineState.RUNNING

        # Handle kwargs if passed by name (ADK sometimes does this)
        if ctx is None:
            ctx = kwargs.get("callback_context") or kwargs.get("ctx")
        if resp is None:
            resp = kwargs.get("response") or kwargs.get("resp")

        if not ctx or not resp:
            return None

        usage = resp.usage_metadata
        in_t = (getattr(usage, "prompt_token_count", None) or 0) if usage else 0
        out_t = (getattr(usage, "candidates_token_count", None) or 0) if usage else 0

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
        return None  # Never replace the model response

    def on_model_error(
        self, ctx: CallbackContext, req: LlmRequest, err: Exception
    ) -> Optional[LlmResponse]:
        """Increment the LLM error counter on model API failures."""
        agent_name = getattr(ctx, "agent_name", "unknown")
        logger.warning("Model error in agent %s: %s", agent_name, err)
        self._c._on_llm_error()
        return None  # Let the error propagate
