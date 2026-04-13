import asyncio
import json
import logging
import typing
from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event
from google.genai import types

from .base import VPOCMixin
from tools import base as tools_base
from tools.registry import registry, initialize_registry
from core.utils import LanguageDetector, PromptLoader
from core.models import Finding, FindingStatus, IMPACT_WEIGHT, RECENCY_BONUS

logger = logging.getLogger(__name__)

# Initialize tools at module level
initialize_registry()

class SourceReviewAgent(VPOCMixin, BaseAgent):
    """
    Source Review Agent responsible for orchestrating static analysis tools
    and performing LLM-based pre-screening.
    """

    description: str = (
        "Orchestrates static analysis tools and filters potential vulnerabilities."
    )
    max_concurrent: int = 4

    def __init__(self, **data: typing.Any):
        super().__init__(**data)
        self._semaphore = asyncio.Semaphore(self.max_concurrent)
        self.language_detector = LanguageDetector()
        self.prompt_loader = PromptLoader()

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> typing.AsyncGenerator[Event, None]:
        """
        Main execution loop for Source Review Agent.
        """
        if not self.storage_manager or not self.project_id:
            yield Event(author=self.name, content=types.Content(parts=[types.Part(text="Error: StorageManager or project_id missing.")]))
            return

        source_path = "source"  # Assuming standard path in workspace
        
        # 1. Detect Languages
        languages = self.language_detector.detect(source_path)
        yield Event(author=self.name, content=types.Content(parts=[types.Part(text=f"Detected languages: {', '.join(languages)}")]))

        # 2. Select and Run Tools
        tools = registry.get_tools_for_languages(languages)
        yield Event(author=self.name, content=types.Content(parts=[types.Part(text=f"Running {len(tools)} tools: {', '.join([t.name for t in tools])}")]))
        
        raw_findings = await self.run_analysis(tools, source_path)
        yield Event(author=self.name, content=types.Content(parts=[types.Part(text=f"Discovered {len(raw_findings)} potential findings.")]))

        # 3. Pre-Screen Findings with LLM
        for raw in raw_findings:
            finding = await self._pre_screen(raw)
            if finding:
                self.storage_manager.add_finding(finding)
                status_msg = f"Promoted to {finding.status}"
                logger.info("Finding: %s at %s:%d - %s", finding.vuln_type, finding.file_path, finding.line_number, status_msg)

    async def _pre_screen(self, raw: typing.Dict[str, typing.Any]) -> typing.Optional[Finding]:
        """
        Uses LLM to evaluate a raw finding.
        
        Assigns confidence, CVSS, and determines if it should be SCREENED or REJECTED.
        """
        # 1. Prepare prompt
        template = self.prompt_loader.load_prompt("source_review_agent")
        prompt = self.prompt_loader.render(
            template,
            vuln_type=raw.get("vuln_type", "Unknown"),
            file_path=raw.get("file", "unknown"),
            line_number=raw.get("line", 0),
            severity=raw.get("severity", "medium"),
            discovery_tool=raw.get("discovery_tool", "unknown"),
            evidence=json.dumps(raw, indent=2)
        )

        # 2. TODO: Implement actual LiteLlm call
        # results = await self.call_llm(prompt)
        # res = json.loads(results)
        
        # For now, deterministic placeholder logic:
        confidence = 0.8
        vuln_type = raw.get("vuln_type", "Unknown")
        impact = IMPACT_WEIGHT.get(vuln_type, 10)
        priority = (impact * confidence) + RECENCY_BONUS

        finding = Finding(
            project_id=self.project_id,
            vuln_type=vuln_type,
            file_path=raw.get("file", "unknown"),
            line_number=raw.get("line", 0),
            severity=raw.get("severity", "medium"),
            status=FindingStatus.SCREENED if confidence > 0.5 else FindingStatus.REJECTED,
            discovery_tool=raw.get("discovery_tool", "unknown"),
            evidence=json.dumps(raw),
            llm_confidence=confidence,
            priority_score=priority,
            cvss_score=7.5,
            cvss_vector="CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
            llm_rationale="Simulated pre-screening rationale."
        )
        return finding

    async def run_analysis(
        self, tools: typing.List[tools_base.AsyncTool], project_path: str
    ) -> typing.List[typing.Dict[str, typing.Any]]:
        """
        Runs multiple tools concurrently and aggregates findings.

        :param tools: List of tools to run in parallel.
        :param project_path: Path to the workspace source directory.
        :return: Aggregated list of findings from all tools.
        """
        tasks = [self._run_single_tool(tool, project_path) for tool in tools]
        results = await asyncio.gather(*tasks)
        return self._aggregate_findings(list(results))

    async def _run_single_tool(
        self, tool: tools_base.AsyncTool, project_path: str
    ) -> typing.Dict[str, typing.Any]:
        """Runs a single tool with concurrency control.

        :raises tools_base.ToolError: Propagated from the tool on failure.
        """
        async with self._semaphore:
            try:
                logger.info("Starting %s on %s", tool.name, project_path)
                result = await tool.run_async(project_path)
                logger.info("Completed %s", tool.name)
                return result
            except tools_base.ToolError as e:
                logger.error(
                    "Tool %s failed [%s]: %s", tool.name, e.error_type, e.stderr_tail
                )
                return {"tool": tool.name, "findings": [], "error": str(e)}

    def _aggregate_findings(
        self, results: typing.List[typing.Dict[str, typing.Any]]
    ) -> typing.List[typing.Dict[str, typing.Any]]:
        """Synthesizes results from different tools into a unified list."""
        all_findings: typing.List[typing.Dict[str, typing.Any]] = []
        for result in results:
            findings = result.get("findings", [])
            for f in findings:
                f["discovery_tool"] = result.get("tool", "unknown")
                all_findings.append(f)
        return all_findings
