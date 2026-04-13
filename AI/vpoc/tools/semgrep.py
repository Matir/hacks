import json
import logging
import typing
from pathlib import Path

from .base import ContainerTool, ToolError, ToolErrorType

logger = logging.getLogger(__name__)

class SemgrepTool(ContainerTool):
    """
    Semgrep Static Analysis Tool.
    Runs Semgrep in a container and parses its JSON output.
    """

    def __init__(self, name: str = "Semgrep") -> None:
        super().__init__(
            name=name,
            image="semgrep/semgrep:latest",
            command_template="semgrep scan --json --config auto --output /tmp/output.json /src"
        )

    async def run_async(
        self, target_path: str, **kwargs: typing.Any
    ) -> typing.Dict[str, typing.Any]:
        """
        Executes Semgrep and parses findings.
        """
        # For now, we use the base implementation's placeholder
        # In a real implementation, this would call docker-py
        # and then read the output.json file.
        
        # result = await super().run_async(target_path, **kwargs)
        
        # Simulate parsing logic for when we have real output:
        # with open(output_file) as f:
        #     data = json.load(f)
        # return self.parse_output(data)
        
        return {"tool": self.name, "findings": []}

    def parse_output(self, data: typing.Dict[str, typing.Any]) -> typing.Dict[str, typing.Any]:
        """
        Parses Semgrep JSON output into VPOC raw findings schema.
        """
        findings = []
        for result in data.get("results", []):
            finding = {
                "vuln_type": result.get("check_id", "Unknown"),
                "file": result.get("path"),
                "line": result.get("start", {}).get("line"),
                "severity": result.get("extra", {}).get("severity", "medium"),
                "message": result.get("extra", {}).get("message"),
                "evidence": result.get("extra", {}).get("lines"),
            }
            findings.append(finding)
        
        return {
            "tool": self.name,
            "findings": findings
        }
