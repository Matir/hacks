import argparse
import asyncio
import dataclasses
import os
import sys
import traceback
import warnings
from typing import Any

import tomli_w
from rich.console import Console

from trashdig.agents.coordinator import Coordinator
from trashdig.config import load_config
from trashdig.sandbox.landlock_tool import init_sandbox_mp_context
from trashdig.services.rate_limiter import init_rate_limiter
from trashdig.services.session import init_session_service
from trashdig.tools import init_artifact_manager
from trashdig.tui.app import TrashDigApp

# Suppress experimental ADK feature warnings
warnings.filterwarnings("ignore", message=".*FeatureName.PLUGGABLE_AUTH.*")


def main() -> None:
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
    parser.add_argument(
        "--dump-config",
        action="store_true",
        help="Dump the loaded configuration as TOML and exit",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Run in batch mode (non-interactive, skip TUI)",
    )
    args = parser.parse_args()

    workspace_root = os.path.abspath(args.root)
    if not os.path.isdir(workspace_root):
        parser.error(f"Not a directory: {workspace_root}")

    config = load_config(
        config_flag=args.config, data_dir_flag=args.data_dir, workspace_root=workspace_root
    )

    # Initialise the forkserver start method before any threads are spawned.
    # This must happen after load_config() so the config singleton is inherited
    # by the forkserver process, and before asyncio.run() / app.run() which
    # create threads.
    init_sandbox_mp_context("forkserver")

    if args.dump_config:

        def filter_none(d: Any) -> Any:
            if isinstance(d, dict):
                return {k: filter_none(v) for k, v in d.items() if v is not None}
            elif isinstance(d, list):
                return [filter_none(v) for v in d if v is not None]
            else:
                return d

        config_dict = filter_none(dataclasses.asdict(config))
        print(tomli_w.dumps(config_dict))  # noqa: T201
        return

    init_rate_limiter(rpm_limit=config.rpm_limit, tpm_limit=config.tpm_limit)
    init_session_service(db_path=config.data_dir + "/trashdig.db")
    art_service = init_artifact_manager(data_dir=config.data_dir)

    # Automatic batch mode if not a TTY or explicitly requested
    is_batch = args.batch or not sys.stdout.isatty()

    if is_batch:
        console = Console()
        console.print("[bold blue]TrashDig:[/bold blue] running in batch mode...")

        coordinator = Coordinator(
            config, project_path=config.workspace_root, artifact_service=art_service
        )

        # Connect simple console logger
        coordinator.on_task_event = console.print
        coordinator.on_stats_event = lambda: None

        try:
            asyncio.run(coordinator.run_full_scan(config.workspace_root))
            console.print("\n[bold green]Scan Complete.[/bold green]")
            console.print(f"Total Findings: {len(coordinator.findings)}")
            console.print(f"Total Cost: ${coordinator.total_cost:.4f}")
        except Exception as e:
            console.print(f"[bold red]Error during scan:[/bold red] {e}")
            traceback.print_exc()
            sys.exit(1)
    else:
        app = TrashDigApp(config=config, workspace_root=config.workspace_root)
        app.run()


if __name__ == "__main__":
    main()
