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
    parser.add_argument(
        "--config",
        help="Path to a project configuration TOML file",
    )
    args = parser.parse_args()

    workspace_root = os.path.abspath(args.root)
    if not os.path.isdir(workspace_root):
        parser.error(f"Not a directory: {workspace_root}")

    config = load_config(
        config_flag=args.config, 
        data_dir_flag=args.data_dir, 
        workspace_root=workspace_root
    )
    
    from trashdig.rate_limiter import init_rate_limiter
    from trashdig.tools import init_artifact_manager
    
    init_rate_limiter(rpm_limit=config.rpm_limit, tpm_limit=config.tpm_limit)
    init_artifact_manager(data_dir=config.data_dir)

    app = TrashDigApp(config=config, workspace_root=workspace_root)
    app.run()

if __name__ == "__main__":
    main()
