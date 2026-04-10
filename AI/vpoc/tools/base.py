import abc
import typing


class AsyncTool(abc.ABC):
    """Base class for all VPOC tools supporting asynchronous parallel execution."""

    def __init__(self, name: str):
        self.name = name
        self.supports_sharding = False

    @abc.abstractmethod
    async def run_async(
        self, target_path: str, **kwargs
    ) -> typing.Dict[str, typing.Any]:
        """
        Executes the tool asynchronously.

        :param target_path: Path to the codebase or shard to analyze.
        :return: A dictionary of findings in the internal VPOC schema.
        """
        pass

    def __repr__(self):
        return f"<AsyncTool(name='{self.name}')>"
