import asyncio
import logging
import typing
from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event
from google.adk.runners.runner import Runner
from google.genai import types

from .base import VPOCMixin
from .recon_agent import ReconAgent
from .source_review_agent import SourceReviewAgent
from .deep_llm_agent import DeepLlmAgent
from core.models import FindingStatus, Finding
from core.agent_manager import AgentManager
from core.events import TOPIC_LOG_LINE, Event as VpocEvent

logger = logging.getLogger(__name__)


class OrchestratorAgent(VPOCMixin, BaseAgent):
    """
    The central intelligence of VPOC.
    
    Manages project lifecycle, handles user hints/commands, 
    and coordinates sub-agents via AgentManager.
    """

    description: str = "Central orchestrator for security analysis."
    
    # Internal state for tracking progress
    _agent_manager: typing.Optional[AgentManager] = None

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> typing.AsyncGenerator[Event, None]:
        """
        Main execution loop for the Orchestrator.
        """
        yield Event(
            author=self.name,
            content=types.Content(
                parts=[types.Part(text="Orchestrator starting analysis...")]
            ),
        )

        if not self.storage_manager or not self._agent_manager:
            raise RuntimeError("StorageManager or AgentManager not initialized.")

        # 1. Trigger Recon Phase
        await self._log_to_bus("Starting reconnaissance phase...")
        recon_runner = await self._agent_manager.get_or_create_runner(ReconAgent, "ReconAgent")
        
        # Recon is usually quick and provides context for Source Review
        async for event in recon_runner.run():
            if hasattr(event, "content") and event.content:
                for part in event.content.parts:
                    if part.text:
                        await self._log_to_bus(f"Recon: {part.text}")

        # 2. Trigger Deep LLM Review (on High-Value Targets)
        await self._log_to_bus("Starting deep LLM review phase...")
        deep_runner = await self._agent_manager.get_or_create_runner(DeepLlmAgent, "DeepLlmAgent")
        
        async for event in deep_runner.run():
            if hasattr(event, "content") and event.content:
                for part in event.content.parts:
                    if part.text:
                        await self._log_to_bus(f"Deep Review: {part.text}")

        # 3. Trigger Source Review
        await self._log_to_bus("Starting source review phase...")
        sr_runner = await self._agent_manager.get_or_create_runner(SourceReviewAgent, "SourceReviewAgent")
        
        # We start it as a background task because Orchestrator must continue 
        # monitoring for findings and hints.
        sr_task = asyncio.create_task(self._run_source_review(sr_runner))

        # 2. Main Monitoring & Handoff Loop
        while True:
            # Poll for SCREENED findings to enqueue (that aren't already being processed)
            screened = self.storage_manager.get_findings_by_status(FindingStatus.SCREENED)
            for finding in screened:
                await self._agent_manager.enqueue_finding(finding)
                # Mark as POC_GENERATING so it's not picked up again by poll
                self.storage_manager.update_finding_status(finding.id, FindingStatus.POC_GENERATING)

            # Process HintLog for new instructions and update strategy
            hints = self.storage_manager.get_hints(self.project_id)
            if hints:
                # TODO: Pass hints to Orchestrator's LLM to re-evaluate strategy
                pass

            await asyncio.sleep(2)

    async def _run_source_review(self, runner: "Runner") -> None:
        """Helper to consume events from the SourceReview runner."""
        async for event in runner.run():
            logger.debug("Source Review: %s", event)
            # Optionally broadcast key agent events back to UI bus
            if hasattr(event, "content") and event.content:
                # Accessing text parts from ADK event
                for part in event.content.parts:
                    if part.text:
                        await self._log_to_bus(f"Source Review: {part.text}")

    async def _log_to_bus(self, message: str) -> None:
        """Publishes a log line to the UI event bus."""
        if self.event_bus:
            await self.event_bus.publish(
                VpocEvent(
                    topic=TOPIC_LOG_LINE,
                    payload={"project_id": self.project_id, "message": message},
                )
            )
        logger.info("[%s] %s", self.project_id, message)
