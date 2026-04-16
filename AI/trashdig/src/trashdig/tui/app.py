from __future__ import annotations
import os
import logging
import traceback
from typing import List, Dict, Any, Optional, TYPE_CHECKING, cast
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Tree, Static, Label, Input, RichLog
from textual.containers import Vertical, Horizontal
from textual.binding import Binding
from textual.events import Key
from textual_autocomplete import AutoComplete, DropdownItem

from trashdig.agents.coordinator import Coordinator
from trashdig.agents.utils import get_project_structure, log_auth_info
from trashdig.config import Config
from trashdig.findings import Finding


def _setup_file_logger(log_path: str) -> logging.Logger:
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    logger = logging.getLogger("trashdig")
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        handler = logging.FileHandler(log_path, encoding="utf-8")
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        )
        logger.addHandler(handler)
    return logger


class FileTree(Tree):
    """A tree representing the project file structure."""

    def __init__(self, label: str, data: Dict[str, Dict[str, Any]]):
        super().__init__(label)
        self.data = data

    def update_tree(self, root_path: str = ".", data: Optional[Dict[str, Dict[str, Any]]] = None) -> None:
        """Updates the tree with file structure and optional metadata."""
        self.clear()
        self.data = data or {}
        file_list = get_project_structure(root_path)

        nodes = {"": self.root}
        for path in file_list:
            parts = path.split(os.sep)
            for i in range(len(parts)):
                parent_path = os.sep.join(parts[:i])
                current_path = os.sep.join(parts[: i + 1])
                if current_path not in nodes:
                    parent_node = nodes[parent_path]
                    is_file = i == len(parts) - 1
                    label = parts[i]
                    if current_path in self.data and self.data[current_path].get(
                        "is_high_value"
                    ):
                        label = f"⭐ {label}"
                    if is_file:
                        nodes[current_path] = parent_node.add_leaf(
                            label, data=current_path
                        )
                    else:
                        nodes[current_path] = parent_node.add(label, data=current_path)
        self.root.expand()


