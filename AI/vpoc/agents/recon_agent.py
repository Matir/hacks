import asyncio
import json
import logging
import os
import typing
import re
from pathlib import Path
from typing import ClassVar
from pydantic import PrivateAttr, ConfigDict

from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event
from google.genai import types

from .base import VPOCMixin
from core.utils import PromptLoader
from core.models import ReconResult

logger = logging.getLogger(__name__)

class ReconAgent(VPOCMixin, BaseAgent):
    """
    Attack Surface Mapper (Recon Agent).
    Identifies entry points, routes, and high-value targets.
    """
    model_config = ConfigDict(extra="allow")

    description: str = "Maps the target's attack surface and identifies entry points."

    # Common routing and configuration file patterns
    ROUTING_PATTERNS: ClassVar[typing.List[str]] = [
        "routes.rb", "urls.py", "main.py", "app.py", "index.js",
        "api.php", "web.php", "docker-compose.yml", ".env",
        "package.json", "go.mod", "Cargo.toml"
    ]

    _prompt_loader: PromptLoader = PrivateAttr()

    def __init__(self, **data: typing.Any):
        super().__init__(**data)
        self._prompt_loader = PromptLoader()

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> typing.AsyncGenerator[Event, None]:
        yield Event(
            author=self.name,
            content=types.Content(parts=[types.Part(text="Recon Agent starting mapping...")]),
        )
        
        if not self.storage_manager or not self.project_id:
            yield Event(author=self.name, content=types.Content(parts=[types.Part(text="Error: StorageManager or project_id missing.")]))
            return

        source_root = Path("source") # Assuming workspace context
        if not source_root.exists():
            yield Event(author=self.name, content=types.Content(parts=[types.Part(text="Error: source directory not found.")]))
            return

        # 1. Scan for Routing and Config Files
        found_files = []
        for root, dirs, files in os.walk(source_root):
            # Prune common vendor dirs
            dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "vendor", "venv", ".venv")]
            for file in files:
                if any(pattern in file for pattern in self.ROUTING_PATTERNS):
                    found_files.append(Path(root) / file)

        yield Event(author=self.name, content=types.Content(parts=[types.Part(text=f"Found {len(found_files)} potential routing/config files.")]))

        # 2. Analyze files with LLM
        for file_path in found_files:
            try:
                yield Event(author=self.name, content=types.Content(parts=[types.Part(text=f"Analyzing {file_path.name}...")]),)
                content = file_path.read_text(errors="ignore")[:10000] # Cap for safety
                
                # Load and render prompt
                template = self._prompt_loader.load_prompt("recon_agent")
                prompt = self._prompt_loader.render(template, file_path=str(file_path), content=content)

                response = await self.call_llm(prompt)
                res_data = self._extract_json(response)
                
                # Process entry points
                for ep in res_data.get("entry_points", []):
                    res = ReconResult(
                        project_id=self.project_id,
                        file_path=str(file_path),
                        result_type="ENTRY_POINT",
                        description=f"{ep.get('method', 'GET')} {ep.get('path', '')}: {ep.get('description', '')}",
                        priority=ep.get("priority", "MEDIUM").upper(),
                        metadata_json=json.dumps(ep)
                    )
                    self.storage_manager.add_recon_result(res)
                
                # Process high-value files
                for hvf in res_data.get("high_value_files", []):
                    res = ReconResult(
                        project_id=self.project_id,
                        file_path=hvf,
                        result_type="HIGH_VALUE_FILE",
                        description="Identified as high-value target by ReconAgent.",
                        priority="HIGH"
                    )
                    self.storage_manager.add_recon_result(res)

                # Special case for .env and docker-compose if not already covered
                if ".env" in file_path.name or "docker-compose" in file_path.name:
                    res = ReconResult(
                        project_id=self.project_id,
                        file_path=str(file_path),
                        result_type="CONFIG",
                        description=f"Environment or infrastructure configuration.",
                        priority="MEDIUM"
                    )
                    self.storage_manager.add_recon_result(res)

            except Exception as e:
                logger.error("Failed to analyze %s: %s", file_path, e)

        # 3. Aggregate results and log
        yield Event(
            author=self.name,
            content=types.Content(parts=[types.Part(text="Attack surface mapping complete. HVTs persisted.")]),
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

ReconAgent.model_rebuild()
