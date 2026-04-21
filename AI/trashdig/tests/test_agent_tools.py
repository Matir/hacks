"""Tests verifying that each agent is built with the correct set of tools.

Overview
--------
Every agent in TrashDig is assembled by a ``create_*_agent`` factory that
passes a concrete ``tools`` list to ``LlmAgent.__init__``. This file verifies
that list for every agent in two complementary directions:

    test_has_tools
        All tools listed in ``EXPECTED_TOOLS`` are actually attached.

    test_no_unexpected_tools
        No registered custom tool is attached unless it is listed in
        ``EXPECTED_TOOLS`` (bidirectional coverage, no explicit deny list
        required).

Two additional meta-tests use ``pkgutil.iter_modules`` to keep the registry
and coverage declarations in sync with the actual source tree:

    TestAllToolsRegistered
        Uses ``iter_tool_callables()`` from ``agent_test_utils`` to check that
        every tool callable defined in ``trashdig.tools`` submodules is present
        in ``ALL_TOOLS``, and that every name in ``ALL_TOOLS`` resolves to an
        attribute of the package.

    TestAllAgentsHaveToolTests
        Uses ``iter_agent_factories()`` from ``agent_test_utils`` to check that
        every ``create_*_agent`` function defined in ``trashdig.agents``
        submodules has a corresponding ``Test<Agent>Tools`` class in this
        module that inherits from ``AgentToolsMixin``.

How the per-agent machinery works
----------------------------------
``_capture_tools`` runs the factory under three patches:

* ``load_prompt`` → returns a dummy string so no filesystem I/O is needed.
* ``google_provider_extras`` → returns a stub that disables the optional
  Google Search tool so it never appears in the captured list.
* ``LlmAgent.__init__`` → replaced with a ``side_effect`` that records its
  keyword arguments and returns immediately.  This gives us the raw ``tools``
  list the factory would have passed to the real constructor.

``_is_trashdig_tool`` walks the tool object's attributes to recover the
original Python callable and checks its ``__module__``.  This lets
``test_no_unexpected_tools`` distinguish between our own tools (which must be
registered in ``ALL_TOOLS``) and third-party ADK tools (which are ignored).

The mixin pattern
-----------------
``AgentToolsMixin`` is a *plain* class — it does **not** inherit from
``unittest.TestCase``.  Pytest collects all ``TestCase`` subclasses regardless
of their name, so a ``TestCase``-inheriting base would appear as a spurious
target.  A plain mixin avoids that: pytest only collects it when it appears in
an MRO whose outermost class starts with ``Test``.

Because the mixin calls ``assertIn``, ``subTest``, and ``fail`` (all from
``TestCase``), two ``Protocol`` classes bridge the type-checker gap:

* ``_TestCaseProto``  — describes just the three ``TestCase`` methods used.
* ``_MixinSelfProto`` — extends ``_TestCaseProto`` with the mixin's own
  attributes so method bodies can be fully type-checked without inheriting
  from ``TestCase``.

Concrete test classes use ``class TestFooTools(AgentToolsMixin, unittest.TestCase)``
and declare ``MODULE``, ``FACTORY``, and ``EXPECTED_TOOLS``.  The ``subTest``
loop reports each failing tool individually rather than stopping at the first.

How to extend this file
-----------------------
**Adding a new tool** (``trashdig/tools/new_tool.py``):
  1. Add the function name to ``ALL_TOOLS``.
  2. Add it to ``EXPECTED_TOOLS`` in every agent class that should receive it.
  The meta-test ``TestAllToolsRegistered`` will fail if step 1 is skipped.

**Adding a new agent** (``trashdig/agents/new_agent.py``):
  1. Create ``class TestNewAgentTools(AgentToolsMixin, unittest.TestCase)``
     following the pattern of the existing concrete classes below.
  2. Set ``MODULE`` to the dotted path of the agent module
     (e.g. ``"trashdig.agents.new_agent"``).
  3. Set ``FACTORY`` to the ``create_new_agent`` function.
  4. List every tool the agent should receive in ``EXPECTED_TOOLS``.
  The meta-test ``TestAllAgentsHaveToolTests`` will fail if step 1 is skipped.

**Modifying an agent's tool list**:
  Update that agent's ``EXPECTED_TOOLS`` list.  The two test methods will catch
  both missing tools and newly attached tools that were not declared.
"""

