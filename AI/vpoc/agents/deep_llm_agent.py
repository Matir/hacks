import asyncio
import json
import logging
import typing
import re
from pathlib import Path
from pydantic import PrivateAttr

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

    _prompt_loader: PromptLoader = PrivateAttr()

    def __init__(self, **data: typing.Any):
        super().__init__(**data)
        self._prompt_loader = PromptLoader()

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

        target_desc = self.project_config.target_description if self.project_config else "N/A"
        entry_points = ", ".join([r.file_path for r in recon_results if r.result_type == "ENTRY_POINT"])

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
                yield Event(author=self.name, content=types.Content(parts=[types.Part(text=f"Auditing {file_path.name}...")]),)
                content = file_path.read_text(errors="ignore")[:15000] # Slightly larger cap for deep review
                
                # Load and render prompt
                template = self._prompt_loader.load_prompt("deep_llm_agent")
                prompt = self._prompt_loader.render(
                    template,
                    file_path=str(file_path),
                    target_description=target_desc,
                    entry_points=entry_points or "None identified yet",
                    content=content
                )

                response = await self.call_llm(prompt)
                res_data = self._extract_json(response)
                
                findings_data = res_data.get("findings", [])
                
                if not findings_data:
                    yield Event(author=self.name, content=types.Content(parts=[types.Part(text=f"Audited {file_path.name}: No findings.")]))
                    continue

                for f_data in findings_data:
                    confidence = f_data.get("llm_confidence", 0.0)
                    vuln_type = f_data.get("vuln_type", "Unknown")
                    impact = IMPACT_WEIGHT.get(vuln_type, 10)
                    priority = (impact * confidence) + RECENCY_BONUS

                    finding = Finding(
                        project_id=self.project_id,
                        vuln_type=vuln_type,
                        file_path=str(file_path),
                        line_number=f_data.get("line_number", 0),
                        severity=f_data.get("severity", "medium"),
                        status=FindingStatus.POTENTIAL, # Deep review findings need triage by Orchestrator
                        discovery_tool=self.name,
                        evidence=f_data.get("evidence", ""),
                        llm_confidence=confidence,
                        priority_score=priority,
                        cvss_score=f_data.get("cvss_score", 0.0),
                        cvss_vector=f_data.get("cvss_vector", ""),
                        llm_rationale=f_data.get("rationale", "No rationale provided.")
                    )
                    self.storage_manager.add_finding(finding)
                    yield Event(author=self.name, content=types.Content(parts=[types.Part(text=f"Discovered {vuln_type} in {file_path.name}")]),)
                
            except Exception as e:
                logger.error("Deep Review: Failed to audit %s: %s", file_path, e)

        yield Event(
            author=self.name,
            content=types.Content(parts=[types.Part(text="Deep LLM Review complete.")]),
        )

    def _extract_json(self, text: str) -> typing.Dict[str, typing.Any]:
        """Extracts JSON from triple backticks or direct text."""
        match = re.search(r"```json\n(.*?)\n```", text, re.DOTALL)
        json_str = match.group(1).strip() if match else text.strip()
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            logger.error("Failed to parse JSON from response: %s", text)
            return {}

DeepLlmAgent.model_rebuild()
