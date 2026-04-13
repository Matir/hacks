import abc
import asyncio
import enum
import logging
import typing
from pathlib import Path

import docker
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ToolErrorType(str, enum.Enum):
    """Classifies the failure mode of a tool execution."""

    BUILD_FAILURE = "BUILD_FAILURE"
    RUNTIME_ERROR = "RUNTIME_ERROR"
    TIMEOUT = "TIMEOUT"


class ToolError(Exception):
    """Raised by tools on failure; carries structured error metadata.

    Tools MUST NOT fail silently.  Raise ``ToolError`` instead of returning
    a partial result or swallowing exceptions.
    """

    def __init__(
        self,
        tool_name: str,
        error_type: ToolErrorType,
        stderr_tail: str,
        suggested_fix: typing.Optional[str] = None,
    ) -> None:
        """
        :param tool_name: Name of the tool that failed.
        :param error_type: Structured failure category.
        :param stderr_tail: Last N lines of stderr for diagnosis.
        :param suggested_fix: Optional LLM-generated remediation hint.
        """
        self.tool_name = tool_name
        self.error_type = error_type
        self.stderr_tail = stderr_tail
        self.suggested_fix = suggested_fix
        super().__init__(f"[{error_type}] {tool_name}: {stderr_tail}")


class AsyncTool(abc.ABC):
    """Base class for all VPOC tools supporting asynchronous parallel execution."""

    def __init__(self, name: str) -> None:
        self.name: str = name
        self.supports_sharding: bool = False

    @abc.abstractmethod
    async def run_async(
        self, target_path: str, **kwargs: typing.Any
    ) -> typing.Dict[str, typing.Any]:
        """Executes the tool asynchronously.

        :param target_path: Path to the codebase or shard to analyze.
        :return: A dictionary of findings in the VPOC internal schema.
        :raises ToolError: On any tool execution failure.
        """

    def __repr__(self) -> str:
        return f"<AsyncTool(name='{self.name}')>"


class ContainerTool(AsyncTool):
    """Base for tools that run inside a Docker container.

    Used primarily for static analysis tools (Semgrep, CodeQL, Joern).
    Mounts the source directory read-only. Does not apply sandbox hardening.
    """

    def __init__(self, name: str, image: str, command_template: str) -> None:
        super().__init__(name)
        self.image = image
        self.command_template = command_template
        self._client = docker.from_env()

    async def run_async(
        self, target_path: str, **kwargs: typing.Any
    ) -> typing.Dict[str, typing.Any]:
        """
        Executes the tool via docker-py.
        """
        # Ensure target_path is absolute for mounting
        abs_target = str(Path(target_path).resolve())

        # Format the command if needed (e.g. for sharding or specific targets)
        command = self.command_template

        logger.info("Running container tool %s with image %s", self.name, self.image)

        try:
            # Run the container synchronously in a thread pool to not block asyncio
            container_output = await asyncio.to_thread(
                self._client.containers.run,
                image=self.image,
                command=command,
                volumes={abs_target: {"bind": "/src", "mode": "ro"}},
                remove=True,
                stderr=True,
            )
            # This is a basic capture; specific tools (like SemgrepTool) 
            # should override this to parse actual output files.
            return {"tool": self.name, "raw_output": container_output.decode()}

        except docker.errors.ContainerError as e:
            logger.error("Container tool %s failed: %s", self.name, e.stderr)
            raise ToolError(
                tool_name=self.name,
                error_type=ToolErrorType.RUNTIME_ERROR,
                stderr_tail=e.stderr.decode()[-500:]
            )
        except Exception as e:
            logger.exception("Unexpected error running container tool %s: %s", self.name, e)
            raise ToolError(
                tool_name=self.name,
                error_type=ToolErrorType.RUNTIME_ERROR,
                stderr_tail=str(e)
            )