import sys
import unittest
from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Protocol
from unittest.mock import patch

from agent_test_utils import iter_agent_factories, iter_tool_callables

import trashdig.tools
from trashdig.agents.code_investigator import create_code_investigator_agent
from trashdig.agents.hunter import create_hunter_agent
from trashdig.agents.recon import create_stack_scout_agent, create_web_route_mapper_agent
from trashdig.agents.skeptic import create_skeptic_agent
from trashdig.agents.validator import create_validator_agent
from trashdig.config import AgentConfig

_PROVIDER_STUB = {"google_search_tool": None, "generate_content_config": None}

# ---------------------------------------------------------------------------
# Global tool registry
#
# ALL_TOOLS is the authoritative set of every callable tool defined in the
# trashdig.tools package that can legitimately be attached to an agent.
# It intentionally excludes internal helpers exported from the same package
# that are not agent tools (artifact_tool, get_artifact_service,
# init_artifact_manager).  Those exceptions are declared in
# _TOOLS_PKG_NON_TOOLS below so that TestAllToolsRegistered can enforce the
# distinction automatically.
#
# The set drives two distinct checks in test_no_unexpected_tools:
#
#   Rule 1 — unregistered custom tool
#       An agent has a tool whose underlying function lives in the trashdig
#       package (detected via __module__) but whose name is absent from
#       ALL_TOOLS. This catches new tool modules that were wired into an
#       agent before being added to this registry.
#
#   Rule 2 — unexpected tool
#       An agent has a tool whose name appears in ALL_TOOLS but that is not
#       listed in the concrete class's EXPECTED_TOOLS. Combined with the
#       existing test_has_tools check, this makes tool coverage bidirectional:
#       every expected tool must be present, and no registered tool may be
#       present unless it is expected.
#
# Because both rules apply only to registered custom tools, third-party tools
# (e.g. ADK's load_artifacts_tool) are intentionally ignored.
# ---------------------------------------------------------------------------

ALL_TOOLS: frozenset[str] = frozenset({
    "bash_tool",
    "container_bash_tool",
    "detect_frameworks",
    "detect_language",
    "exit_loop",
    "find_files",
    "find_references",
    "get_ast_summary",
    "get_next_hypothesis",
    "get_project_structure",
    "get_scope_info",
    "get_symbol_definition",
    "list_files",
    "query_cwe_database",
    "read_file",
    "ripgrep_search",
    "save_findings",
    "save_hypotheses",
    "semgrep_scan",
    "trace_taint_cross_file",
    "trace_variable",
    "trace_variable_semantic",
    "update_hypothesis_status",
    "web_fetch",
})


def _get_tool_name(tool: object) -> str | None:
    """Returns the tool's name, or None if it cannot be determined."""
    if hasattr(tool, "name") and isinstance(tool.name, str):
        return tool.name
    if callable(tool) and hasattr(tool, "__name__"):
        return tool.__name__
    return None


def _get_tool_func(tool: object) -> Callable | None:
    """Extracts the underlying callable from an ADK tool object.

    FunctionTool stores the wrapped function under various private attribute
    names depending on the ADK version. We probe a small set of candidates so
    that the test does not depend on ADK internals beyond what is observable.
    """
    for attr in ("func", "_func", "_raw_tool"):
        candidate = getattr(tool, attr, None)
        if callable(candidate):
            return candidate  # type: ignore[return-value]
    # functools.wraps copies __wrapped__; handle bare decorated callables too
    wrapped = getattr(tool, "__wrapped__", None)
    if callable(wrapped):
        return wrapped  # type: ignore[return-value]
    if callable(tool):
        return tool  # type: ignore[return-value]
    return None


