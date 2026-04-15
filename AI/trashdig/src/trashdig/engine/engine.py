import uuid
from typing import List, Dict, Optional, Any, Callable, TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import logging

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService, BaseSessionService
import google.genai.types as genai_types

if TYPE_CHECKING:
    from google.adk.agents import BaseAgent

logger = logging.getLogger(__name__)

class EngineState(Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    WAITING_FOR_TOOLS = "WAITING_FOR_TOOLS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

@dataclass
class EngineResult:
    text: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    status: EngineState = EngineState.IDLE
    error: Optional[str] = None

class Engine:
    """The Engine handles the core Observer-Actor loop for ADK agents.
    
    It manages multi-turn tool calling, retries for transient LLM errors, 
    and context token tracking.
    """

    def __init__(
        self,
        max_retries: int = 3,
        retry_delay: float = 2.0,
        max_context_tokens: int = 128000,
        compaction_threshold: float = 0.8,
        session_service: Optional[BaseSessionService] = None,
        session_id_prefix: Optional[str] = None,
    ):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.max_context_tokens = max_context_tokens
        self.compaction_threshold = compaction_threshold
        self.state = EngineState.IDLE
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.session_service = session_service if session_service is not None else InMemorySessionService()
        self.session_id_prefix = session_id_prefix

    async def run(
        self,
        agent: "BaseAgent",
        prompt: str,
        on_event: Optional[Callable[[str], None]] = None,
        on_stats: Optional[Callable[[int, int, bool], None]] = None,
        on_error: Optional[Callable[[], None]] = None,
        session_id: Optional[str] = None,
    ) -> EngineResult:
        """Runs a prompt through the agent with retries and tracking.
        
        Args:
            agent: The ADK agent instance to run.
            prompt: The text prompt to send.
            on_event: Callback for tool call events.
            on_stats: Callback for token usage stats (input, output, is_final).
            on_error: Callback for transient LLM errors.
            
        Returns:
            An EngineResult object containing the outcome of the run.
        """
        from trashdig.services.rate_limiter import get_rate_limiter
        limiter = get_rate_limiter()

        self.state = EngineState.RUNNING
        result = EngineResult()

        user_id = "trashdig"
        # Use caller-supplied session_id, fall back to prefix-scoped or fresh UUID
        if session_id is None:
            if self.session_id_prefix:
                session_id = f"{self.session_id_prefix}:{agent.name}"
            else:
                session_id = str(uuid.uuid4())

        existing = await self.session_service.get_session(
            app_name=agent.name, user_id=user_id, session_id=session_id
        )
        if existing is None:
            await self.session_service.create_session(
                app_name=agent.name,
                user_id=user_id,
                session_id=session_id,
            )
        
        runner = Runner(
            agent=agent,
            app_name=agent.name,
            session_service=self.session_service,
        )
        
        content = genai_types.Content(role="user", parts=[genai_types.Part(text=prompt)])
        
        retries = 0
        while retries <= self.max_retries:
            if limiter:
                await limiter.wait_for_request()

            try:
                # Reset intermediate tokens for this attempt
                input_tokens = 0
                output_tokens = 0
                final_text = ""
                tool_calls = []

                async for event in runner.run_async(
                    user_id=user_id,
                    session_id=session_id,
                    new_message=content,
                ):
                    # Handle tool-calling state
                    if event.content and any(getattr(p, "function_call", None) for p in event.content.parts):
                        self.state = EngineState.WAITING_FOR_TOOLS
                    else:
                        self.state = EngineState.RUNNING

                    # Extract token usage
                    usage = getattr(event, "usage_metadata", None)
                    if usage is None:
                        usage = getattr(getattr(event, "response", None), "usage_metadata", None)
                    if usage is None:
                        usage = getattr(getattr(event, "raw_response", None), "usageMetadata", None)

                    if usage is not None:
                        if isinstance(usage, dict):
                            pt = usage.get("prompt_token_count") or usage.get("promptTokenCount") or 0
                            ct = usage.get("candidates_token_count") or usage.get("candidatesTokenCount") or 0
                        else:
                            pt = getattr(usage, "prompt_token_count", 0) or getattr(usage, "promptTokenCount", 0) or 0
                            ct = getattr(usage, "candidates_token_count", 0) or getattr(usage, "candidatesTokenCount", 0) or 0

                        if pt:
                            input_tokens = max(input_tokens, pt)
                        if ct:
                            output_tokens = max(output_tokens, ct)
                        
                        if on_stats:
                            on_stats(input_tokens, output_tokens, False)
                        
                        # Context Compaction check
                        if input_tokens > (self.max_context_tokens * self.compaction_threshold):
                            await self._compact_history(agent.name, user_id, session_id)

                    # Extract tool calls for logging
                    if event.content and event.content.parts:
                        for part in event.content.parts:
                            fc = getattr(part, "function_call", None)
                            if fc and getattr(fc, "name", None):
                                args = getattr(fc, "args", {}) or {}
                                tool_calls.append({"name": fc.name, "args": args})
                                if on_event:
                                    args_str = ", ".join(f"{k}={repr(v)[:60]}" for k, v in args.items())
                                    on_event(f"  [dim]→ {fc.name}({args_str})[/dim]")

                    # Capture final response
                    if event.is_final_response() and event.content and event.content.parts:
                        for part in event.content.parts:
                            if hasattr(part, "text") and part.text:
                                final_text = part.text

                # Success!
                result.text = final_text
                result.input_tokens = input_tokens
                result.output_tokens = output_tokens
                result.tool_calls = tool_calls
                result.status = EngineState.COMPLETED
                self.state = EngineState.COMPLETED
                
                self.total_input_tokens += input_tokens
                self.total_output_tokens += output_tokens
                
                if limiter:
                    await limiter.update_usage(input_tokens + output_tokens)
                
                if on_stats:
                    on_stats(input_tokens, output_tokens, True)
                
                return result

            except Exception as e:
                retries += 1
                if on_error:
                    on_error()
                
                if retries > self.max_retries:
                    self.state = EngineState.FAILED
                    result.status = EngineState.FAILED
                    result.error = str(e)
                    raise e
                
                logger.warning(f"Engine retry {retries}/{self.max_retries} due to: {e}")
                await asyncio.sleep(self.retry_delay * retries)
                # Note: Content is same, session/runner state depends on runner behavior.
                # If we retry, we might want to start a fresh runner or session if it's corrupted.
                # For now, we reuse them.

        return result

    async def _compact_history(self, agent_name: str, user_id: str, session_id: str):
        """Compact the conversation history by pruning intermediate events.

        Keeps the first event (initial prompt) and the last 3 events to
        preserve context flow while staying within the token budget.

        For InMemorySessionService, uses direct internal mutation (fast path).
        For all other services (e.g. SqliteSessionService), uses the public
        delete + recreate API.

        Args:
            agent_name: Name of the agent (app_name).
            user_id: ID of the user.
            session_id: ID of the session.
        """
        session = await self.session_service.get_session(
            app_name=agent_name, user_id=user_id, session_id=session_id
        )
        if not session or len(session.events) <= 4:
            return

        surviving_events = [session.events[0]] + session.events[-3:]

        if isinstance(self.session_service, InMemorySessionService):
            # Fast path: direct internal mutation for in-memory service.
            try:
                internal_session = self.session_service.sessions[agent_name][user_id][session_id]
                if len(internal_session.events) > 4:
                    logger.info(
                        f"Compacting (in-memory) session {session_id}: "
                        f"{len(internal_session.events)} → {len(surviving_events)} events"
                    )
                    internal_session.events = surviving_events
            except (AttributeError, KeyError, IndexError) as e:
                logger.error(f"Failed to compact in-memory history: {e}")
        else:
            # Generic path: delete the session and recreate with pruned events.
            # SqliteSessionService uses ON DELETE CASCADE on events, so deleting
            # the session row also removes all its child event rows atomically.
            logger.info(
                f"Compacting (persistent) session {session_id}: "
                f"{len(session.events)} → {len(surviving_events)} events"
            )
            try:
                await self.session_service.delete_session(
                    app_name=agent_name, user_id=user_id, session_id=session_id
                )
                new_session = await self.session_service.create_session(
                    app_name=agent_name,
                    user_id=user_id,
                    session_id=session_id,
                    state=session.state,
                )
                for event in surviving_events:
                    await self.session_service.append_event(new_session, event)
            except Exception as e:
                logger.error(f"Failed to compact persistent history: {e}")
