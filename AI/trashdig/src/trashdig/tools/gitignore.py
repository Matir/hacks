r"""Hierarchical multi-level .gitignore evaluation and workspace directory walker.

Supports nested .gitignore files at any level of the project tree, honoring:
- Git line syntax (whitespace-only lines and unescaped # comments ignored,
  escaped \\# literal comments preserved, unescaped trailing spaces stripped)
- Order-dependent rule evaluation and negation patterns (!)
- Parent directory exclusion blockades (negation rules cannot un-ignore files
  inside excluded parent directories)
- Middle-slash and leading-slash pattern anchoring relative to the defining
  .gitignore directory
- Discovery-time directory tree pruning for maximum I/O efficiency
"""

import os
from collections.abc import Iterable, Iterator
from dataclasses import dataclass

from pathspec import PathSpec

import trashdig.config


def sanitize_gitignore_lines(raw_lines: Iterable[str]) -> list[str]:
    r"""Sanitizes raw lines from a .gitignore file according to Git spec.

    - Drops lines that are empty or consist only of whitespace.
    - Drops comment lines starting with unescaped '#'.
    - Preserves literal '#' when escaped as '\\#'.
    - Strips unescaped trailing spaces.
    """
    sanitized: list[str] = []
    for raw in raw_lines:
        line = raw.rstrip("\r\n")
        if not line or line.isspace():
            continue

        lstripped = line.lstrip()
        if lstripped.startswith("#") and not lstripped.startswith(r"\#"):
            continue

        # Strip unescaped trailing whitespace per Git spec
        while line.endswith(" ") and not line.endswith(r"\ "):
            line = line[:-1]

        if not line or line.isspace():
            continue

        sanitized.append(line)
    return sanitized


@dataclass
class _CachedSpec:
    mtime: float
    spec: PathSpec | None


class HierarchicalGitIgnore:
    """Evaluates .gitignore rules across arbitrary hierarchy levels in a project."""

    def __init__(self, workspace_root: str | None = None) -> None:
        """Initializes resolver for the specified or default workspace root."""
        if workspace_root is None:
            workspace_root = trashdig.config.get_config().workspace_root
        self.workspace_root = os.path.abspath(workspace_root)
        self._cache: dict[str, _CachedSpec] = {}

    def _get_dir_spec(self, rel_dir: str) -> PathSpec | None:
        """Retrieves and caches the compiled PathSpec for a subdirectory's .gitignore."""
        abs_dir = (
            self.workspace_root
            if not rel_dir or rel_dir == "."
            else os.path.join(self.workspace_root, rel_dir)
        )
        gitignore_path = os.path.join(abs_dir, ".gitignore")

        if not os.path.exists(gitignore_path):
            self._cache[rel_dir] = _CachedSpec(mtime=0.0, spec=None)
            return None

        try:
            stat = os.stat(gitignore_path)
            cached = self._cache.get(rel_dir)
            if cached is not None and cached.mtime == stat.st_mtime:
                return cached.spec

            with open(gitignore_path, encoding="utf-8") as f:
                sanitized = sanitize_gitignore_lines(f.readlines())

            spec = PathSpec.from_lines("gitignore", sanitized) if sanitized else None
            self._cache[rel_dir] = _CachedSpec(mtime=stat.st_mtime, spec=spec)
            return spec
        except Exception:
            return None

    def _get_ancestor_dirs(self, target_rel_path: str) -> list[str]:
        """Returns ordered relative directory paths from workspace_root down to target's folder."""
        parts = [p for p in target_rel_path.replace(os.sep, "/").split("/") if p and p != "."]
        if not parts:
            return [""]
        # Exclude the last component if it's the target itself; include directories only
        ancestors = [""]
        current = ""
        for part in parts[:-1]:
            current = f"{current}/{part}" if current else part
            ancestors.append(current)
        return ancestors

    def _is_dir_excluded(self, dir_rel_path: str) -> bool:
        """Checks if a directory is excluded by applicable .gitignore files."""
        if not dir_rel_path or dir_rel_path == ".":
            return False

        parts = [p for p in dir_rel_path.replace(os.sep, "/").split("/") if p and p != "."]
        current_path = ""
        for part in parts:
            parent_dir = current_path
            current_path = f"{current_path}/{part}" if current_path else part
            if self._check_path_at_level(current_path, parent_dir, is_dir=True):
                return True
        return False

    def _check_path_at_level(self, rel_path: str, parent_dir: str, is_dir: bool = False) -> bool:
        """Evaluates rel_path against all .gitignore files from root down to parent_dir."""
        ancestors = self._get_ancestor_dirs(rel_path)
        status: bool | None = None

        for git_dir in ancestors:
            spec = self._get_dir_spec(git_dir)
            if spec is None:
                continue

            if not git_dir:
                rel_from_git = rel_path
            else:
                rel_from_git = os.path.relpath(rel_path, git_dir).replace(os.sep, "/")

            check_target = (
                f"{rel_from_git}/" if is_dir and not rel_from_git.endswith("/") else rel_from_git
            )
            res = spec.check_file(check_target)
            if res.include is True:
                status = True
            elif res.include is False:
                status = False

        return status is True

    def is_ignored(self, target_path: str, is_dir: bool = False) -> bool:
        """Determines whether target_path is ignored by any applicable .gitignore rule.

        Enforces Git parent-directory exclusion lockout: if a parent directory of target_path
        is excluded, target_path is automatically ignored regardless of sub-directory rules.
        """
        if os.path.isabs(target_path):
            try:
                rel_path = os.path.relpath(target_path, self.workspace_root)
            except ValueError:
                return False
        else:
            rel_path = target_path

        rel_path = rel_path.replace(os.sep, "/")
        if not rel_path or rel_path == ".":
            return False

        # First, check if any parent directory of this path is excluded
        parent_dir = os.path.dirname(rel_path).replace(os.sep, "/")
        if parent_dir and parent_dir != "." and self._is_dir_excluded(parent_dir):
            return True

        return self._check_path_at_level(rel_path, parent_dir, is_dir=is_dir)


