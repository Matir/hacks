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
        Executes Semgrep via Docker and parses findings.
        """
        # Ensure target_path is absolute for mounting
        abs_target = str(Path(target_path).resolve())
        
        # We'll use a temporary file on the host to capture the JSON output
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            output_host_path = tmp.name
        
        try:
            # We mount the parent of the temp file so the container can write to it
            # Or better, just let ContainerTool handle standard run and we use --json
            # and capture stdout if we don't want to mess with mounts.
            # But Semgrep can be chatty on stderr.
            
            # Revised approach: Run semgrep and capture stdout as JSON.
            # SemgrepTool is a ContainerTool, so it uses self._client.containers.run
            
            abs_target = str(Path(target_path).resolve())
            
            logger.info("Starting Semgrep scan on %s", abs_target)
            
            # We override the command to output to stdout instead of a file for easier retrieval
            command = "semgrep scan --json --config auto /src"
            
            container_output = await asyncio.to_thread(
                self._client.containers.run,
                image=self.image,
                command=command,
                volumes={abs_target: {"bind": "/src", "mode": "ro"}},
                remove=True,
                stderr=True,
            )
            
            data = json.loads(container_output.decode("utf-8"))
            return self.parse_output(data)

        except json.JSONDecodeError as e:
            logger.error("Failed to parse Semgrep output: %s", e)
            raise ToolError(
                tool_name=self.name,
                error_type=ToolErrorType.RUNTIME_ERROR,
                stderr_tail="Invalid JSON output from Semgrep"
            )
        except Exception as e:
            logger.exception("Semgrep execution failed: %s", e)
            raise ToolError(
                tool_name=self.name,
                error_type=ToolErrorType.RUNTIME_ERROR,
                stderr_tail=str(e)
            )
        finally:
            if os.path.exists(output_host_path):
                os.unlink(output_host_path)

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
