import inspect
from typing import Any, Callable, Dict, List, Optional
from functools import wraps
from google.adk.tools import FunctionTool
from trashdig.config import Config, get_config

class PermissionManager:
    """Manages tool call permissions based on configuration and user confirmation.

    This class provides a way to intercept tool calls made by agents and verify
    them against defined policies or ask for user confirmation.
    """

    def __init__(
        self, 
        config: Optional[Config] = None, 
        on_confirm: Optional[Callable[[str, Dict[str, Any]], bool]] = None
    ):
        """Initializes the PermissionManager.

        Args:
            config: The configuration object. Defaults to the global config.
            on_confirm: A callback function that takes the tool name and arguments
                and returns a boolean indicating whether the tool call is allowed.
        """
        self.config = config or get_config()
        self.on_confirm = on_confirm
        # Tools that are always considered sensitive and require confirmation if a callback is provided.
        self.sensitive_tools = {"bash_tool", "container_bash_tool"}

    def is_allowed(self, tool_name: str, args: Dict[str, Any]) -> bool:
        """Checks if a tool call is allowed.

        Args:
            tool_name: The name of the tool.
            args: The arguments passed to the tool.

        Returns:
            True if allowed, False otherwise.
        """
        # 1. Check global policies
        # (Placeholder for future policy checks based on self.config)
        
        # 2. Check for sensitive tools and user confirmation
        if tool_name in self.sensitive_tools:
            if self.on_confirm:
                return self.on_confirm(tool_name, args)
        
        return True

    def wrap_tool(self, tool: FunctionTool) -> FunctionTool:
        """Wraps a FunctionTool to intercept calls for permission checks.

        Args:
            tool: The tool to wrap.

        Returns:
            A new FunctionTool with permission checks.
        """
        original_func = tool.func
        tool_name = tool.name or original_func.__name__

        if inspect.iscoroutinefunction(original_func):
            @wraps(original_func)
            async def wrapped(*args, **kwargs):
                sig = inspect.signature(original_func)
                try:
                    bound = sig.bind(*args, **kwargs)
                    bound.apply_defaults()
                    tool_args = bound.arguments
                except TypeError:
                    tool_args = kwargs

                if not self.is_allowed(tool_name, tool_args):
                    return f"Permission denied for tool: {tool_name}"
                return await original_func(*args, **kwargs)
        else:
            @wraps(original_func)
            def wrapped(*args, **kwargs):
                sig = inspect.signature(original_func)
                try:
                    bound = sig.bind(*args, **kwargs)
                    bound.apply_defaults()
                    tool_args = bound.arguments
                except TypeError:
                    tool_args = kwargs

                if not self.is_allowed(tool_name, tool_args):
                    return f"Permission denied for tool: {tool_name}"
                return original_func(*args, **kwargs)

        return FunctionTool(
            func=wrapped
        )

    def wrap_tools(self, tools: List[FunctionTool]) -> List[FunctionTool]:
        """Wraps a list of tools.

        Args:
            tools: List of FunctionTools.

        Returns:
            List of wrapped FunctionTools.
        """
        return [self.wrap_tool(t) for t in tools]

    def tool_decorator(self, func: Callable) -> Callable:
        """A decorator that can be applied directly to tool functions.
        
        Args:
            func: The function to decorate.
            
        Returns:
            The wrapped function.
        """
        tool_name = func.__name__

        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def wrapped(*args, **kwargs):
                sig = inspect.signature(func)
                try:
                    bound = sig.bind(*args, **kwargs)
                    bound.apply_defaults()
                    tool_args = bound.arguments
                except TypeError:
                    tool_args = kwargs

                if not self.is_allowed(tool_name, tool_args):
                    return f"Permission denied for tool: {tool_name}"
                return await func(*args, **kwargs)
        else:
            @wraps(func)
            def wrapped(*args, **kwargs):
                sig = inspect.signature(func)
                try:
                    bound = sig.bind(*args, **kwargs)
                    bound.apply_defaults()
                    tool_args = bound.arguments
                except TypeError:
                    tool_args = kwargs

                if not self.is_allowed(tool_name, tool_args):
                    return f"Permission denied for tool: {tool_name}"
                return func(*args, **kwargs)
        
        return wrapped
