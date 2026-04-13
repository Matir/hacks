import os
from typing import List, Dict, Any
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Tree, Static, Label, Input, RichLog
from textual.containers import Vertical, Horizontal
from textual.binding import Binding
from textual.events import Key
from textual_autocomplete import AutoComplete, Dropdown, DropdownItem

from trashdig.agents.coordinator import Coordinator
from trashdig.agents.utils import get_project_structure
from trashdig.config import Config
from trashdig.findings import Finding

class FileTree(Tree):
    """A tree representing the project file structure."""
    def __init__(self, label: str, data: Dict[str, Dict[str, Any]]):
        super().__init__(label)
        self.data = data # Dict mapping file paths to summaries and flags

    def update_tree(self, root_path: str = ".", data: Dict[str, Dict[str, Any]] = None):
        """Updates the tree with file structure and optional metadata."""
        self.clear()
        self.data = data or {}
        file_list = get_project_structure(root_path)
        
        # Build tree structure from file list
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
                    # Add star if high value
                    if current_path in self.data and self.data[current_path].get("is_high_value"):
                        label = f"⭐ {label}"
                        
                    if is_file:
                        nodes[current_path] = parent_node.add_leaf(label, data=current_path)
                    else:
                        nodes[current_path] = parent_node.add(label, data=current_path)
        self.root.expand()

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
        
        # Setup Autocomplete for the Input
        yield AutoComplete(
            Input(placeholder="Type a command (e.g., 'scan api/', 'help')...", id="repl_input"),
            Dropdown(items=[DropdownItem(cmd) for cmd in self.commands], id="repl_dropdown"),
            id="repl_autocomplete"
        )

    def on_input_submitted(self, event: Input.Submitted) -> None:
        command = event.value.strip()
        if not command:
            return

        # Add to history
        if not self.history or self.history[-1] != command:
            self.history.append(command)
        self.history_index = -1

        log = self.query_one("#repl_log", RichLog)
        log.write(f"> [bold cyan]{command}[/bold cyan]")
        
        # Clear the input
        event.input.value = ""

        # Process the command
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
            path = cmd_parts[1] if len(cmd_parts) > 1 else "."
            # Call the app method to run the scan
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
        Binding("s", "scan", "Scan"),
        Binding("p", "prioritize", "Prioritize"),
        Binding("ctrl+l", "clear_log", "Clear Log"),
    ]

    def __init__(self, config: Config = None):
        super().__init__()
        self.config = config or Config()
        self.coordinator = Coordinator(self.config)
        self.coordinator.on_task_event = self._on_coordinator_log
        self.prioritized_targets: List[str] = []

    def _on_coordinator_log(self, message: str) -> None:
        """Callback for coordinator logs."""
        try:
            self.query_one("#repl_log", RichLog).write(message)
        except Exception:
            pass # App might not be fully mounted

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield Vertical(
                Label("Project Map"),
                FileTree("Project Root", {}),
                id="sidebar"
            )
            with Vertical():
                yield Label("File Summary")
                yield Static("Select a file to see its summary.", id="summary", expand=True)
                yield REPLPane(id="repl_pane")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one(FileTree).update_tree()

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Handles selecting a node in the file tree."""
        path = event.node.data
        if path and path in self.coordinator.scan_results:
            summary_data = self.coordinator.scan_results[path]
            summary_text = f"**Path:** {path}\n\n"
            summary_text += f"**Summary:** {summary_data.get('summary', 'N/A')}\n\n"
            summary_text += f"**High Value:** {'Yes' if summary_data.get('is_high_value') else 'No'}"
            self.query_one("#summary", Static).update(summary_text)

    async def run_archaeologist_scan(self, path: str = ".") -> None:
        """Runs the Archaeologist scan and updates the UI."""
        results = await self.coordinator.run_archaeologist(path)
        
        if "error" not in results:
            self.query_one(FileTree).update_tree(path, results)

    async def run_hunter_analysis(self, targets: List[str]) -> None:
        """Runs the Hunter analysis and updates the UI."""
        await self.coordinator.run_hunter(targets)

    async def run_verification(self, finding: Finding) -> None:
        """Runs the Validator scan and updates the UI."""
        await self.coordinator.verify_finding(finding)

    def action_quit(self) -> None:

        self.exit()

    def action_clear_log(self) -> None:
        self.query_one("#repl_log", RichLog).clear()

if __name__ == "__main__":
    app = TrashDigApp()
    app.run()
