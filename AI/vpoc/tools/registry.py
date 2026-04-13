import typing
from .base import AsyncTool
from .semgrep import SemgrepTool

class ToolRegistry:
    """Registry mapping languages to their appropriate tool instances."""

    def __init__(self) -> None:
        self._tools: typing.Dict[str, typing.List[AsyncTool]] = {
            "PHP": [],
            "C/C++": [],
            "Go": [],
            "Rust": [],
            "Lua": [],
        }

    def register_tool(self, language: str, tool: AsyncTool) -> None:
        """Adds a tool to the registry for a specific language."""
        if language in self._tools:
            self._tools[language].append(tool)
        else:
            self._tools[language] = [tool]

    def get_tools_for_languages(self, languages: typing.List[str]) -> typing.List[AsyncTool]:
        """Returns a deduplicated list of tools for the given languages."""
        tools = set()
        for lang in languages:
            if lang in self._tools:
                tools.update(self._tools[lang])
        return list(tools)

# Global registry instance
registry = ToolRegistry()

def initialize_registry() -> None:
    """Initializes the registry with standard tool instances."""

    # Semgrep (Multi-language)
    semgrep = SemgrepTool()

    registry.register_tool("PHP", semgrep)
    registry.register_tool("C/C++", semgrep)
    registry.register_tool("Go", semgrep)
    registry.register_tool("Rust", semgrep)
    registry.register_tool("Lua", semgrep)

    # TODO: Add more specialized tools (CodeQL, Joern, etc.)
