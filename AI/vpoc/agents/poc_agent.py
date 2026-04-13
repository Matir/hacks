import logging
import typing
import json
import re
from pathlib import Path
from pydantic import PrivateAttr, ConfigDict
from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event
from google.genai import types

from .base import VPOCMixin
from core.utils import PromptLoader
from core.models import Finding

logger = logging.getLogger(__name__)

class PocAgent(VPOCMixin, BaseAgent):
    """
    PoC Agent.
    Generates specialized exploit scripts and Docker environments.
    """
    model_config = ConfigDict(extra="allow")

    description: str = "Dynamically generates exploit scripts and sandbox environments."
    
    finding_id: typing.Optional[int] = None
    _prompt_loader: PromptLoader = PrivateAttr()

    def __init__(self, **data: typing.Any):
        super().__init__(**data)
        self._prompt_loader = PromptLoader()

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> typing.AsyncGenerator[Event, None]:
        finding_id = self.finding_id
        
        if not finding_id:
            yield Event(author=self.name, content=types.Content(parts=[types.Part(text="Error: No finding_id provided to PoC Agent.")]))
            return

        yield Event(
            author=self.name,
            content=types.Content(parts=[types.Part(text=f"PoC Agent: Generating artifacts for finding {finding_id}...")]),
        )

        # 1. Fetch Finding details
        with self.storage_manager.engine.connect() as conn:
            from sqlmodel import Session
            with Session(self.storage_manager.engine) as session:
                finding = session.get(Finding, finding_id)
                if not finding:
                    yield Event(author=self.name, content=types.Content(parts=[types.Part(text=f"Error: Finding {finding_id} not found in database.")]))
                    return

        # 2. Setup Artifact directory
        artifact_dir = Path("workspaces") / self.project_id / "artifacts" / str(finding_id)
        artifact_dir.mkdir(parents=True, exist_ok=True)

        try:
            # 3. Generate Exploit
            yield Event(author=self.name, content=types.Content(parts=[types.Part(text="Generating exploit script...")]),)
            exploit_template = self._prompt_loader.load_prompt("poc_agent", "exploit_gen")
            exploit_prompt = self._prompt_loader.render(
                exploit_template,
                vuln_type=finding.vuln_type,
                file_path=finding.file_path,
                line_number=finding.line_number,
                severity=finding.severity,
                discovery_tool=finding.discovery_tool,
                evidence=finding.evidence,
                rationale=finding.llm_rationale or "No rationale provided."
            )
            
            exploit_response = await self.call_llm(exploit_prompt)
            exploit_code = self._extract_code(exploit_response)
            
            # Determine extension
            ext = ".py"
            if "bash" in exploit_response.lower() or "#!/bin/bash" in exploit_code:
                ext = ".sh"
            
            exploit_file = artifact_dir / f"exploit{ext}"
            exploit_file.write_text(exploit_code)

            # 4. Generate Dockerfile
            yield Event(author=self.name, content=types.Content(parts=[types.Part(text="Generating Dockerfile...")]),)
            docker_template = self._prompt_loader.load_prompt("poc_agent", "dockerfile_gen")
            # TODO: Get target_language from project config
            docker_prompt = self._prompt_loader.render(
                docker_template,
                exploit_code=exploit_code,
                target_language="unknown" 
            )
            
            docker_response = await self.call_llm(docker_prompt)
            dockerfile_content = self._extract_code(docker_response)
            (artifact_dir / "Dockerfile").write_text(dockerfile_content)

            # 5. Metadata
            metadata = {
                "finding_id": finding_id,
                "vuln_type": finding.vuln_type,
                "target": f"{finding.file_path}:{finding.line_number}",
                "exploit_file": exploit_file.name,
            }
            (artifact_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))

            yield Event(
                author=self.name,
                content=types.Content(parts=[types.Part(text=f"PoC Agent: Artifacts staged at {artifact_dir}")]),
            )

        except Exception as e:
            logger.exception("PoC Agent failed: %s", e)
            yield Event(author=self.name, content=types.Content(parts=[types.Part(text=f"Error during artifact generation: {str(e)}")]),)

    def _extract_code(self, text: str) -> str:
        """Extracts code from triple backticks."""
        match = re.search(r"```(?:\w+)?\n(.*?)\n```", text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return text.strip()

PocAgent.model_rebuild()
