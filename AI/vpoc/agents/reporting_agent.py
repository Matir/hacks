import logging
import typing
from pathlib import Path
from pydantic import PrivateAttr
from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event
from google.genai import types

from .base import VPOCMixin
from core.utils import PromptLoader
from core.models import Finding, FindingStatus

logger = logging.getLogger(__name__)

class ReportingAgent(VPOCMixin, BaseAgent):
    """
    Reporting Agent.
    Aggregates findings and synthesizes logs into human-readable security reports.
    """
    description: str = "Synthesizes analysis results into security reports."

    _prompt_loader: PromptLoader = PrivateAttr()

    def __init__(self, **data: typing.Any):
        super().__init__(**data)
        self._prompt_loader = PromptLoader()

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> typing.AsyncGenerator[Event, None]:
        yield Event(
            author=self.name,
            content=types.Content(parts=[types.Part(text="Reporting Agent: Starting report synthesis...")]),
        )

        if not self.storage_manager or not self.project_id:
            yield Event(author=self.name, content=types.Content(parts=[types.Part(text="Error: StorageManager or project_id missing.")]))
            return

        # 1. Aggregate findings
        all_findings = []
        with self.storage_manager.engine.connect() as conn:
            from sqlmodel import Session, select
            with Session(self.storage_manager.engine) as session:
                statement = select(Finding).where(Finding.project_id == self.project_id)
                all_findings = list(session.exec(statement).all())

        if not all_findings:
            yield Event(author=self.name, content=types.Content(parts=[types.Part(text="No findings to report.")]),)
            return

        # 2. Synthesize Executive Summary via LLM
        yield Event(author=self.name, content=types.Content(parts=[types.Part(text="Synthesizing executive summary...")]),)
        
        findings_summary = "\n".join([
            f"- {f.vuln_type} in {f.file_path}:{f.line_number} (Status: {f.status}, CVSS: {f.cvss_score})"
            for f in all_findings if f.status in (FindingStatus.VALIDATED, FindingStatus.SCREENED, FindingStatus.POC_READY)
        ])
        
        template = self._prompt_loader.load_prompt("reporting_agent")
        prompt = self._prompt_loader.render(
            template,
            project_name=self.project_config.name if self.project_config else self.project_id,
            findings_summary=findings_summary or "No high-confidence findings."
        )
        
        exec_summary = await self.call_llm(prompt)

        # 3. Build full Markdown Report
        report_lines = [
            f"# VPOC Security Analysis Report: {self.project_config.name if self.project_config else self.project_id}",
            "\n## Executive Summary\n",
            exec_summary,
            "\n## Technical Findings\n"
        ]

        for f in all_findings:
            if f.status in (FindingStatus.REJECTED, FindingStatus.POTENTIAL):
                continue
                
            report_lines.append(f"### {f.vuln_type} - {f.file_path}:{f.line_number}")
            report_lines.append(f"- **Status:** {f.status}")
            report_lines.append(f"- **Severity:** {f.severity}")
            report_lines.append(f"- **CVSS Base Score:** {f.cvss_score}")
            report_lines.append(f"- **CVSS Vector:** `{f.cvss_vector}`")
            report_lines.append(f"- **Discovery Tool:** {f.discovery_tool}")
            report_lines.append("\n#### Rationale")
            report_lines.append(f"{f.llm_rationale or 'N/A'}")
            report_lines.append("\n#### Evidence")
            report_lines.append(f"```\n{f.evidence}\n```\n")

        report_content = "\n".join(report_lines)

        # 4. Write to file
        report_dir = Path("workspaces") / self.project_id / "artifacts"
        report_dir.mkdir(parents=True, exist_ok=True)
        report_file = report_dir / "report.md"
        report_file.write_text(report_content)

        yield Event(
            author=self.name,
            content=types.Content(parts=[types.Part(text=f"Reporting Agent: Report generated at {report_file}")]),
        )

ReportingAgent.model_rebuild()
