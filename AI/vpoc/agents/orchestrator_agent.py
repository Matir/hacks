import logging
import typing
from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.base_agent import BaseAgent
from google.genai import types
from pydantic import PrivateAttr

from .base import VPOCMixin
from .recon_agent import ReconAgent
from .source_review_agent import SourceReviewAgent
from .deep_llm_agent import DeepLlmAgent
from .build_agent import BuildAgent
from .reporting_agent import ReportingAgent

from . import orchestrator_tools as tools
from core.events import TOPIC_LOG_LINE, Event as VpocEvent
from core.utils import PromptLoader

if typing.TYPE_CHECKING:
    from core.agent_manager import AgentManager

logger = logging.getLogger(__name__)


class OrchestratorAgent(VPOCMixin, LlmAgent):
    """
    The autonomous coordinator of VPOC.

    Uses LLM reasoning to drive the project lifecycle, delegating to sub-agents
    and prioritizing findings based on impact and confidence.
    """

    name: str = "Orchestrator"
    description: str = "Autonomous coordinator for security analysis."

    instruction: str = ""
    
    agent_manager: typing.Optional["AgentManager"] = None
    _prompt_loader: PromptLoader = PrivateAttr()

    # Sub-agents exposed as tools by ADK
    sub_agents: typing.List[BaseAgent] = [
        ReconAgent(name="recon_agent"),
        BuildAgent(name="build_agent"),
        SourceReviewAgent(name="source_review_agent"),
        DeepLlmAgent(name="deep_review_agent"),
        ReportingAgent(name="reporting_agent"),
    ]

    def __init__(self, **data: typing.Any):
        super().__init__(**data)
        self._prompt_loader = PromptLoader()
        self.instruction = self._prompt_loader.load_prompt("orchestrator_agent")

        # Define and bind tools
        async def get_summary():
            """Returns a high-level summary of the project's current state."""
            return tools.get_project_summary(self.storage_manager, self.project_id)

        async def get_recon_summary():
            """Returns a list of entry points and high-value targets identified during Recon."""
            return tools.get_recon_results_summary(self.storage_manager, self.project_id)

        async def get_findings_to_review(limit: int = 10):
            """Returns a list of POTENTIAL findings that need review."""
            return tools.get_findings_to_review(self.storage_manager, self.project_id, limit)

        async def screen_finding(finding_id: int, status: str, rationale: str, priority_score: typing.Optional[float] = None):
            """Promotes a finding to SCREENED or REJECTED status with a rationale."""
            return tools.promote_finding(self.storage_manager, self.agent_manager, finding_id, status, rationale, priority_score)

        async def get_budget_status():
            """Returns the current token usage vs the daily limit."""
            return tools.get_budget_status(self.budget_manager, self.project_id)

        async def log_message(message: str):
            """Publishes a log message to the UI event bus."""
            if self.event_bus:
                await self.event_bus.publish(
                    VpocEvent(
                        topic=TOPIC_LOG_LINE,
                        payload={"project_id": self.project_id, "message": f"Orchestrator: {message}"},
                    )
                )
            logger.info("[%s] %s", self.project_id, message)
            return "Logged successfully."

        self.tools = [
            get_summary,
            get_recon_summary,
            get_findings_to_review,
            screen_finding,
            get_budget_status,
            log_message,
        ]

OrchestratorAgent.model_rebuild()