def _is_trashdig_tool(tool: object) -> bool:
    """Returns True if the tool's underlying function is from the trashdig package."""
    func = _get_tool_func(tool)
    module: str = getattr(func, "__module__", "") or ""
    return module.startswith("trashdig.")


def _capture_tools(module_path: str, create_fn: Callable, **kwargs: object) -> list:
    """Calls a create_*_agent factory and returns the raw tool list that
    would be passed to LlmAgent.__init__."""
    captured: dict = {}

    def fake_init(*args: object, **kw: object) -> None:
        captured.update(kw)

    with (
        patch(f"{module_path}.load_prompt", return_value="instruction"),
        patch(f"{module_path}.google_provider_extras", return_value=_PROVIDER_STUB),
        patch("google.adk.agents.LlmAgent.__init__", side_effect=fake_init),
    ):
        create_fn(**kwargs)

    return captured.get("tools", [])


# ---------------------------------------------------------------------------
# Mixin design
#
# AgentToolsMixin is a plain class — it does NOT inherit from unittest.TestCase.
# This is deliberate: pytest collects all unittest.TestCase subclasses
# regardless of their name, so any base class that inherits from TestCase will
# appear as a spurious test target. A plain mixin avoids that entirely; pytest
# only runs it when it appears in an MRO whose outermost class starts with
# "Test".
#
# The mixin's test methods call assertIn and subTest, which live on
# unittest.TestCase. To keep the type checker happy without inheriting from
# TestCase, we declare two Protocols:
#
#   _TestCaseProto  — describes just the TestCase methods we rely on.
#   _MixinSelfProto — extends _TestCaseProto with the mixin's own attributes
#                     and _get_raw_tools(), so that type-checking a method
#                     body sees both sides of the combined interface.
#
# Each test method on the mixin annotates its `self` parameter as
# _MixinSelfProto. Concrete test classes (e.g. TestSkepticTools) inherit from
# both AgentToolsMixin and unittest.TestCase, making them structurally
# compatible with the protocol. The mixin itself is never instantiated directly.
# ---------------------------------------------------------------------------

class _TestCaseProto(Protocol):
    """The unittest.TestCase methods that AgentToolsMixin relies on."""

    def subTest(self, msg: object = ..., **params: object) -> AbstractContextManager[None]: ...  # noqa: N802
    def assertIn(self, member: object, container: object, msg: object = ...) -> None: ...  # noqa: N802
    def fail(self, msg: object = ...) -> None: ...


class _MixinSelfProto(_TestCaseProto, Protocol):
    """Full interface expected on ``self`` inside AgentToolsMixin methods.

    Combines the TestCase helpers with the mixin's own attributes so the type
    checker can validate method bodies without requiring TestCase inheritance.
    """

    EXPECTED_TOOLS: list[str]

    def _get_raw_tools(self) -> list: ...


