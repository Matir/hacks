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
    parser.add_argument(
        "--data-dir",
        help="Location for internal data (default: {workspace}/.trashdig)",
    )
    args = parser.parse_args()

    workspace_root = os.path.abspath(args.root)
    if not os.path.isdir(workspace_root):
        parser.error(f"Not a directory: {workspace_root}")

    config = load_config(data_dir=args.data_dir, workspace_root=workspace_root)
    
    from trashdig.rate_limiter import init_rate_limiter
    init_rate_limiter(rpm_limit=config.rpm_limit, tpm_limit=config.tpm_limit)

    app = TrashDigApp(config=config, workspace_root=workspace_root)
    app.run()

if __name__ == "__main__":
    main()
