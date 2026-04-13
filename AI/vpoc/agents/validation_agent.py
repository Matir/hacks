import logging
import typing
import json
import docker
import re
from pathlib import Path
from pydantic import PrivateAttr
from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event
from google.genai import types

from .base import VPOCMixin
from core.utils import PromptLoader
from core.sandbox import SandboxRunner
from core.models import ServerConfig, Finding, FindingStatus

logger = logging.getLogger(__name__)

class ValidationAgent(VPOCMixin, BaseAgent):
    """
    Validation Agent.
    Executes PoCs in a sandboxed environment and analyzes results.
    """
    description: str = "Executes PoCs in a hardened sandbox and confirms security impact."
    
    finding_id: typing.Optional[int] = None
    _prompt_loader: PromptLoader = PrivateAttr()

    def __init__(self, **data: typing.Any):
        super().__init__(**data)
        self._prompt_loader = PromptLoader()
        # We need a way to get ServerConfig. For MVP, we'll assume it's available or use defaults.
        self.sandbox_runner = SandboxRunner(config=ServerConfig())

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> typing.AsyncGenerator[Event, None]:
        finding_id = self.finding_id
        if not finding_id:
            yield Event(author=self.name, content=types.Content(parts=[types.Part(text="Error: No finding_id provided to Validation Agent.")]))
            return

        yield Event(
            author=self.name,
            content=types.Content(parts=[types.Part(text=f"Validation Agent: Starting validation for finding {finding_id}...")]),
        )

        artifact_dir = Path("workspaces") / self.project_id / "artifacts" / str(finding_id)
        if not artifact_dir.exists():
            yield Event(author=self.name, content=types.Content(parts=[types.Part(text=f"Error: Artifacts not found for finding {finding_id}.")]),)
            return

        # 0. Load Finding
        with self.storage_manager.engine.connect() as conn:
            from sqlmodel import Session
            with Session(self.storage_manager.engine) as session:
                finding = session.get(Finding, finding_id)
                if not finding:
                    yield Event(author=self.name, content=types.Content(parts=[types.Part(text=f"Error: Finding {finding_id} not found in database.")]))
                    return

        try:
            # 1. Build PoC Image
            yield Event(author=self.name, content=types.Content(parts=[types.Part(text="Building PoC Docker image...")]),)
            client = docker.from_env()
            image, _ = client.images.build(
                path=str(artifact_dir),
                tag=f"vpoc-finding-{finding_id}",
                rm=True
            )

            # 2. Run in Sandbox
            yield Event(author=self.name, content=types.Content(parts=[types.Part(text="Executing PoC in hardened sandbox...")]),)
            sandbox_result = await self.sandbox_runner.run_poc(image_id=image.id)

            # 3. Analyze Outcome
            yield Event(author=self.name, content=types.Content(parts=[types.Part(text="Analyzing execution outcome...")]),)
            analysis_template = self._prompt_loader.load_prompt("validation_agent", "outcome_analysis")
            analysis_prompt = self._prompt_loader.render(
                analysis_template,
                vuln_type=finding.vuln_type,
                target=f"{finding.file_path}:{finding.line_number}",
                exit_code=sandbox_result.exit_code,
                duration=round(sandbox_result.duration, 2),
                stdout=sandbox_result.stdout or "(empty)",
                stderr=sandbox_result.stderr or "(empty)"
            )
            
            analysis_response = await self.call_llm(analysis_prompt)
            analysis_data = self._extract_json(analysis_response)
            
            success = analysis_data.get("success", False)
            new_status_str = analysis_data.get("status", "INCONCLUSIVE")
            rationale = analysis_data.get("rationale", "No rationale provided.")
            
            yield Event(
                author=self.name,
                content=types.Content(parts=[types.Part(text=f"Validation Result: {new_status_str} (Success: {success})")]),
            )
            
            # 4. Update finding status in DB
            try:
                new_status = FindingStatus(new_status_str.upper())
                self.storage_manager.update_finding_status(finding_id, new_status)
                # Also update rationale
                with Session(self.storage_manager.engine) as session:
                    f = session.get(Finding, finding_id)
                    if f:
                        f.llm_rationale = (f.llm_rationale or "") + f"\n\nValidation: {rationale}"
                        session.add(f)
                        session.commit()
            except Exception as e:
                logger.error("Failed to update finding status after validation: %s", e)

        except Exception as e:
            logger.exception("Validation Agent failed: %s", e)
            yield Event(author=self.name, content=types.Content(parts=[types.Part(text=f"Error during validation: {str(e)}")]),)

    def _extract_json(self, text: str) -> typing.Dict[str, typing.Any]:
        """Extracts JSON from triple backticks or direct text."""
        match = re.search(r"```json\n(.*?)\n```", text, re.DOTALL)
        json_str = match.group(1).strip() if match else text.strip()
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            logger.error("Failed to parse JSON from analysis response: %s", text)
            return {}

ValidationAgent.model_rebuild()
