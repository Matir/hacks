"""Environment diagnostics for TrashDig."""

import sys
from dataclasses import dataclass

from trashdig.config import Config
from trashdig.metadata.languages import get_ts_language
from trashdig.utils import get_binary_path


@dataclass
class DiagnosticResult:
    """Result of a single diagnostic check."""
    name: str
    status: bool  # True for OK, False for Error/Warning
    message: str
    is_critical: bool = False  # If True, failure prevents startup when require_sandbox=True


def check_tree_sitter() -> list[DiagnosticResult]:
    """Verifies tree-sitter and grammars."""
    results = []

    # Check core
    try:
        import tree_sitter  # noqa: F401, PLC0415
        results.append(DiagnosticResult("Tree-sitter core", True, "Installed"))
    except ImportError:
        results.append(DiagnosticResult("Tree-sitter core", False, "Not installed", True))
        return results

    # Check grammars
    grammars = ["python", "go", "javascript", "csharp"]
    missing = []
    for lang in grammars:
        if get_ts_language(lang) is None:
            missing.append(lang)

    if missing:
        results.append(DiagnosticResult(
            "Tree-sitter grammars",
            False,
            f"Missing: {', '.join(missing)}",
            True
        ))
    else:
        results.append(DiagnosticResult("Tree-sitter grammars", True, "All supported grammars found"))

    return results


def check_sandboxes(config: Config) -> list[DiagnosticResult]:
    """Verifies availability of sandboxing mechanisms."""
    results = []

    # 1. OS-level Sandbox (Minijail / Bx)
    if sys.platform == "linux":
        path = get_binary_path("minijail0")
        if path:
            results.append(DiagnosticResult("Minijail sandbox", True, f"Found at {path}"))
        else:
            results.append(DiagnosticResult("Minijail sandbox", False, "minijail0 not found in PATH", True))
    elif sys.platform == "darwin":
        path = get_binary_path("bx")
        if path:
            results.append(DiagnosticResult("Bx sandbox (macOS)", True, f"Found at {path}"))
        else:
            results.append(DiagnosticResult("Bx sandbox (macOS)", False, "bx not found in PATH. Install via: brew install holtwick/tap/bx", True))
    else:
        results.append(DiagnosticResult("OS Sandbox", False, f"Not supported on {sys.platform}", True))

    # 2. Python-level Sandbox (Landlock)
    if sys.platform == "linux":
        try:
            from landlock import Ruleset  # noqa: PLC0415
            abi = Ruleset.get_abi()
            if abi > 0:
                results.append(DiagnosticResult("Landlock (Linux)", True, f"Available (ABI v{abi})"))
            else:
                results.append(DiagnosticResult("Landlock (Linux)", False, "Kernel does not support Landlock", True))
        except ImportError:
            results.append(DiagnosticResult("Landlock (Linux)", False, "landlock package not installed", True))
    else:
        results.append(DiagnosticResult("Landlock (Linux)", True, "N/A (Not on Linux)"))

    return results


def run_all_diagnostics(config: Config) -> list[DiagnosticResult]:
    """Runs all environment checks."""
    results = []
    results.extend(check_tree_sitter())
    results.extend(check_sandboxes(config))
    return results