class StatusPane(Vertical):
    """Displays a live summary of scan state."""

    DEFAULT_CSS = """
    StatusPane {
        height: auto;
        border-top: solid $accent;
        padding: 0 1;
    }
    StatusPane Label {
        text-style: bold;
        margin-bottom: 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("Status")
        yield Static("", id="status_body")

    def refresh_status(
        self,
        workspace_root: str,
        phase: str,
        tech_stack: str,
        scan_results: Dict[str, Any],
        prioritized_targets: List[str],
        findings: List[Finding],
        task_queue_len: int,
        completed_len: int,
        total_messages: int = 0,
        input_tokens: int = 0,
        output_tokens: int = 0,
        llm_errors: int = 0,
    ) -> None:
        high_value = sum(
            1
            for d in scan_results.values()
            if isinstance(d, dict) and d.get("is_high_value")
        )

        severity_counts: Dict[str, int] = {}
        for f in findings:
            sev = getattr(f, "severity", "Unknown") or "Unknown"
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        sev_parts = [f"{sev}: {n}" for sev, n in sorted(severity_counts.items())]
        sev_str = ", ".join(sev_parts) if sev_parts else "none"

        phase_color = {
            "Idle": "dim",
            "Scanning": "yellow",
            "Hunting": "cyan",
            "Verifying": "magenta",
        }.get(phase, "white")

        root_display = os.path.basename(workspace_root) or workspace_root

        def _fmt_tokens(n: int) -> str:
            return f"{n:,}" if n < 1_000_000 else f"{n/1_000_000:.1f}M"

        lines = [
            f"[bold]Phase:[/bold]    [{phase_color}]{phase}[/{phase_color}]",
            f"[bold]Root:[/bold]     {root_display}",
            f"[bold]Stack:[/bold]    {tech_stack or '—'}",
            f"[bold]Files:[/bold]    {len(scan_results)} ({high_value} high-value)",
            f"[bold]Targets:[/bold]  {len(prioritized_targets)} prioritized",
            f"[bold]Findings:[/bold] {len(findings)} ({sev_str})",
            f"[bold]Queue:[/bold]    {task_queue_len} pending / {completed_len} done",
            f"[bold]LLM Msgs:[/bold] {total_messages}",
            f"[bold]Tokens↑:[/bold]  {_fmt_tokens(input_tokens)}",
            f"[bold]Tokens↓:[/bold]  {_fmt_tokens(output_tokens)}",
            f"[bold]Errors:[/bold]   {'[red]' if llm_errors else ''}{llm_errors}{'[/red]' if llm_errors else ''}",
        ]
        self.query_one("#status_body", Static).update("\n".join(lines))


class REPLPane(Vertical):
    """A REPL-style interface with command history and autocompletion."""
    if TYPE_CHECKING:
        app: TrashDigApp

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.history: List[str] = []
        self.history_index: int = -1
        self.commands = ["help", "scan", "hunt", "star", "verify", "status", "exit"]

    def compose(self) -> ComposeResult:
        yield Label("Interactive Console")
        yield RichLog(id="repl_log", highlight=True, markup=True, wrap=True)
        yield AutoComplete(
            Input(
                placeholder="Type a command (e.g., 'scan api/', 'help')...",
                id="repl_input",
            ),
            candidates=[DropdownItem(cmd) for cmd in self.commands],
            id="repl_autocomplete",
        )

    def on_input_submitted(self, event: Input.Submitted) -> None:
        command = event.value.strip()
        if not command:
            return
        if not self.history or self.history[-1] != command:
            self.history.append(command)
        self.history_index = -1
        log = self.query_one("#repl_log", RichLog)
        log.write(f"> [bold cyan]{command}[/bold cyan]")
        event.input.value = ""
        self.run_worker(self.process_command(command, log))

    def on_key(self, event: Key) -> None:
        """Handle Up/Down arrows for command history."""
        if event.key == "up":
            if self.history:
                if self.history_index == -1:
                    self.history_index = len(self.history) - 1
                elif self.history_index > 0:
                    self.history_index -= 1
                input_widget = self.query_one("#repl_input", Input)
                input_widget.value = self.history[self.history_index]
                input_widget.cursor_position = len(input_widget.value)
                event.prevent_default()
        elif event.key == "down":
            if self.history:
                if self.history_index != -1:
                    if self.history_index < len(self.history) - 1:
                        self.history_index += 1
                        input_widget = self.query_one("#repl_input", Input)
                        input_widget.value = self.history[self.history_index]
                    else:
                        self.history_index = -1
                        self.query_one("#repl_input", Input).value = ""
                event.prevent_default()

    async def process_command(self, command: str, log: RichLog) -> None:
        cmd_parts = command.split()
        base_cmd = cmd_parts[0].lower() if cmd_parts else ""
        app = cast("TrashDigApp", self.app)

        if base_cmd == "help":
            log.write(
                "Available commands: [green]" + ", ".join(self.commands) + "[/green]"
            )
        elif base_cmd == "scan":
            path = cmd_parts[1] if len(cmd_parts) > 1 else app.workspace_root
            app.run_worker(app.run_recon_scan(path))
        elif base_cmd == "hunt":
            if not app.prioritized_targets:
                log.write("[red]No targets prioritized. Star some files first![/red]")
            else:
                app.run_worker(
                    app.run_hunter_analysis(app.prioritized_targets)
                )
        elif base_cmd == "verify":
            if not app.coordinator.findings:
                log.write("[red]No findings to verify. Run 'hunt' first![/red]")
            else:
                if len(cmd_parts) < 2:
                    log.write("[yellow]Verifying all findings...[/yellow]")
                    for finding in app.coordinator.findings:
                        app.run_worker(app.run_verification(finding))
                else:
                    try:
                        idx = int(cmd_parts[1]) - 1
                        finding = app.coordinator.findings[idx]
                        app.run_worker(app.run_verification(finding))
                    except (ValueError, IndexError):
                        log.write(f"[red]Invalid finding index: {cmd_parts[1]}[/red]")
        elif base_cmd == "star":
            if len(cmd_parts) < 2:
                log.write("[red]Usage: star <path>[/red]")
            else:
                path = os.path.normpath(cmd_parts[1])
                if path not in app.prioritized_targets:
                    app.prioritized_targets.append(path)
                    app._file_log.info("Starred: %s", path)
                    log.write(f"[green]Starred {path} for hunting.[/green]")
                    app.refresh_status()
                else:
                    log.write(f"[yellow]{path} is already starred.[/yellow]")
        elif base_cmd == "status":
            log.write(
                f"Prioritized targets: [cyan]{', '.join(app.prioritized_targets) or 'None'}[/cyan]"
            )
            app.refresh_status()
        elif base_cmd == "exit":
            await app.action_quit()
        else:
            log.write(f"[red]Unknown command: {base_cmd}[/red]")


class TrashDigApp(App):
    """The main TrashDig TUI application."""

    TITLE = "TrashDig"
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("f5", "scan", "Scan"),
        Binding("f6", "prioritize", "Prioritize"),
        Binding("ctrl+l", "clear_log", "Clear Log"),
    ]
    DEFAULT_CSS = """
    #sidebar {
        width: 30;
        min-width: 24;
    }
    FileTree {
        height: 1fr;
    }
    REPLPane {
        overflow-x: hidden;
    }
    #repl_log {
        overflow-x: hidden;
    }
    """

    def __init__(self, config: Optional[Config] = None, workspace_root: Optional[str] = None):
        super().__init__()
        self.config = config or Config()
        self.workspace_root = workspace_root or self.config.workspace_root
        self._phase = "Idle"
        log_path = self.config.resolve_data_path("trashdig.log")
        self._file_log = _setup_file_logger(log_path)
        self._file_log.info("Session started — workspace: %s", workspace_root)
        log_auth_info(self.config, self._file_log)
        
        from trashdig.tools import get_artifact_service
        art_service = get_artifact_service()
        
        self.coordinator = Coordinator(self.config, project_path=workspace_root, artifact_service=art_service)
        self.coordinator.on_task_event = lambda msg: self.call_from_thread(self._on_coordinator_log, msg)
        self.coordinator.on_stats_event = lambda: self.call_from_thread(self.refresh_status)
        self.prioritized_targets: List[str] = []

    def log_message(self, level: str, message: str) -> None:
        """Write to both the TUI console and the log file."""
        plain = message  # Rich markup stripped automatically by logger
        getattr(self._file_log, level)(plain)
        try:
            self.query_one("#repl_log", RichLog).write(message)
            self.refresh_status()
        except Exception:
            pass

    def _on_coordinator_log(self, message: str) -> None:
        self.log_message("info", message)

    def on_worker_state_changed(self, event: Any) -> None:
        """Catch worker failures and surface them in the console and log."""
        if isinstance(event.worker.error, Exception):
            err = event.worker.error
            tb = "".join(traceback.format_exception(type(err), err, err.__traceback__))
            self._file_log.error("Worker failed:\n%s", tb)
            try:
                log = self.query_one("#repl_log", RichLog)
                log.write(f"[bold red]Error:[/bold red] {err}")
            except Exception:
                pass
            self._phase = "Idle"
            self.refresh_status()

    def refresh_status(self) -> None:
        try:
            status_pane = self.query_one(StatusPane)
            status_pane.refresh_status(
                workspace_root=self.workspace_root,
                phase=self._phase,
                tech_stack=self.coordinator.tech_stack,
                scan_results=self.coordinator.scan_results,
                prioritized_targets=self.prioritized_targets,
                findings=self.coordinator.findings,
                task_queue_len=len(self.coordinator.task_queue),
                completed_len=len(self.coordinator.completed_tasks),
                total_messages=self.coordinator.total_messages,
                input_tokens=self.coordinator.input_tokens,
                output_tokens=self.coordinator.output_tokens,
                llm_errors=self.coordinator.llm_errors,
            )
        except Exception as e:
            if hasattr(self, "_file_log"):
                self._file_log.error("refresh_status error: %s", e)

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Label("Project Map")
                yield FileTree("Project Root", {})
                yield StatusPane()
            with Vertical():
                yield Label("File Summary")
                yield Static(
                    "Select a file to see its summary.", id="summary", expand=True
                )
                yield REPLPane(id="repl_pane")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one(FileTree).update_tree(self.workspace_root)
        self.refresh_status()

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        path = event.node.data
        if path and path in self.coordinator.scan_results:
            summary_data = self.coordinator.scan_results[path]
            summary_text = f"**Path:** {path}\n\n"
            summary_text += f"**Summary:** {summary_data.get('summary', 'N/A')}\n\n"
            summary_text += f"**High Value:** {'Yes' if summary_data.get('is_high_value') else 'No'}"
            self.query_one("#summary", Static).update(summary_text)

    async def run_recon_scan(self, path: str = ".") -> None:
        self._phase = "Scanning"
        self._file_log.info("Scan started: %s", path)
        self.refresh_status()
        try:
            results = await self.coordinator.run_recon(path)
            if "error" in results:
                self.log_message(
"error", f"[red]Scan error:[/red] {results['error']}")
            else:
                self._file_log.info("Scan complete: %d files mapped", len(results))
                self.query_one(FileTree).update_tree(path, results)
        except Exception as e:
            self._file_log.error("Scan exception: %s\n%s", e, traceback.format_exc())
            self.log_message(
"error", f"[bold red]Scan failed:[/bold red] {e}")
        finally:
            self._phase = "Idle"
            self.refresh_status()

    async def run_hunter_analysis(self, targets: List[str]) -> None:
        self._phase = "Hunting"
        self._file_log.info("Hunt started: %s", targets)
        self.refresh_status()
        try:
            await self.coordinator.run_hunter(targets)
            self._file_log.info(
                "Hunt complete: %d findings", len(self.coordinator.findings)
            )
        except Exception as e:
            self._file_log.error("Hunt exception: %s\n%s", e, traceback.format_exc())
            self.log_message(
"error", f"[bold red]Hunt failed:[/bold red] {e}")
        finally:
            self._phase = "Idle"
            self.refresh_status()

    async def run_verification(self, finding: Finding) -> None:
        self._phase = "Verifying"
        self._file_log.info("Verification started: %s", finding.title)
        self.refresh_status()
        try:
            await self.coordinator.verify_finding(finding)
            self._file_log.info(
                "Verification complete: %s → %s",
                finding.title,
                finding.verification_status,
            )
        except Exception as e:
            self._file_log.error(
                "Verification exception: %s\n%s", e, traceback.format_exc()
            )
            self.log_message(
"error", f"[bold red]Verification failed:[/bold red] {e}")
        finally:
            self._phase = "Idle"
            self.refresh_status()

    def action_scan(self) -> None:
        self.run_worker(self.run_recon_scan(self.workspace_root))

    def action_prioritize(self) -> None:
        high_value = [
            p
            for p, d in self.coordinator.scan_results.items()
            if d.get("is_high_value")
        ]
        for path in high_value:
            if path not in self.prioritized_targets:
                self.prioritized_targets.append(path)
        self._file_log.info(
            "Auto-prioritized %d targets: %s", len(high_value), high_value
        )
        self.log_message(
            "info",
            f"[green]Auto-prioritized {len(high_value)} high-value targets.[/green]",
        )
        self.refresh_status()

    async def action_quit(self) -> None:
        if hasattr(self, "coordinator") and self.coordinator is not None:
            self.coordinator.db.close_scan_session(self.coordinator.session_id)
        self.exit()

    def action_clear_log(self) -> None:
        self.query_one("#repl_log", RichLog).clear()


if __name__ == "__main__":
    app = TrashDigApp()
    app.run()
