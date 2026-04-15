import uuid
from typing import List, Dict, Optional, Any, TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import logging

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService, BaseSessionService
from google.adk.artifacts import BaseArtifactService
import google.genai.types as genai_types
from trashdig.services.cost import CostTracker

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
        artifact_service: Optional[BaseArtifactService] = None,
        session_id_prefix: Optional[str] = None,
        cost_tracker: Optional[CostTracker] = None,
    ):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.max_context_tokens = max_context_tokens
        self.compaction_threshold = compaction_threshold
        self.state = EngineState.IDLE
        self.session_service = session_service if session_service is not None else InMemorySessionService()
        self.artifact_service = artifact_service
        self.session_id_prefix = session_id_prefix
        self.cost_tracker = cost_tracker or CostTracker()
        self.total_messages = 0

    async def run(
        self,
        agent: "BaseAgent",
        prompt: str,
    ) -> EngineResult:
        """Executes an agent with the given prompt, handling tool loops and retries."""
        self.state = EngineState.RUNNING
        
        runner = Runner(
            agent=agent,
            app_name=agent.name,
            session_service=self.session_service,
            artifact_service=self.artifact_service,
        )
        
        content = genai_types.Content(role="user", parts=[genai_types.Part(text=prompt)])
        
        retries = 0
        while retries <= self.max_retries:
            try:
                # Create a unique session ID for this run if prefix is provided
                session_id = f"{self.session_id_prefix}:{agent.name}" if self.session_id_prefix else str(uuid.uuid4())
                
                result_text = ""
                total_input = 0
                total_output = 0
                tool_calls = []

                async for event in runner.run_async(
                    new_message=content, 
                    session_id=session_id,
                    user_id="default_user"
                ):
                    if hasattr(event, "usage_metadata") and event.usage_metadata:
                        total_input += event.usage_metadata.prompt_token_count or 0
                        total_output += event.usage_metadata.candidates_token_count or 0
                        self.cost_tracker.record_usage(
                            agent.model, 
                            event.usage_metadata.prompt_token_count or 0, 
                            event.usage_metadata.candidates_token_count or 0
                        )
                    
                    if hasattr(event, "content") and event.content and event.content.parts:
                        for part in event.content.parts:
                            if part.text:
                                result_text += part.text
                            if part.function_call:
                                tool_calls.append({
                                    "name": part.function_call.name,
                                    "args": part.function_call.args,
                                    "id": part.function_call.id
                                })
                                self.state = EngineState.WAITING_FOR_TOOLS

                self.total_messages += 1
                self.state = EngineState.COMPLETED

                # Trigger compaction if threshold exceeded
                if total_input > (self.max_context_tokens * self.compaction_threshold):
                    await self._compact_history(session_id)

                return EngineResult(
                    text=result_text,
                    input_tokens=total_input,
                    output_tokens=total_output,
                    tool_calls=tool_calls,
                    status=EngineState.COMPLETED
                )

            except Exception as e:
                retries += 1
                logger.warning(f"Engine retry {retries}/{self.max_retries} for agent {agent.name}: {e}")
                if retries > self.max_retries:
                    self.state = EngineState.FAILED
                    return EngineResult(status=EngineState.FAILED, error=str(e))
                await asyncio.sleep(self.retry_delay)
        
        return EngineResult(status=EngineState.FAILED, error="Max retries exceeded")

    @property
    def ctx(self) -> Any:
        """Returns a dummy context for the current runner. 
        Note: ADK's Context is usually created per session.
        """
        from google.adk.agents import Context
        # This is a bit of a hack to provide a context object for manual loop running
        return Context()

    async def _compact_history(self, session_id: str) -> None:
        """Triggers history compaction/summarization via ADK."""
        try:
            events = await self.session_service.get_events(session_id)
            if len(events) < 20:
                return
            
            logger.info(f"Compacting history for session {session_id}")
            surviving_events = events[-10:]
            new_session = f"{session_id}:compacted"
            for event in surviving_events:
                await self.session_service.append_event(new_session, event)
        except Exception as e:
            logger.error(f"Failed to compact persistent history: {e}")
