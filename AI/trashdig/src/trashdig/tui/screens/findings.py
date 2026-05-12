from __future__ import annotations

from typing import TYPE_CHECKING, cast

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Input

from trashdig.tui.screens.finding_detail import FindingDetailScreen

if TYPE_CHECKING:
    from trashdig.tui.app import TrashDigApp


class FindingsScreen(Screen):
    """A screen for browsing all discovered findings."""

    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("q", "back", "Back"),
        Binding("enter", "select_finding", "View Details"),
    ]

    def compose(self) -> ComposeResult:
        """Composes the findings browser layout."""
        yield Header()
        with Vertical():
            yield Input(placeholder="Search findings (title, file, description...)", id="search_findings")
            yield DataTable(id="findings_table")
        yield Footer()

    def on_mount(self) -> None:
        """Populates the data table when the screen is mounted."""
        table = self.query_one(DataTable)
        table.cursor_type = "row"
        table.add_columns("#", "Title", "Severity", "File", "Status")
        self.update_table()

    def update_table(self, search_text: str = "") -> None:
        """Updates the table with filtered findings.

        Args:
            search_text: Text to filter by.
        """
        table = self.query_one(DataTable)
        table.clear()

        app = cast("TrashDigApp", self.app)
        findings = app.coordinator.findings

        search_text = search_text.lower()

        for i, f in enumerate(findings, 1):
            # Search across all fields
            match_data = f"{f.title} {f.file_path} {f.severity} {f.description} {f.impact} {f.cwe_id}".lower()
            if search_text and search_text not in match_data:
                continue

            table.add_row(
                str(i),
                f.title,
                f"[bold]{f.severity}[/bold]",
                f.file_path,
                f.verification_status or "Unverified",
                key=str(i-1) # Store index for selection
            )

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handles real-time search filtering."""
        if event.input.id == "search_findings":
            self.update_table(event.value)

    def action_back(self) -> None:
        """Returns to the main dashboard."""
        self.app.pop_screen()

    def action_select_finding(self) -> None:
        """Opens the detail view for the selected finding."""
        table = self.query_one(DataTable)
        if table.cursor_row is not None:
            table.get_row_at(table.cursor_row)
            # We can't easily get the key back from get_row_at in some versions,
            # but we can use the row index if we didn't filter, or store finding in row data.
            # DataTable.get_row returns the list of values.
            # Better approach: find the finding by the key we set.
            idx = int(table.cursor_row) # This works if we re-sync table and list

            app = cast("TrashDigApp", self.app)
            # Since we filter, we need to map back to the original list.
            # Let's store the index in the row key or similar.

            # Re-fetch the filtered list to find the correct finding
            search_text = self.query_one("#search_findings", Input).value.lower()
            filtered = []
            for f in app.coordinator.findings:
                match_data = f"{f.title} {f.file_path} {f.severity} {f.description} {f.impact} {f.cwe_id}".lower()
                if not search_text or search_text in match_data:
                    filtered.append(f)

            if 0 <= idx < len(filtered):
                self.app.push_screen(FindingDetailScreen(filtered[idx]))

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handles row selection via enter or double-click."""
        app = cast("TrashDigApp", self.app)
        search_text = self.query_one("#search_findings", Input).value.lower()
        filtered = []
        for f in app.coordinator.findings:
            match_data = f"{f.title} {f.file_path} {f.severity} {f.description} {f.impact} {f.cwe_id}".lower()
            if not search_text or search_text in match_data:
                filtered.append(f)

        # event.cursor_row is the absolute row index in the current table view
        if 0 <= event.cursor_row < len(filtered):
            self.app.push_screen(FindingDetailScreen(filtered[event.cursor_row]))