def filter_by_gitignore(
    files: list[str] | set[str] | Iterable[str],
    workspace_root: str | None = None,
) -> list[str]:
    """Filters a collection of file paths against multi-level gitignore rules in the workspace.

    Args:
        files: A list or set of file paths (relative to workspace_root or absolute).
        workspace_root: The root directory containing the project. Defaults to Config workspace_root.

    Returns:
        A sorted list of file paths that are NOT ignored by any gitignore rules.
    """
    resolver = HierarchicalGitIgnore(workspace_root=workspace_root)
    filtered: list[str] = []
    for filepath in files:
        if not resolver.is_ignored(filepath, is_dir=False):
            filtered.append(filepath)
    return sorted(filtered)


def walk_workspace(
    workspace_root: str | None = None,
    include_dirs: bool = False,
    ignore_noisy: bool = False,
) -> Iterator[str]:
    """Yields relative file paths in workspace, pruning ignored directories early for performance."""
    cfg = trashdig.config.get_config()
    if workspace_root is None:
        workspace_root = cfg.workspace_root
    workspace_root = os.path.abspath(workspace_root)

    resolver = HierarchicalGitIgnore(workspace_root=workspace_root)
    noisy_dirs = cfg.noisy_dirs if ignore_noisy else set()

    for root, dirs, filenames in os.walk(workspace_root):
        rel_root = os.path.relpath(root, workspace_root).replace(os.sep, "/")
        if rel_root == ".":
            rel_root = ""

        # Early directory pruning: mutate dirs[:] in-place to avoid descending into ignored subtrees
        allowed_dirs: list[str] = []
        for d in dirs:
            if ignore_noisy and d in noisy_dirs:
                continue
            rel_dir = f"{rel_root}/{d}" if rel_root else d
            if not resolver.is_ignored(rel_dir, is_dir=True):
                allowed_dirs.append(d)
                if include_dirs:
                    yield rel_dir
        dirs[:] = allowed_dirs

        for f in filenames:
            rel_file = f"{rel_root}/{f}" if rel_root else f
            if not resolver.is_ignored(rel_file, is_dir=False):
                yield rel_file
