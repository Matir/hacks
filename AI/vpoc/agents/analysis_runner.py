import asyncio
import typing
from tools import base as tools_base


class AnalysisRunner:
    """Orchestrator for running multiple security analysis tools in parallel."""

    def __init__(self, max_concurrent: int = 4):
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def run_analysis(
        self, tools: typing.List[tools_base.AsyncTool], project_path: str
    ) -> typing.List[typing.Dict[str, typing.Any]]:
        """
        Runs multiple tools concurrently and aggregates findings.

        :param tools: List of tools to execute.
        :param project_path: Root directory of the target project.
        :return: Aggregated findings from all tools.
        """
        tasks = [self._run_single_tool(tool, project_path) for tool in tools]
        results = await asyncio.gather(*tasks)

        # Flatten and deduplicate findings (Basic implementation)
        return self._aggregate_findings(results)

    async def _run_single_tool(
        self, tool: tools_base.AsyncTool, project_path: str
    ) -> typing.Dict[str, typing.Any]:
        """Runs a single tool with concurrency control."""
        async with self.semaphore:
            try:
                # Log tool start (could use a real logger here)
                print(f"[AnalysisRunner] Starting {tool.name} on {project_path}")
                result = await tool.run_async(project_path)
                print(f"[AnalysisRunner] Completed {tool.name}")
                return result
            except Exception as e:
                # Granular exception handling as requested
                print(f"[AnalysisRunner] Tool {tool.name} failed: {e}")
                return {"tool": tool.name, "findings": [], "error": str(e)}

    def _aggregate_findings(
        self, results: typing.List[typing.Dict[str, typing.Any]]
    ) -> typing.List[typing.Dict[str, typing.Any]]:
        """Synthesizes results from different tools into a unified list."""
        all_findings = []
        for result in results:
            findings = result.get("findings", [])
            for f in findings:
                # Ensure each finding has metadata about which tool discovered it
                f["discovery_tool"] = result.get("tool", "unknown")
                all_findings.append(f)

        # TODO: Implement deep deduplication and correlation logic
        return all_findings
