"""Utilities for enumerating trashdig agents and tools in tests.

These helpers use ``pkgutil.iter_modules`` to discover the live source tree so
that meta-tests can verify the tool registry and agent test coverage without
hard-coding module lists that would go stale.

Functions
---------
iter_tool_callables()
    Yields every callable *defined* (not merely imported) in a
    ``trashdig.tools`` submodule that is an agent-attachable tool.

iter_agent_factories()
    Yields every ``create_*_agent`` function *defined* in a
    ``trashdig.agents`` submodule.

Both generators filter by ``obj.__module__`` so that functions re-exported
from other modules are not counted twice.
"""

import importlib
import inspect
import pkgutil
from collections.abc import Callable, Iterator

import trashdig.agents
import trashdig.tools

# Callables exported from trashdig.tools that are infrastructure helpers rather
# than agent-attachable tools.  iter_tool_callables skips these so that
# ALL_TOOLS (in test_agent_tools.py) does not need to list them.
TOOLS_PKG_NON_TOOLS: frozenset[str] = frozenset({
    "artifact_tool",         # decorator applied to tool implementations
    "get_artifact_service",  # runtime singleton accessor
    "init_artifact_manager", # one-time initialisation helper
})


def iter_tool_callables() -> Iterator[tuple[str, str, Callable[..., object]]]:
    """Yield ``(full_module_name, attr_name, callable)`` for every tool function
    defined in a ``trashdig.tools`` submodule.

    Filters applied:
    - Private names (starting with ``_``) are skipped.
    - Objects whose ``__module__`` differs from the submodule are skipped
      (they are imported, not defined here).
    - Names listed in ``TOOLS_PKG_NON_TOOLS`` are skipped.

    Yields:
        A 3-tuple of the fully-qualified module name, the attribute name, and
        the callable object itself.
    """
    for _, module_name, _ in pkgutil.iter_modules(trashdig.tools.__path__):
        full_name = f"trashdig.tools.{module_name}"
        module = importlib.import_module(full_name)
        for attr, obj in inspect.getmembers(module, callable):
            if attr.startswith("_"):
                continue
            if getattr(obj, "__module__", "") != full_name:
                continue
            if attr in TOOLS_PKG_NON_TOOLS:
                continue
            yield full_name, attr, obj


def iter_agent_factories() -> Iterator[tuple[str, str, Callable[..., object]]]:
    """Yield ``(full_module_name, factory_name, factory_fn)`` for every
    ``create_*_agent`` function defined in a ``trashdig.agents`` submodule.

    Filters applied:
    - Only functions whose name starts with ``create_`` and ends with
      ``_agent`` are yielded.
    - Functions whose ``__module__`` differs from the submodule are skipped
      (they are re-exported, not defined here).

    Yields:
        A 3-tuple of the fully-qualified module name, the factory function
        name, and the factory callable itself.
    """
    for _, module_name, _ in pkgutil.iter_modules(trashdig.agents.__path__):
        full_name = f"trashdig.agents.{module_name}"
        module = importlib.import_module(full_name)
        for attr, obj in inspect.getmembers(module, inspect.isfunction):
            if not (attr.startswith("create_") and attr.endswith("_agent")):
                continue
            if getattr(obj, "__module__", "") != full_name:
                continue
            yield full_name, attr, obj