class AgentToolsMixin:
    """Mixin that contributes test_has_tools and test_no_unexpected_tools.

    Concrete subclasses must also inherit from unittest.TestCase and declare:
        MODULE         -- dotted import path of the agent module (for patching)
        FACTORY        -- the create_*_agent factory function
        EXPECTED_TOOLS -- tool names that must be present (and only these
                          custom tools may be present; see ALL_TOOLS)
    """

    MODULE: str = ""
    FACTORY: Callable | None = None
    EXPECTED_TOOLS: list[str] = []

    def _get_raw_tools(self) -> list:
        # Access FACTORY via type() to avoid Python's descriptor protocol
        # turning the class-level function into a bound method.
        factory = type(self).FACTORY
        if factory is None:
            return []
        config = AgentConfig(model="test-model", provider="google")
        return _capture_tools(self.MODULE, factory, config=config)

    def test_has_tools(self: _MixinSelfProto) -> None:
        """Every name in EXPECTED_TOOLS must appear in the agent's tool list."""
        attached = {_get_tool_name(t) for t in self._get_raw_tools()}
        for tool in self.EXPECTED_TOOLS:
            with self.subTest(tool=tool):
                self.assertIn(tool, attached)

    def test_no_unexpected_tools(self: _MixinSelfProto) -> None:
        """Enforce both rules from the ALL_TOOLS registry.

        Rule 1 — unregistered custom tool: any tool whose function lives in
        the trashdig package must appear in ALL_TOOLS. This catches new tools
        wired into an agent before being registered in the global set.

        Rule 2 — unexpected tool: any tool that is in ALL_TOOLS must also be
        in EXPECTED_TOOLS for this agent. This makes the expected-tool check
        bidirectional — no registered tool may appear silently.
        """
        expected = set(self.EXPECTED_TOOLS)
        for tool_obj in self._get_raw_tools():
            name = _get_tool_name(tool_obj)
            if name is None:
                continue
            with self.subTest(tool=name):
                if _is_trashdig_tool(tool_obj) and name not in ALL_TOOLS:
                    self.fail(
                        f"{name!r} is from the trashdig package but is not "
                        f"registered in ALL_TOOLS"
                    )
                if name in ALL_TOOLS and name not in expected:
                    self.fail(
                        f"{name!r} is attached to this agent but is not "
                        f"listed in EXPECTED_TOOLS"
                    )


# ---------------------------------------------------------------------------
# Per-agent test classes
# ---------------------------------------------------------------------------

class TestCodeInvestigatorTools(AgentToolsMixin, unittest.TestCase):
    """CodeInvestigator should have its technical investigation toolset."""

    MODULE = "trashdig.agents.code_investigator"
    FACTORY = create_code_investigator_agent
    EXPECTED_TOOLS = [
        "find_files",
        "find_references",
        "get_ast_summary",
        "get_project_structure",
        "get_scope_info",
        "get_symbol_definition",
        "list_files",
        "read_file",
        "ripgrep_search",
        "trace_taint_cross_file",
        "trace_variable_semantic",
    ]


class TestStackScoutTools(AgentToolsMixin, unittest.TestCase):
    """StackScout should have every tool listed in README under SS column."""

    MODULE = "trashdig.agents.recon"
    FACTORY = create_stack_scout_agent
    EXPECTED_TOOLS = [
        "detect_frameworks",
        "detect_language",
        "find_files",
        "find_references",
        "get_ast_summary",
        "get_project_structure",
        "get_scope_info",
        "list_files",
        "query_cwe_database",
        "ripgrep_search",
        "web_fetch",
    ]


class TestWebRouteMapperTools(AgentToolsMixin, unittest.TestCase):
    """WebRouteMapper should have the tools it needs to map attack surfaces."""

    MODULE = "trashdig.agents.recon"
    FACTORY = create_web_route_mapper_agent
    EXPECTED_TOOLS = [
        "find_files",
        "get_ast_summary",
        "get_project_structure",
        "list_files",
        "ripgrep_search",
    ]


class TestHunterTools(AgentToolsMixin, unittest.TestCase):
    """Hunter should have every tool listed in README under H column."""

    MODULE = "trashdig.agents.hunter"
    FACTORY = create_hunter_agent
    EXPECTED_TOOLS = [
        "detect_language",
        "find_files",
        "find_references",
        "get_ast_summary",
        "get_scope_info",
        "get_symbol_definition",
        "list_files",
        "query_cwe_database",
        "read_file",
        "ripgrep_search",
        "semgrep_scan",
        "trace_taint_cross_file",
        "trace_variable",
        "trace_variable_semantic",
        "web_fetch",
    ]


