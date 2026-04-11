import abc
import enum
import typing


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
