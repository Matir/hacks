import os
import time
from typing import Optional

def list_files(directory: str = ".", recursive: bool = False) -> str:
    """Lists files and directories in a given path.

    Args:
        directory: The directory to list.
        recursive: Whether to list files recursively.

    Returns:
        A formatted string containing file names, sizes, and modification times.
    """
    try:
        if recursive:
            output = []
            for root, dirs, files in os.walk(directory):
                for name in dirs + files:
                    full_path = os.path.join(root, name)
                    rel_path = os.path.relpath(full_path, directory)
                    stat = os.stat(full_path)
                    mtime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat.st_mtime))
                    size = stat.st_size if os.path.isfile(full_path) else "-"
                    type_char = "D" if os.path.isdir(full_path) else "F"
                    output.append(f"{type_char} {size:>10} {mtime} {rel_path}")
            return "\n".join(output)
        else:
            items = os.listdir(directory)
            output = []
            for item in sorted(items):
                full_path = os.path.join(directory, item)
                stat = os.stat(full_path)
                mtime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat.st_mtime))
                size = stat.st_size if os.path.isfile(full_path) else "-"
                type_char = "D" if os.path.isdir(full_path) else "F"
                output.append(f"{type_char} {size:>10} {mtime} {item}")
            return "\n".join(output)
    except Exception as e:
        return f"Error listing directory {directory}: {e}"
