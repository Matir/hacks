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

from trashdig.agents.utils.json_utils import BLOCKED_REASONS
from trashdig.agents.utils.types import EngineState
from trashdig.services.rate_limiter import get_rate_limiter

# Standard library and 3rd party imports are at the top.
# The following imports are for type hinting only and avoid circular dependencies.
if TYPE_CHECKING:
    from trashdig.agents.coordinator import Coordinator

logger = logging.getLogger(__name__)


def _extract_response(resp: LlmResponse) -> tuple[str, list[dict]]:
    """Pull the text and tool calls out of an LlmResponse's content parts."""
    response_text = ""
    tool_calls: list[dict] = []
    if resp.content and resp.content.parts:
        for part in resp.content.parts:
            if hasattr(part, "text") and part.text:
                response_text = part.text
            fc = getattr(part, "function_call", None)
            if fc and getattr(fc, "name", None):
                tool_calls.append(
                    {
                        "name": fc.name,
                        "args": dict(getattr(fc, "args", None) or {}),
                    }
                )
    return response_text, tool_calls


def _is_tool_error(tool_response: Any) -> bool:
    """Best-effort detection of a tool-reported failure.

    Trashdig's own tools (bash_tool, read_file, web_fetch, semgrep_scan, ...)
    signal failure by returning a plain string starting with "Error" rather
    than raising; ADK's own FunctionTool falls back to {"error": ...} for
    things like missing required arguments. Check both conventions.
    """
    if isinstance(tool_response, dict):
        return "error" in tool_response
    if isinstance(tool_response, str):
        return tool_response.startswith("Error")
    return False


