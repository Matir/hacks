import asyncio
import logging
import typing
from google.adk import Agent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event
from google.genai import types
from .base import VPOCMixin
from tools import base as tools_base

logger = logging.getLogger(__name__)


class SourceReviewAgent(VPOCMixin, Agent):
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
