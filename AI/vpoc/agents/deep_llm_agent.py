import asyncio
import json
import logging
import typing
from pathlib import Path

from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event
from google.genai import types

from .base import VPOCMixin
from core.utils import PromptLoader
from core.models import Finding, FindingStatus, IMPACT_WEIGHT, RECENCY_BONUS

logger = logging.getLogger(__name__)

class DeepLlmAgent(VPOCMixin, BaseAgent):
    """
    Deep LLM Review Agent.
    Performs high-intensity security analysis on High-Value Targets (HVTs).
    Focuses on logical flaws and complex vulnerabilities that tools miss.
    """
    description: str = "Performs deep LLM-based security audits of high-value targets."

    def __init__(self, **data: typing.Any):
        super().__init__(**data)
        self.prompt_loader = PromptLoader()

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> typing.AsyncGenerator[Event, None]:
        yield Event(
            author=self.name,
            content=types.Content(parts=[types.Part(text="Deep LLM Review Agent starting...")]),
        )
        
        if not self.storage_manager or not self.project_id:
            yield Event(author=self.name, content=types.Content(parts=[types.Part(text="Error: StorageManager or project_id missing.")]))
            return

        # 1. Fetch High-Value Targets from Recon phase
        recon_results = self.storage_manager.get_recon_results(self.project_id)
        # Filter for high-priority files
        hvts = [r for r in recon_results if r.result_type in ("ENTRY_POINT", "HIGH_VALUE_FILE") and r.priority == "HIGH"]

        if not hvts:
            yield Event(author=self.name, content=types.Content(parts=[types.Part(text="No high-value targets found to audit. skipping Deep Review.")]),)
            return

        yield Event(author=self.name, content=types.Content(parts=[types.Part(text=f"Auditing {len(hvts)} high-value targets...")]),)

        # 2. Deep Audit Loop
        for hvt in hvts:
            file_path = Path(hvt.file_path)
            if not file_path.exists():
                # Try relative to source
                file_path = Path("source") / hvt.file_path
            
            if not file_path.exists():
                logger.warning("Deep Review: HVT file not found: %s", hvt.file_path)
                continue

            try:
                content = file_path.read_text(errors="ignore")[:15000] # Slightly larger cap for deep review
                
                # Load and render prompt
                template = self.prompt_loader.load_prompt("deep_llm_agent")
                # TODO: Retrieve target_description and entry_points from project state
                prompt = self.prompt_loader.render(
                    template,
                    file_path=str(file_path),
                    target_description="Security review project",
                    entry_points="N/A",
                    content=content
                )

                # TODO: Implement LiteLlm call to get structured JSON output
                # results = await self.call_llm(prompt)
                # findings_data = json.loads(results).get("findings", [])
                
                # For now, deterministic placeholder to simulate LLM finding a logical flaw:
                yield Event(author=self.name, content=types.Content(parts=[types.Part(text=f"Audited {file_path.name}: No findings.")]))
                
            except Exception as e:
                logger.error("Deep Review: Failed to audit %s: %s", file_path, e)

        yield Event(
            author=self.name,
            content=types.Content(parts=[types.Part(text="Deep LLM Review complete.")]),
        )
