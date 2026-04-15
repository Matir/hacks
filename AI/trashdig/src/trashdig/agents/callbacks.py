"""ADK-native callback handlers for TrashDig.

Bridges ADK's before_tool_callback / after_model_callback / on_model_error_callback
hooks to TrashDig's TUI logging, token accounting, cost tracking, and DB persistence.
This replaces the manual on_event/on_stats/on_error/conversation_log_fn parameters
that were previously threaded through every agent wrapper method.
"""
from __future__ import annotations

import logging
from typing import Any, Optional, TYPE_CHECKING

from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext

if TYPE_CHECKING:
    from trashdig.agents.coordinator import Coordinator

logger = logging.getLogger(__name__)


class TrashDigCallback:
    """Single callback object wired to every agent in a scan session.

    Receives ADK hook calls and routes them to the Coordinator's TUI event
    system, token/cost tracking, and ProjectDatabase conversation log.

    Usage::

        cb = TrashDigCallback(coordinator)
        for agent in (stack_scout, hunter, ...):
            agent.before_tool_callback = cb.on_before_tool
            agent.after_model_callback = cb.on_after_model
            agent.on_model_error_callback = cb.on_model_error
    """

    def __init__(self, coordinator: "Coordinator") -> None:
        self._c = coordinator

    # ------------------------------------------------------------------
    # Tool hook
    # ------------------------------------------------------------------

    def on_before_tool(
        self, tool: BaseTool, args: dict[str, Any], ctx: ToolContext
    ) -> Optional[dict]:
        """Log tool invocations to the TUI before execution."""
        args_str = ", ".join(f"{k}={repr(v)[:60]}" for k, v in args.items())
        self._c.log(f"  [dim]→ {tool.name}({args_str})[/dim]")
        return None  # Never skip the actual tool call

    # ------------------------------------------------------------------
    # Model hooks
    # ------------------------------------------------------------------

    def on_after_model(
        self, ctx: CallbackContext, resp: LlmResponse
    ) -> Optional[LlmResponse]:
        """Record token usage, cost, and conversation log after each model turn."""
        usage = resp.usage_metadata
        in_t = (getattr(usage, "prompt_token_count", None) or 0) if usage else 0
        out_t = (getattr(usage, "candidates_token_count", None) or 0) if usage else 0

        agent_name = ctx.agent_name
        model_name = getattr(self._c._agent_by_name(agent_name), "model", None)

        # Final accounting: cumulative totals + cost tracker
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
            "",  # prompt not available in after_model_callback; logged upstream
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
        logger.warning("Model error in agent %s: %s", ctx.agent_name, err)
        self._c._on_llm_error()
        return None  # Let the error propagate to Engine's retry logic
