import asyncio
import typing
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event
from google.genai import types
from .base import VPOCAgent
from tools import base as tools_base


class SourceReviewAgent(VPOCAgent):
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

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> typing.AsyncGenerator[Event, None]:
        """
        Main execution loop for Source Review Agent.
        In ADK, this is the entry point for the agent.
        """
        # TODO: Implement full agent logic including LLM pre-screening.
        # For now, it could yield a starting event.
        yield Event(
            author=self.name,
            content=types.Content(
                parts=[types.Part(text="Source Review Agent starting...")]
            ),
        )

    async def run_analysis(
        self, tools: typing.List[tools_base.AsyncTool], project_path: str
    ) -> typing.List[typing.Dict[str, typing.Any]]:
        """
        Runs multiple tools concurrently and aggregates findings.
        This preserves the AnalysisRunner logic but inside an agent.
        """
        tasks = [self._run_single_tool(tool, project_path) for tool in tools]
        results = await asyncio.gather(*tasks)
        return self._aggregate_findings(results)

    async def _run_single_tool(
        self, tool: tools_base.AsyncTool, project_path: str
    ) -> typing.Dict[str, typing.Any]:
        """Runs a single tool with concurrency control."""
        async with self._semaphore:
            try:
                # Log tool start (could use a real logger or yield an event)
                print(f"[SourceReviewAgent] Starting {tool.name} on {project_path}")
                result = await tool.run_async(project_path)
                print(f"[SourceReviewAgent] Completed {tool.name}")
                return result
            except Exception as e:
                print(f"[SourceReviewAgent] Tool {tool.name} failed: {e}")
                return {"tool": tool.name, "findings": [], "error": str(e)}

    def _aggregate_findings(
        self, results: typing.List[typing.Dict[str, typing.Any]]
    ) -> typing.List[typing.Dict[str, typing.Any]]:
        """Synthesizes results from different tools into a unified list."""
        all_findings = []
        for result in results:
            findings = result.get("findings", [])
            for f in findings:
                f["discovery_tool"] = result.get("tool", "unknown")
                all_findings.append(f)
        return all_findings
