import os
from typing import List, Dict, Any
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Tree, Static, Label, Input, RichLog
from textual.containers import Vertical, Horizontal
from textual.binding import Binding
from textual.events import Key
from textual_autocomplete import AutoComplete, DropdownItem

from trashdig.agents.coordinator import Coordinator
from trashdig.agents.utils import get_project_structure
from trashdig.config import Config
from trashdig.findings import Finding


class FileTree(Tree):
    """A tree representing the project file structure."""
    def __init__(self, label: str, data: Dict[str, Dict[str, Any]]):
        super().__init__(label)
        self.data = data

    def update_tree(self, root_path: str = ".", data: Dict[str, Dict[str, Any]] = None):
        """Updates the tree with file structure and optional metadata."""
        self.clear()
        self.data = data or {}
        file_list = get_project_structure(root_path)

        nodes = {"": self.root}
        for path in file_list:
            parts = path.split(os.sep)
            for i in range(len(parts)):
                parent_path = os.sep.join(parts[:i])
                current_path = os.sep.join(parts[:i+1])
                if current_path not in nodes:
                    parent_node = nodes[parent_path]
                    is_file = (i == len(parts) - 1)
                    label = parts[i]
                    if current_path in self.data and self.data[current_path].get("is_high_value"):
                        label = f"⭐ {label}"
                    if is_file:
                        nodes[current_path] = parent_node.add_leaf(label, data=current_path)
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
    ) -> None:
        high_value = sum(1 for d in scan_results.values() if isinstance(d, dict) and d.get("is_high_value"))

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

        lines = [
            f"[bold]Phase:[/bold]    [{phase_color}]{phase}[/{phase_color}]",
            f"[bold]Root:[/bold]     {root_display}",
            f"[bold]Stack:[/bold]    {tech_stack or '—'}",
            f"[bold]Files:[/bold]    {len(scan_results)} ({high_value} high-value)",
            f"[bold]Targets:[/bold]  {len(prioritized_targets)} prioritized",
            f"[bold]Findings:[/bold] {len(findings)} ({sev_str})",
            f"[bold]Queue:[/bold]    {task_queue_len} pending / {completed_len} done",
        ]
        self.query_one("#status_body", Static).update("\n".join(lines))


class REPLPane(Vertical):
    """A REPL-style interface with command history and autocompletion."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.history: List[str] = []
        self.history_index: int = -1
        self.commands = ["help", "scan", "hunt", "star", "verify", "status", "exit"]

    def compose(self) -> ComposeResult:
        yield Label("Interactive Console")
        yield RichLog(id="repl_log", highlight=True, markup=True)
        yield AutoComplete(
            Input(placeholder="Type a command (e.g., 'scan api/', 'help')...", id="repl_input"),
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

        if base_cmd == "help":
            log.write("Available commands: [green]" + ", ".join(self.commands) + "[/green]")
        elif base_cmd == "scan":
            path = cmd_parts[1] if len(cmd_parts) > 1 else self.app.workspace_root
            self.app.run_worker(self.app.run_archaeologist_scan(path))
        elif base_cmd == "hunt":
            if not self.app.prioritized_targets:
                log.write("[red]No targets prioritized. Star some files first![/red]")
            else:
                self.app.run_worker(self.app.run_hunter_analysis(self.app.prioritized_targets))
        elif base_cmd == "verify":
            if not self.app.coordinator.findings:
                log.write("[red]No findings to verify. Run 'hunt' first![/red]")
            else:
                if len(cmd_parts) < 2:
                    log.write("[yellow]Verifying all findings...[/yellow]")
                    for finding in self.app.coordinator.findings:
                        self.app.run_worker(self.app.run_verification(finding))
                else:
                    try:
                        idx = int(cmd_parts[1]) - 1
                        finding = self.app.coordinator.findings[idx]
                        self.app.run_worker(self.app.run_verification(finding))
                    except (ValueError, IndexError):
                        log.write(f"[red]Invalid finding index: {cmd_parts[1]}[/red]")
        elif base_cmd == "star":
            if len(cmd_parts) < 2:
                log.write("[red]Usage: star <path>[/red]")
            else:
                path = cmd_parts[1]
                if path not in self.app.prioritized_targets:
                    self.app.prioritized_targets.append(path)
                    log.write(f"[green]Starred {path} for hunting.[/green]")
                    self.app.refresh_status()
                else:
                    log.write(f"[yellow]{path} is already starred.[/yellow]")
        elif base_cmd == "status":
            log.write(f"Prioritized targets: [cyan]{', '.join(self.app.prioritized_targets) or 'None'}[/cyan]")
        elif base_cmd == "exit":
            self.app.exit()
        else:
            log.write(f"[red]Unknown command: {command}[/red]")


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
    """

    def __init__(self, config: Config = None, workspace_root: str = "."):
        super().__init__()
        self.config = config or Config()
        self.workspace_root = workspace_root
        self._phase = "Idle"
        self.coordinator = Coordinator(self.config, project_path=workspace_root)
        self.coordinator.on_task_event = self._on_coordinator_log
        self.prioritized_targets: List[str] = []

    def _on_coordinator_log(self, message: str) -> None:
        try:
            self.query_one("#repl_log", RichLog).write(message)
            self.refresh_status()
        except Exception:
            pass

    def refresh_status(self) -> None:
        try:
            self.query_one(StatusPane).refresh_status(
                workspace_root=self.workspace_root,
                phase=self._phase,
                tech_stack=self.coordinator.tech_stack,
                scan_results=self.coordinator.scan_results,
                prioritized_targets=self.prioritized_targets,
                findings=self.coordinator.findings,
                task_queue_len=len(self.coordinator.task_queue),
                completed_len=len(self.coordinator.completed_tasks),
            )
        except Exception:
            pass

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Label("Project Map")
                yield FileTree("Project Root", {})
                yield StatusPane()
            with Vertical():
                yield Label("File Summary")
                yield Static("Select a file to see its summary.", id="summary", expand=True)
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

    async def run_archaeologist_scan(self, path: str = ".") -> None:
        self._phase = "Scanning"
        self.refresh_status()
        results = await self.coordinator.run_archaeologist(path)
        self._phase = "Idle"
        if "error" not in results:
            self.query_one(FileTree).update_tree(path, results)
        self.refresh_status()

    async def run_hunter_analysis(self, targets: List[str]) -> None:
        self._phase = "Hunting"
        self.refresh_status()
        await self.coordinator.run_hunter(targets)
        self._phase = "Idle"
        self.refresh_status()

    async def run_verification(self, finding: Finding) -> None:
        self._phase = "Verifying"
        self.refresh_status()
        await self.coordinator.verify_finding(finding)
        self._phase = "Idle"
        self.refresh_status()

    def action_scan(self) -> None:
        self.run_worker(self.run_archaeologist_scan(self.workspace_root))

    def action_prioritize(self) -> None:
        log = self.query_one("#repl_log", RichLog)
        high_value = [p for p, d in self.coordinator.scan_results.items() if d.get("is_high_value")]
        for path in high_value:
            if path not in self.prioritized_targets:
                self.prioritized_targets.append(path)
        log.write(f"[green]Auto-prioritized {len(high_value)} high-value targets.[/green]")
        self.refresh_status()

    def action_quit(self) -> None:
        self.exit()

    def action_clear_log(self) -> None:
        self.query_one("#repl_log", RichLog).clear()


if __name__ == "__main__":
    app = TrashDigApp()
    app.run()
