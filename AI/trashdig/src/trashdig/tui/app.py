from __future__ import annotations

import logging
import os
import traceback
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, cast

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.events import Key
from textual.widgets import Footer, Header, Input, Label, RichLog, Static, Tree
from textual_autocomplete import AutoComplete, DropdownItem

from trashdig.agents.coordinator import Coordinator
from trashdig.agents.utils.helpers import get_project_structure, log_auth_info
from trashdig.agents.utils.types import EngineState
from trashdig.config import Config
from trashdig.findings import Finding
from trashdig.tools import get_artifact_service
from trashdig.tui.screens.ask import AskModal
from trashdig.tui.screens.findings import FindingsScreen

if TYPE_CHECKING:
    from trashdig.agents.coordinator import Coordinator


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

    def __init__(self, label: str, data: dict[str, dict[str, Any]]):
        """Initializes the file tree.

        Args:
            label: The root label for the tree.
            data: Project mapping data.
        """
        super().__init__(label)
        self.data = data

    def update_tree(self, root_path: str = ".", data: dict[str, dict[str, Any]] | None = None) -> None:
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
        """Composes the status pane widgets."""
        yield Label("Status")
        yield Static("", id="status_body")

    def refresh_status(  # noqa: PLR0913
        self,
        workspace_root: str,
        phase: str,
        tech_stack: str,
        scan_results: dict[str, Any],
        prioritized_targets: list[str],
        findings: list[Finding],
        task_queue_len: int,
        completed_len: int,
        total_messages: int = 0,
        input_tokens: int = 0,
        output_tokens: int = 0,
        llm_errors: int = 0,
    ) -> None:
        """Refreshes the status display with current engine stats.

        Args:
            workspace_root: Path to the project root.
            phase: Current engine phase.
            tech_stack: Detected technology stack.
            scan_results: Mapping of files to metadata.
            prioritized_targets: List of files selected for hunting.
            findings: List of all findings found so far.
            task_queue_len: Number of pending tasks.
            completed_len: Number of completed tasks.
            total_messages: Count of LLM messages.
            input_tokens: Cumulative input tokens.
            output_tokens: Cumulative output tokens.
            llm_errors: Count of LLM-related errors.
        """
        high_value = sum(
            1
            for d in scan_results.values()
            if isinstance(d, dict) and d.get("is_high_value")
        )

        severity_counts: dict[str, int] = {}
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
            "Paused": "red",
            "Steering": "cyan",
        }.get(phase, "white")

        root_display = os.path.basename(workspace_root) or workspace_root

        def _fmt_tokens(n: int) -> str:
            return f"{n:,}" if n < 1_000_000 else f"{n/1_000_000:.1f}M"  # noqa: PLR2004

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
        """Initializes the REPL pane.

        Args:
            **kwargs: Keyword arguments for Vertical.
        """
        super().__init__(**kwargs)
        self.history: list[str] = []
        self.history_index: int = -1
        self.commands = [
            "help", "scan", "hunt", "star", "verify", "status", "exit",
            "pause", "resume", "hint", "hypotheses",
        ]

    def compose(self) -> ComposeResult:
        """Composes the REPL pane widgets."""
        yield Label("Interactive Console")
        yield RichLog(id="repl_log", highlight=True, markup=True, wrap=True)
        repl_input = Input(
            placeholder="Type a command (e.g., 'scan api/', 'help')...",
            id="repl_input",
        )
        yield repl_input
        yield AutoComplete(
            repl_input,
            candidates=[DropdownItem(cmd) for cmd in self.commands],
            id="repl_autocomplete",
        )

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handles command submission from the input field."""
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
        elif event.key == "down" and self.history:
            if self.history_index != -1:
                if self.history_index < len(self.history) - 1:
                    self.history_index += 1
                    input_widget = self.query_one("#repl_input", Input)
                    input_widget.value = self.history[self.history_index]
                else:
                    self.history_index = -1
                    self.query_one("#repl_input", Input).value = ""
            event.prevent_default()

    def _handle_help_command(self, log: RichLog) -> None:
        log.write("Available commands: [green]" + ", ".join(self.commands) + "[/green]")

    def _handle_scan_command(self, cmd_parts: list[str], app: TrashDigApp) -> None:
        path = cmd_parts[1] if len(cmd_parts) > 1 else app.workspace_root
        app.run_worker(app.run_recon_scan(path))

    def _handle_hunt_command(self, log: RichLog, app: TrashDigApp) -> None:
        if not app.prioritized_targets:
            log.write("[red]No targets prioritized. Star some files first![/red]")
        else:
            app.run_worker(app.run_hunter_analysis(app.prioritized_targets))

    def _handle_verify_command(self, cmd_parts: list[str], log: RichLog, app: TrashDigApp) -> None:
        if not app.coordinator.findings:
            log.write("[red]No findings to verify. Run 'hunt' first![/red]")
        elif len(cmd_parts) < 2:  # noqa: PLR2004
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

    def _handle_star_command(self, cmd_parts: list[str], log: RichLog, app: TrashDigApp) -> None:
        if len(cmd_parts) < 2:  # noqa: PLR2004
            log.write("[red]Usage: star <path>[/red]")
        else:
            path = os.path.normpath(cmd_parts[1])  # noqa: ASYNC240
            if path not in app.prioritized_targets:
                app.prioritized_targets.append(path)
                app._file_log.info("Starred: %s", path)
                log.write(f"[green]Starred {path} for hunting.[/green]")
                app.refresh_status()
            else:
                log.write(f"[yellow]{path} is already starred.[/yellow]")

    def _handle_status_command(self, log: RichLog, app: TrashDigApp) -> None:
        log.write(
            f"Prioritized targets: [cyan]{', '.join(app.prioritized_targets) or 'None'}[/cyan]"
        )
        app.refresh_status()

    def _handle_pause_command(self, log: RichLog, app: TrashDigApp) -> None:
        app.coordinator.pause()
        log.write("[bold yellow]System:[/bold yellow] Engine pausing... will stop at next safe point.")
        app.refresh_status()

    def _handle_resume_command(self, log: RichLog, app: TrashDigApp) -> None:
        app.coordinator.resume()
        log.write("[bold green]System:[/bold green] Engine resumed.")
        app.refresh_status()

    def _handle_hint_command(self, cmd_parts: list[str], log: RichLog, app: TrashDigApp) -> None:
        if len(cmd_parts) < 2:  # noqa: PLR2004
            log.write("[red]Usage: hint <text>[/red]")
        else:
            text = " ".join(cmd_parts[1:])
            app.coordinator.add_hint(text)
            log.write(f"[bold cyan]User Hint:[/bold cyan] {text}")

    def _resolve_hypothesis_match(
        self, hypotheses: list[dict[str, Any]], prefix: str, log: RichLog
    ) -> dict[str, Any] | None:
        matches = [h for h in hypotheses if str(h["task_id"]).startswith(prefix)]
        if len(matches) != 1:
            log.write(f"[red]{'No' if not matches else 'Ambiguous'} match for id prefix '{prefix}'.[/red]")
            return None
        return matches[0]

    def _handle_hypotheses_list(self, hypotheses: list[dict[str, Any]], log: RichLog) -> None:
        if not hypotheses:
            log.write("[yellow]No hypotheses recorded yet.[/yellow]")
            return
        for h in hypotheses:
            short_id = str(h["task_id"])[:8]
            log.write(
                f"[cyan]{short_id}[/cyan] "
                f"conf=[bold]{h['confidence']:.2f}[/bold] "
                f"status={h['status']} "
                f"target={h['target']} — {h['description']}"
            )

    def _handle_hypotheses_delete(
        self, cmd_parts: list[str], hypotheses: list[dict[str, Any]], log: RichLog, app: TrashDigApp
    ) -> None:
        if len(cmd_parts) < 3:  # noqa: PLR2004
            log.write("[red]Usage: hypotheses del <id-prefix>[/red]")
            return
        match = self._resolve_hypothesis_match(hypotheses, cmd_parts[2], log)
        if match is None:
            return
        app.coordinator.db.delete_hypothesis(match["task_id"])
        log.write(f"[green]Deleted hypothesis {match['task_id'][:8]}.[/green]")

    def _handle_hypotheses_prio(
        self, cmd_parts: list[str], hypotheses: list[dict[str, Any]], log: RichLog, app: TrashDigApp
    ) -> None:
        if len(cmd_parts) < 4:  # noqa: PLR2004
            log.write("[red]Usage: hypotheses prio <id-prefix> <confidence>[/red]")
            return
        match = self._resolve_hypothesis_match(hypotheses, cmd_parts[2], log)
        if match is None:
            return
        try:
            confidence = float(cmd_parts[3])
        except ValueError:
            log.write(f"[red]Invalid confidence: {cmd_parts[3]}[/red]")
            return
        if not 0.0 <= confidence <= 1.0:
            log.write("[red]Confidence must be between 0.0 and 1.0.[/red]")
            return
        app.coordinator.db.update_hypothesis_confidence(match["task_id"], confidence)
        log.write(f"[green]Updated {match['task_id'][:8]} confidence to {confidence:.2f}.[/green]")

    def _handle_hypotheses_command(self, cmd_parts: list[str], log: RichLog, app: TrashDigApp) -> None:
        sub = cmd_parts[1].lower() if len(cmd_parts) > 1 else "list"
        hypotheses = app.coordinator.db.get_hypotheses(app.coordinator.project_path)

        if sub == "list":
            self._handle_hypotheses_list(hypotheses, log)
        elif sub in ("del", "delete"):
            self._handle_hypotheses_delete(cmd_parts, hypotheses, log, app)
        elif sub in ("prio", "prioritize"):
            self._handle_hypotheses_prio(cmd_parts, hypotheses, log, app)
        else:
            log.write(f"[red]Unknown hypotheses subcommand: {sub}[/red]")

    async def process_command(self, command: str, log: RichLog) -> None:
        """Parses and executes a command from the REPL.

        Args:
            command: The raw command string.
            log: The log widget to write output to.
        """
        cmd_parts = command.split()
        if not cmd_parts:
            return
        base_cmd = cmd_parts[0].lower()
        app = cast("TrashDigApp", self.app)

        if base_cmd == "exit":
            await app.action_quit()
            return

        handlers: dict[str, Callable[[], None]] = {
            "help": lambda: self._handle_help_command(log),
            "scan": lambda: self._handle_scan_command(cmd_parts, app),
            "hunt": lambda: self._handle_hunt_command(log, app),
            "verify": lambda: self._handle_verify_command(cmd_parts, log, app),
            "star": lambda: self._handle_star_command(cmd_parts, log, app),
            "status": lambda: self._handle_status_command(log, app),
            "pause": lambda: self._handle_pause_command(log, app),
            "resume": lambda: self._handle_resume_command(log, app),
            "hint": lambda: self._handle_hint_command(cmd_parts, log, app),
            "hypotheses": lambda: self._handle_hypotheses_command(cmd_parts, log, app),
        }
        handler = handlers.get(base_cmd)
        if handler is None:
            log.write(f"[red]Unknown command: {base_cmd}[/red]")
        else:
            handler()


class TrashDigApp(App):
    """The main TrashDig TUI application."""

    TITLE = "TrashDig"
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("f5", "scan", "Scan"),
        Binding("f6", "prioritize", "Prioritize"),
        Binding("v", "view_findings", "Findings"),
        Binding("ctrl+l", "clear_log", "Clear Log"),
        Binding("space", "toggle_pause", "Pause/Resume"),
        Binding("h", "hint", "Provide Hint"),
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
    .code_block {
        background: $boost;
        border: solid $accent;
        padding: 1 2;
        margin: 1 0;
    }
    .detail_header {
        background: $accent;
        color: $text;
        text-style: bold;
        padding: 1 2;
        margin-bottom: 1;
    }
    #action_buttons {
        height: auto;
        align: center middle;
        margin-top: 1;
    }
    #action_buttons Button {
        margin: 0 1;
    }
    """

    def __init__(self, config: Config | None = None, workspace_root: str | None = None):
        """Initializes the TUI application.

        Args:
            config: TrashDig configuration.
            workspace_root: Path to the project to scan.
        """
        super().__init__()
        self.config = config or Config()
        self.workspace_root = workspace_root or self.config.workspace_root
        self._phase = "Idle"
        # Concurrent verification workers (e.g. "verify all findings") share
        # this counter so the phase only drops back to "Idle" once every
        # in-flight verification has actually finished.
        self._active_verifications = 0
        log_path = self.config.resolve_data_path("trashdig.log")
        self._file_log = _setup_file_logger(log_path)
        self._file_log.info("Session started — workspace: %s", workspace_root)
        log_auth_info(self.config, self._file_log)

        art_service = get_artifact_service()

        self.coordinator = Coordinator(
            self.config,
            project_path=workspace_root,
            on_ask=self._on_ask,
            artifact_service=art_service,
        )
        self.coordinator.on_task_event = lambda msg: self.call_from_thread(self._on_coordinator_log, msg)
        self.coordinator.on_stats_event = lambda: self.call_from_thread(self.refresh_status)
        self.prioritized_targets: list[str] = []

    def log_message(self, level: str, message: str) -> None:
        """Write to both the TUI console and the log file."""
        plain = message  # Rich markup stripped automatically by logger
        getattr(self._file_log, level)(plain)
        try:
            self.query_one("#repl_log", RichLog).write(message)
            self.refresh_status()
        except Exception:
            self._file_log.debug("REPL log write failed (likely TUI not fully mounted).")

    def _on_coordinator_log(self, message: str) -> None:
        self.log_message("info", message)

    async def _on_ask(self, question: str) -> str:
        """Handles a question from an agent by showing a modal.

        Args:
            question: The question to ask.
        """
        self.log_message("info", f"[bold red]Interaction Required:[/bold red] {question}")
        result = await self.push_screen_wait(AskModal(question))
        return cast(str, result)

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
                self._file_log.debug("Worker error logging to REPL failed.")
            self._phase = "Idle"
            self.refresh_status()

    def refresh_status(self) -> None:
        """Triggers a UI refresh of the status pane."""
        try:
            status_pane = self.query_one(StatusPane)
            engine_state = getattr(self.coordinator, "state", None)
            if engine_state == EngineState.PAUSED:
                phase = "Paused"
            elif engine_state == EngineState.STEERING:
                phase = "Steering"
            else:
                phase = self._phase
            status_pane.refresh_status(
                workspace_root=self.workspace_root,
                phase=phase,
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
        """Composes the application layout."""
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
        """Fires when the app is mounted."""
        self.query_one(FileTree).update_tree(self.workspace_root)
        self.refresh_status()

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Handles file selection in the tree."""
        path = event.node.data
        if path and path in self.coordinator.scan_results:
            summary_data = self.coordinator.scan_results[path]
            summary_text = f"**Path:** {path}\n\n"
            summary_text += f"**Summary:** {summary_data.get('summary', 'N/A')}\n\n"
            summary_text += f"**High Value:** {'Yes' if summary_data.get('is_high_value') else 'No'}"
            self.query_one("#summary", Static).update(summary_text)

    async def run_recon_scan(self, path: str = ".") -> None:
        """Runs the reconnaissance phase asynchronously.

        Args:
            path: Project path to scan.
        """
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

    async def run_hunter_analysis(self, targets: list[str]) -> None:
        """Runs the hunting phase for prioritized targets asynchronously.

        Args:
            targets: List of files to hunt in.
        """
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
        """Runs the verification pipeline for a finding asynchronously.

        Safe to run concurrently (e.g. "verify all findings" spawns one
        worker per finding): the phase only reverts to "Idle" once every
        concurrently-running verification has finished, via
        `_active_verifications`.

        Args:
            finding: The Finding to verify.
        """
        self._active_verifications += 1
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
            self._active_verifications -= 1
            if self._active_verifications <= 0:
                self._phase = "Idle"
            self.refresh_status()

    def action_scan(self) -> None:
        """Starts a full scan via a keybinding."""
        self.run_worker(self.run_recon_scan(self.workspace_root))

    def action_prioritize(self) -> None:
        """Automatically stars all high-value files."""
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
        """Saves session state and exits the application."""
        if hasattr(self, "coordinator") and self.coordinator is not None:
            self.coordinator.db.close_scan_session(self.coordinator.session_id)
        self.exit()

    def action_clear_log(self) -> None:
        """Clears the REPL console log."""
        self.query_one("#repl_log", RichLog).clear()

    def action_toggle_pause(self) -> None:
        """Toggles the engine paused state."""
        if self.coordinator.state == EngineState.PAUSED:
            self.coordinator.resume()
            self.query_one("#repl_log", RichLog).write("[bold green]System:[/bold green] Engine resumed.")
        else:
            self.coordinator.pause()
            self.query_one("#repl_log", RichLog).write("[bold yellow]System:[/bold yellow] Engine pausing... will stop at next safe point.")
        self.refresh_status()

    async def action_hint(self) -> None:
        """Provides a manual hint to the engine."""
        def check_hint(hint: str | None) -> None:
            if hint:
                # Append hint to context or print
                self.query_one("#repl_log", RichLog).write(f"[bold cyan]User Hint:[/bold cyan] {hint}")
                self.coordinator.add_hint(hint)
        self.push_screen(AskModal("Enter a hint/override for the current analysis:"), check_hint)

    def action_view_findings(self) -> None:
        """Opens the findings browser screen."""
        self.push_screen(FindingsScreen())


if __name__ == "__main__":
    app = TrashDigApp()
    app.run()
