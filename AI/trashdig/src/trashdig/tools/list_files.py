import os
import time

from trashdig.config import WorkspacePathError, get_config, resolve_workspace_path
from trashdig.sandbox.landlock_tool import landlock_tool

from .gitignore import HierarchicalGitIgnore


@landlock_tool()
def _format_entry(full_path: str, rel_display: str, is_dir: bool) -> str:
    stat = os.stat(full_path)
    mtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime))
    size = "-" if is_dir else stat.st_size
    type_char = "D" if is_dir else "F"
    return f"{type_char} {size:>10} {mtime} {rel_display}"


def _list_recursive(
    target_dir: str, workspace_root: str, resolver: HierarchicalGitIgnore
) -> str:
    output: list[str] = []
    for root, dirs, filenames in os.walk(target_dir):
        rel_root = os.path.relpath(root, workspace_root).replace(os.sep, "/")
        if rel_root == ".":
            rel_root = ""

        allowed_dirs: list[str] = []
        for d in dirs:
            rel_dir = f"{rel_root}/{d}" if rel_root else d
            if not resolver.is_ignored(rel_dir, is_dir=True):
                allowed_dirs.append(d)
                full_d = os.path.join(root, d)
                rel_from_target = os.path.relpath(full_d, target_dir)
                output.append(_format_entry(full_d, rel_from_target, is_dir=True))
        dirs[:] = allowed_dirs

        for f in filenames:
            rel_file = f"{rel_root}/{f}" if rel_root else f
            if not resolver.is_ignored(rel_file, is_dir=False):
                full_f = os.path.join(root, f)
                rel_from_target = os.path.relpath(full_f, target_dir)
                output.append(_format_entry(full_f, rel_from_target, is_dir=False))
    return "\n".join(output)


def _list_flat(
    target_dir: str, workspace_root: str, resolver: HierarchicalGitIgnore
) -> str:
    output: list[str] = []
    rel_target = os.path.relpath(target_dir, workspace_root).replace(os.sep, "/")
    if rel_target == ".":
        rel_target = ""

    for item in sorted(os.listdir(target_dir)):
        full_path = os.path.join(target_dir, item)
        is_dir = os.path.isdir(full_path)
        rel_item = f"{rel_target}/{item}" if rel_target else item
        if not resolver.is_ignored(rel_item, is_dir=is_dir):
            output.append(_format_entry(full_path, item, is_dir=is_dir))
    return "\n".join(output)


@landlock_tool()
def list_files(directory: str | None = None, recursive: bool = False) -> str:
    """Lists files and directories in a given path.

    Args:
        directory: The directory to list. Defaults to Config workspace_root.
        recursive: Whether to list files recursively.

    Returns:
        A formatted string containing file names, sizes, and modification times.
    """
    cfg = get_config()
    workspace_root = cfg.workspace_root
    try:
        target_dir = resolve_workspace_path(directory)
    except WorkspacePathError as e:
        return f"Error: {e}"

    resolver = HierarchicalGitIgnore(workspace_root=workspace_root)

    try:
        if recursive:
            return _list_recursive(target_dir, workspace_root, resolver)
        return _list_flat(target_dir, workspace_root, resolver)
    except Exception as e:
        return f"Error listing directory {directory}: {e}"



