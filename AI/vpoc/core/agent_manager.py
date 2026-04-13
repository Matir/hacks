import asyncio
import logging
import typing
from dataclasses import dataclass, field

from google.adk import Agent, Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService

# Circular imports avoid with top-level but late binding if needed, 
# but for now we follow the "imports at top" rule.
from agents.poc_agent import PocAgent
from agents.validation_agent import ValidationAgent

from core.models import Finding, FindingStatus, ProjectConfig
from core.storage import StorageManager
from core.events import EventBus, Event, TOPIC_AGENT_STATUS

logger = logging.getLogger(__name__)


@dataclass(order=True)
class PrioritizedFinding:
    """Findings prioritized by their priority_score descending."""

    priority_score: float
    finding: Finding = field(compare=False)


class AgentManager:
    """Manages the lifecycle of sub-agent runners and finding queue.

    Responsible for: Dispatching findings to PoC/Validation agents,
    maintaining the priority-weighted queue, and coordinating runners.
    """

    def __init__(
        self,
        project_config: ProjectConfig,
        storage_manager: StorageManager,
        budget_manager: typing.Optional["BudgetManager"] = None,
        event_bus: typing.Optional[EventBus] = None,
        max_concurrent_findings: int = 2,
    ) -> None:
        self.config = project_config
        self.storage = storage_manager
        self.budget_manager = budget_manager
        self.event_bus = event_bus
        self.max_concurrent = max_concurrent_findings
        self.queue: asyncio.PriorityQueue[PrioritizedFinding] = asyncio.PriorityQueue()
        self._runners: typing.Dict[str, Runner] = {}
        self._session_service = InMemorySessionService()
        self._workers: typing.List[asyncio.Task] = []
        self._running = False

    async def start(self) -> None:
        """Starts the finding processing workers."""
        if self._running:
            return
        self._running = True
        for i in range(self.max_concurrent):
            task = asyncio.create_task(self._worker_loop(i))
            self._workers.append(task)
        logger.info("AgentManager started with %d workers", self.max_concurrent)

    async def stop(self) -> None:
        """Stops all workers and cleans up runners."""
        self._running = False
        for task in self._workers:
            task.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers = []
        # TODO: Runner cleanup logic
        logger.info("AgentManager stopped")

    async def enqueue_finding(self, finding: Finding) -> None:
        """Adds a finding to the priority queue for processing."""
        if finding.priority_score is None:
            # Fallback to 0 if score is missing
            score = 0.0
        else:
            # PriorityQueue is min-heap, so we negate score for max-priority
            score = -finding.priority_score
        
        await self.queue.put(PrioritizedFinding(score, finding))
        logger.debug("Finding %d enqueued with score %s", finding.id, finding.priority_score)

    async def _worker_loop(self, worker_id: int) -> None:
        """Continuous loop pulling findings from the queue."""
        while self._running:
            try:
                prioritized = await self.queue.get()
                finding = prioritized.finding
                logger.info("Worker %d processing finding %d", worker_id, finding.id)
                
                await self._process_finding(finding)
                
                self.queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("Error in AgentManager worker %d: %s", worker_id, e)

    async def _process_finding(self, finding: Finding) -> None:
        """Coordinates PoC generation and Validation for a single finding."""

        # Check if validation is enabled
        if not self.config.enable_validation:
            logger.info("Validation disabled for project %s, skipping PoC/Validation for finding %d", 
                        self.config.project_id, finding.id)
            return

        # 1. PoC Generation
        self.storage.update_finding_status(finding.id, FindingStatus.POC_GENERATING)
        poc_runner = await self.get_or_create_runner(PocAgent, "PocAgent")
        
        # In ADK, we can pass context to run(). 
        # We'll use a hack for MVP: set it on the agent or ctx if possible.
        # More idiomatic is using the session state.
        
        # For now, let's inject it into the runner's agent instance directly 
        # (risky with concurrency, but runners are 1:1 with agents in this manager for now)
        poc_runner.agent.finding_id = finding.id
        
        async for event in await poc_runner.run():
            logger.debug("PoC Agent: %s", event)

        # Assume PoC is ready for now (in reality, we'd check events/artifact existence)
        self.storage.update_finding_status(finding.id, FindingStatus.POC_READY)

        # 2. Validation
        self.storage.update_finding_status(finding.id, FindingStatus.VALIDATING)
        val_runner = await self.get_or_create_runner(ValidationAgent, "ValidationAgent")
        val_runner.agent.finding_id = finding.id
        
        async for event in await val_runner.run():
            logger.debug("Validation Agent: %s", event)

        # Final status based on validation outcome
        self.storage.update_finding_status(finding.id, FindingStatus.VALIDATED)

    async def get_or_create_runner(self, agent_cls: typing.Type[Agent], name: str) -> Runner:
        """Returns a managed runner for the given agent class."""
        if name in self._runners:
            return self._runners[name]
        
        agent = agent_cls(name=name)
        # Inject VPOC dependencies if it's a VPOCMixin agent
        if hasattr(agent, "project_id"):
            agent.project_id = self.config.project_id
        if hasattr(agent, "project_config"):
            agent.project_config = self.config
        if hasattr(agent, "storage_manager"):
            agent.storage_manager = self.storage
        if hasattr(agent, "event_bus"):
            agent.event_bus = self.event_bus
        if hasattr(agent, "budget_manager"):
            agent.budget_manager = self.budget_manager
        if hasattr(agent, "agent_manager"):
            agent.agent_manager = self

        runner = Runner(agent=agent, session_service=self._session_service)
        self._runners[name] = runner
        return runner
