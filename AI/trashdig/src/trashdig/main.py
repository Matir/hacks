import argparse
import os

from trashdig.tui.app import TrashDigApp
from trashdig.config import load_config

def main():
    """Main entry point for TrashDig."""
    parser = argparse.ArgumentParser(
        prog="trashdig",
        description="AI-powered vulnerability scanner",
    )
    parser.add_argument(
        "root",
        nargs="?",
        default=".",
        metavar="DIR",
        help="Workspace root directory to scan (default: current directory)",
    )
    args = parser.parse_args()

    workspace_root = os.path.abspath(args.root)
    if not os.path.isdir(workspace_root):
        parser.error(f"Not a directory: {workspace_root}")

    config = load_config()
    app = TrashDigApp(config=config, workspace_root=workspace_root)
    app.run()

if __name__ == "__main__":
    main()
