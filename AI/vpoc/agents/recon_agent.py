import asyncio
import json
import logging
import os
import typing
from pathlib import Path

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
    description: str = "Maps the target's attack surface and identifies entry points."

    # Common routing and configuration file patterns
    ROUTING_PATTERNS = [
        "routes.rb", "urls.py", "main.py", "app.py", "index.js",
        "api.php", "web.php", "docker-compose.yml", ".env",
        "package.json", "go.mod", "Cargo.toml"
    ]

    def __init__(self, **data: typing.Any):
        super().__init__(**data)
        self.prompt_loader = PromptLoader()

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
            for file in files:
                if any(pattern in file for pattern in self.ROUTING_PATTERNS):
                    found_files.append(Path(root) / file)

        yield Event(author=self.name, content=types.Content(parts=[types.Part(text=f"Found {len(found_files)} potential routing/config files.")]))

        # 2. Analyze files with LLM
        for file_path in found_files:
            try:
                content = file_path.read_text(errors="ignore")[:10000] # Cap for safety
                
                # Load and render prompt
                template = self.prompt_loader.load_prompt("recon_agent")
                prompt = self.prompt_loader.render(template, file_path=str(file_path), content=content)

                # TODO: Implement LiteLlm call to get structured JSON output
                # For now, deterministic placeholder logic to simulate LLM finding HVTs:
                
                # Simulate finding an entry point
                if "routes" in file_path.name or "urls" in file_path.name:
                    res = ReconResult(
                        project_id=self.project_id,
                        file_path=str(file_path),
                        result_type="ENTRY_POINT",
                        description=f"Likely contains API routes or URL mappings.",
                        priority="HIGH",
                        metadata_json=json.dumps({"file": str(file_path)})
                    )
                    self.storage_manager.add_recon_result(res)
                
                # Simulate finding a config/sensitive file
                if ".env" in file_path.name or "docker-compose" in file_path.name:
                    res = ReconResult(
                        project_id=self.project_id,
                        file_path=str(file_path),
                        result_type="CONFIG",
                        description=f"Environment or infrastructure configuration.",
                        priority="MEDIUM"
                    )
                    self.storage_manager.add_recon_result(res)

                yield Event(author=self.name, content=types.Content(parts=[types.Part(text=f"Analyzed {file_path.name}")]))
            except Exception as e:
                logger.error("Failed to analyze %s: %s", file_path, e)

        # 3. Aggregate results and log
        yield Event(
            author=self.name,
            content=types.Content(parts=[types.Part(text="Attack surface mapping complete. HVTs persisted.")]),
        )
