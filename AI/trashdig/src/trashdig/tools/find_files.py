import fnmatch
import os

from trashdig.config import WorkspacePathError, get_config, resolve_workspace_path
from trashdig.sandbox.landlock_tool import landlock_tool

from .gitignore import HierarchicalGitIgnore


def _collect_recursive(
    target_dir: str,
    workspace_root: str,
    pattern: str,
    case_sensitive: bool,
    resolver: HierarchicalGitIgnore,
) -> list[str]:
    matches: list[str] = []
    for root, dirs, files in os.walk(target_dir):
        rel_root = os.path.relpath(root, workspace_root).replace(os.sep, "/")
        if rel_root == ".":
            rel_root = ""

        allowed_dirs: list[str] = []
        for d in dirs:
            rel_dir = f"{rel_root}/{d}" if rel_root else d
            if not resolver.is_ignored(rel_dir, is_dir=True):
                allowed_dirs.append(d)
        dirs[:] = allowed_dirs

        for filename in files:
            rel_file = f"{rel_root}/{filename}" if rel_root else filename
            if resolver.is_ignored(rel_file, is_dir=False):
                continue
            full_path = os.path.join(root, filename)
            rel_from_target = os.path.relpath(full_path, target_dir)

            # If pattern contains a path separator, match against the full relative path,
            # otherwise match against just the filename
            match_target = rel_from_target if "/" in pattern.replace(os.sep, "/") else filename

            check_name = match_target if case_sensitive else match_target.lower()
            if fnmatch.fnmatch(check_name, pattern):
                matches.append(rel_from_target)

    return matches


def _collect_flat(
    target_dir: str,
    workspace_root: str,
    pattern: str,
    case_sensitive: bool,
    resolver: HierarchicalGitIgnore,
) -> list[str]:
    matches: list[str] = []
    rel_target = os.path.relpath(target_dir, workspace_root).replace(os.sep, "/")
    if rel_target == ".":
        rel_target = ""
    for filename in os.listdir(target_dir):
        full_path = os.path.join(target_dir, filename)
        if os.path.isfile(full_path):
            rel_file = f"{rel_target}/{filename}" if rel_target else filename
            if not resolver.is_ignored(rel_file, is_dir=False):
                check_name = filename if case_sensitive else filename.lower()
                if fnmatch.fnmatch(check_name, pattern):
                    matches.append(filename)
    return matches


def _collect_matching_paths(
    target_dir: str,
    workspace_root: str,
    pattern: str,
    recursive: bool,
    case_sensitive: bool,
) -> list[str]:
    resolver = HierarchicalGitIgnore(workspace_root=workspace_root)
    if recursive:
        return _collect_recursive(target_dir, workspace_root, pattern, case_sensitive, resolver)
    return _collect_flat(target_dir, workspace_root, pattern, case_sensitive, resolver)


@landlock_tool()
def find_files(
    pattern: str,
    directory: str | None = None,
    recursive: bool = True,
    case_sensitive: bool = False,
) -> str:
    """Finds files by name pattern in a given directory.

    Args:
        pattern: The file name pattern to search for (e.g., '*.py').
        directory: The root directory to start the search. Defaults to Config workspace_root.
        recursive: Whether to search subdirectories.
        case_sensitive: Whether the pattern matching should be case-sensitive.

    Returns:
        A newline-separated list of relative paths for matching files.
    """
    cfg = get_config()
    workspace_root = cfg.workspace_root
    try:
        target_dir = resolve_workspace_path(directory)
    except WorkspacePathError as e:
        return f"Error: {e}"

    if not case_sensitive:
        pattern = pattern.lower()

    try:
        matches = _collect_matching_paths(
            target_dir, workspace_root, pattern, recursive, case_sensitive
        )
        return "\n".join(sorted(matches))
    except Exception as e:
        return f"Error searching in {directory}: {e}"