class TestSkepticTools(AgentToolsMixin, unittest.TestCase):
    """Skeptic should have tools listed in README under S column."""

    MODULE = "trashdig.agents.skeptic"
    FACTORY = create_skeptic_agent
    EXPECTED_TOOLS = [
        "find_files",
        "list_files",
        "read_file",
        "ripgrep_search",
        "web_fetch",
    ]


class TestValidatorTools(AgentToolsMixin, unittest.TestCase):
    """Validator should have tools listed in README under V column."""

    MODULE = "trashdig.agents.validator"
    FACTORY = create_validator_agent
    EXPECTED_TOOLS = [
        "bash_tool",
        "container_bash_tool",
        "find_files",
        "list_files",
        "read_file",
        "ripgrep_search",
        "web_fetch",
    ]


# ---------------------------------------------------------------------------
# Meta-tests: registry and coverage completeness
# ---------------------------------------------------------------------------

class TestAllToolsRegistered(unittest.TestCase):
    """Verify ALL_TOOLS stays in sync with the trashdig.tools package.

    Uses ``iter_tool_callables()`` from ``agent_test_utils`` to discover every
    tool function defined in ``trashdig.tools`` submodules, and checks that
    each is present in ``ALL_TOOLS``.  The reverse direction is also checked:
    every name in ``ALL_TOOLS`` must be an attribute of the package.

    When a new tool module is added to ``trashdig/tools/``, this test will fail
    until its function name is added to ``ALL_TOOLS``.
    """

    def test_no_tool_missing_from_registry(self) -> None:
        """Every callable defined in a trashdig.tools submodule must be in ALL_TOOLS."""
        for full_name, attr, _ in iter_tool_callables():
            module_name = full_name.rpartition(".")[2]
            with self.subTest(module=module_name, tool=attr):
                self.assertIn(
                    attr,
                    ALL_TOOLS,
                    f"{attr!r} is defined in {full_name} but not in ALL_TOOLS",
                )

    def test_no_registry_entry_without_tool(self) -> None:
        """Every name in ALL_TOOLS must be exported from trashdig.tools."""
        for name in sorted(ALL_TOOLS):
            with self.subTest(tool=name):
                self.assertTrue(
                    hasattr(trashdig.tools, name),
                    f"{name!r} is in ALL_TOOLS but not found in trashdig.tools",
                )


class TestAllAgentsHaveToolTests(unittest.TestCase):
    """Verify that every agent factory has a corresponding Test*Tools class.

    Uses ``iter_agent_factories()`` from ``agent_test_utils`` to discover every
    ``create_*_agent`` function defined in ``trashdig.agents`` submodules, and
    checks that each has a corresponding ``Test<Agent>Tools`` class in this
    test module that inherits from ``AgentToolsMixin``.

    The naming convention is:
        ``create_foo_bar_agent``  →  ``TestFooBarTools``
        (strip prefix/suffix, title-case each word, remove underscores)

    When a new agent factory is added, this test will fail until a matching
    test class is added to this file.
    """

    @staticmethod
    def _factory_to_test_class_name(factory_name: str) -> str:
        """Converts a create_*_agent name to the expected Test*Tools class name."""
        middle = factory_name[len("create_"):-len("_agent")]
        return "Test" + "".join(w.title() for w in middle.split("_")) + "Tools"

    def test_all_agent_factories_have_tool_tests(self) -> None:
        """Every create_*_agent function must have a Test*Tools class in this module."""
        this_module = sys.modules[__name__]

        for full_name, attr, _ in iter_agent_factories():
            expected_cls_name = self._factory_to_test_class_name(attr)
            with self.subTest(factory=attr):
                test_cls = getattr(this_module, expected_cls_name, None)
                self.assertIsNotNone(
                    test_cls,
                    f"No test class {expected_cls_name!r} found for {attr!r} "
                    f"in {full_name}",
                )
                self.assertTrue(
                    isinstance(test_cls, type)
                    and issubclass(test_cls, AgentToolsMixin),
                    f"{expected_cls_name!r} exists but does not inherit from "
                    f"AgentToolsMixin",
                )