def _refusal_reason(resp: LlmResponse) -> str | None:
    """Return the refusal reason if `resp` was safety/policy-blocked, else None.

    ADK's LlmResponse.create() (google.adk.models.llm_response) sets
    `finish_reason` when the model started generating and was cut off (e.g.
    mid-stream), and sets `error_code` instead when Gemini blocked the prompt
    before generating any candidate at all — so both must be checked.
    """
    for reason in (getattr(resp, "finish_reason", None), getattr(resp, "error_code", None)):
        if reason is not None and reason in BLOCKED_REASONS:
            return getattr(reason, "value", reason)
    return None


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
                raise ValueError(
                    "TrashDigCallback.get_instance() requires a coordinator on first call"
                )
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
            agent.after_tool_callback = self.on_after_tool
            agent.on_tool_error_callback = self.on_tool_error
            agent.before_model_callback = self.on_before_model
            agent.after_model_callback = self.on_after_model
            agent.on_model_error_callback = self.on_model_error

    def _handle_refusal(
        self, ctx: CallbackContext, agent_name: str, refusal_reason: str, response_text: str
    ) -> None:
        """Log a detected model refusal/safety-block and stop the agent."""
        self._c.log(
            f"[bold red]Refused:[/bold red] {agent_name} — model blocked "
            f"the response ({refusal_reason}). Stopping this agent."
        )
        logger.warning(
            "Model refusal in agent %s: reason=%s response=%r",
            agent_name,
            refusal_reason,
            response_text,
        )
        # Stop the agent that received the refusal. `escalate` is the same
        # ADK signal the exit_loop tool uses (tool_context.actions.escalate)
        # — it immediately breaks any enclosing LoopAgent (e.g. hunter_loop)
        # instead of retrying against the next target. For a single-shot
        # agent there's nothing further to break: a refusal event carries no
        # function_calls, so the agent's own model-call loop already ends
        # after this turn.
        ctx.actions.escalate = True

    # ------------------------------------------------------------------
    # Agent lifecycle hooks
    # ------------------------------------------------------------------

    def on_before_agent(self, **kwargs: Any) -> None:
        """Update state to RUNNING when an agent starts and log it."""
        self._c._state = EngineState.RUNNING
        self._c._active_agents += 1
        if self._c.on_stats_event:
            self._c.on_stats_event()

        ctx = kwargs.get("callback_context") or kwargs.get("context")
        agent_name = getattr(ctx, "agent_name", "unknown") if ctx else "unknown"
        self._c.log(f"[bold]System:[/bold] Agent [cyan]{agent_name}[/cyan] is starting...")

    def on_after_agent(self, **kwargs: Any) -> None:
        """Update state to IDLE when an agent finishes and log it."""
        self._c._state = EngineState.IDLE
        self._c._active_agents = max(0, self._c._active_agents - 1)
        if self._c.on_stats_event:
            self._c.on_stats_event()

        ctx = kwargs.get("callback_context") or kwargs.get("context")
        agent_name = getattr(ctx, "agent_name", "unknown") if ctx else "unknown"
        self._c.log(f"[bold]System:[/bold] Agent [cyan]{agent_name}[/cyan] finished.")

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

        agent_name = getattr(tool_context, "agent_name", "unknown")

        def _format_arg(k: str, v: Any) -> str:
            if k in (
                "file_path",
                "path",
                "directory",
                "target",
                "filename",
                "project_path",
                "db_path",
            ) and isinstance(v, str):
                return repr(v)
            r = repr(v)
            max_len = 60
            return r if len(r) <= max_len else r[: max_len - 3] + "..."

        args_str = ", ".join(f"{k}={_format_arg(k, v)}" for k, v in args.items())

        self._c.log(f"  [dim]→ {tool.name}({args_str})[/dim]")
        logger.info("Tool call — agent=%s tool=%s args=%r", agent_name, tool.name, args)
        return None  # Never skip the actual tool call

    def on_after_tool(
        self,
        tool: BaseTool,
        args: dict[str, Any],
        tool_context: ToolContext,
        tool_response: Any,
        **kwargs: Any,
    ) -> dict | None:
        """Log a tool's response, flagging a tool-reported failure in the console."""
        agent_name = getattr(tool_context, "agent_name", "unknown")
        preview = repr(tool_response)[:200]

        if _is_tool_error(tool_response):
            self._c.log(f"  [bold red]✗ {tool.name} failed:[/bold red] {preview}")
            logger.warning(
                "Tool failed — agent=%s tool=%s response=%r", agent_name, tool.name, tool_response
            )
        else:
            self._c.log(f"  [dim]← {tool.name} → {preview}[/dim]")
            logger.info(
                "Tool response — agent=%s tool=%s response=%r", agent_name, tool.name, tool_response
            )
        return None  # Never override the actual tool response

    def on_tool_error(
        self,
        tool: BaseTool,
        args: dict[str, Any],
        tool_context: ToolContext,
        error: Exception,
        **kwargs: Any,
    ) -> dict | None:
        """Indicate a raised (not just tool-reported) tool failure in the console."""
        agent_name = getattr(tool_context, "agent_name", "unknown")
        self._c.log(f"  [bold red]✗ {tool.name} raised:[/bold red] {error}")
        logger.warning(
            "Tool raised — agent=%s tool=%s args=%r error=%s",
            agent_name,
            tool.name,
            args,
            error,
            exc_info=error,
        )
        return None  # Don't swallow the error — let it propagate as before.

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
                agent_name,
                max_turns,
                current,
            )
            return LlmResponse(
                content=types.Content(
                    role="model",
                    parts=[
                        types.Part(
                            text=(
                                f"Turn limit of {max_turns} reached. "
                                "Stopping and returning control to the coordinator."
                            )
                        )
                    ],
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
                    parts=[
                        types.Part(
                            text=(
                                "[HUMAN STEERING HINT — high priority, adjust course now]\n"
                                f"{hint_text}"
                            )
                        )
                    ],
                )
            )

        limiter = get_rate_limiter()
        if limiter:
            await limiter.wait_for_request()

        # llm_request.contents holds the *entire* running conversation ADK
        # resends on every call, not just this turn's input — concatenating
        # all of it here would make every logged "prompt" start with (and be
        # dominated by) the very first turn's message, especially once later
        # turns add only a function_response (tool result), which has no
        # `.text` part. Only the newest entry — the actual new input for
        # this turn — belongs in the per-turn log.
        prompt = ""
        if llm_request.contents:
            last_content = llm_request.contents[-1]
            if last_content.parts:
                for part in last_content.parts:
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

        # In streaming mode, this callback fires once per partial chunk. Skip
        # those so accounting and logging happen only on complete responses.
        if resp.partial:
            return None

        agent_name = getattr(ctx, "agent_name", "unknown")

        # Extract response text and tool calls for the DB log
        response_text, tool_calls = _extract_response(resp)

        refusal_reason = _refusal_reason(resp)
        if refusal_reason:
            self._handle_refusal(ctx, agent_name, refusal_reason, response_text)
        elif not response_text and not tool_calls:
            # Gemini's streaming aggregator can yield a trailing "echo" event
            # after the real content (partial=False, finish_reason set) that
            # carries only usage/finish metadata with empty content — its text
            # was already flushed into an earlier event whose `partial` is left
            # unset rather than explicitly False. Skip these empty echoes so we
            # don't overwrite the real logged response with a blank one, and
            # don't double-count usage between the two events.
            return None

        usage = resp.usage_metadata
        in_t = (getattr(usage, "prompt_token_count", None) or 0) if usage else 0
        out_t = (getattr(usage, "candidates_token_count", None) or 0) if usage else 0

        # Update rate limiter if present
        limiter = get_rate_limiter()
        if limiter:
            total_t = getattr(usage, "total_token_count", None) or (in_t + out_t)
            await limiter.update_usage(total_t)

        agent = self._c._agent_by_name(agent_name)
        model_name = getattr(agent, "model", None) or "unknown"

        # Final accounting
        self._c._cost_tracker.record_usage(model_name, in_t, out_t)

        # Signaling hook for the TUI
        self._c._on_stats(in_t, out_t, new_msg=True, model_name=model_name)

        logged_response = (
            f"[REFUSED: {refusal_reason}] {response_text}" if refusal_reason else response_text
        )
        self._c.db.log_conversation(
            self._c.project_path,
            agent_name,
            self._last_prompt,
            logged_response,
            tool_calls,
            in_t,
            out_t,
        )

        # Full turn (prompt + response) goes to the logfile only — the TUI
        # log window only gets the compact "request" notice from on_before_model.
        logger.info(
            "LLM turn — agent=%s\n"
            "--- BEGIN PROMPT (%s) ---\n%s\n--- END PROMPT (%s) ---\n"
            "--- BEGIN RESPONSE (%s) ---\n%s\n--- END RESPONSE (%s) ---",
            agent_name,
            agent_name,
            self._last_prompt,
            agent_name,
            agent_name,
            response_text,
            agent_name,
        )
        return None  # Never replace the model response

    async def on_model_error(
        self,
        callback_context: CallbackContext,
        llm_request: LlmRequest,
        error: Exception,
        **kwargs: Any,
    ) -> LlmResponse | None:
        """Increment the LLM error counter on model API failures."""
        agent_name = getattr(callback_context, "agent_name", "unknown")
        logger.warning("Model error in agent %s: %s", agent_name, error)
        self._c._on_llm_error()
        return None  # Let the error propagate
