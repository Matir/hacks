from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Markdown, Static

from trashdig.services.vulndb import get_vulndb_service

if TYPE_CHECKING:
    from trashdig.findings import Finding


class Label(Static):
    """Simple styled label for sections."""

    DEFAULT_CSS = """
    Label {
        text-style: bold;
        background: $accent;
        color: $text;
        padding: 0 1;
        margin-top: 1;
    }
    """


class FindingDetailScreen(Screen):
    """A screen for viewing the full details of a single finding."""

    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("q", "back", "Back"),
    ]

    def __init__(self, finding: Finding, **kwargs: Any) -> None:
        """Initializes the detail screen.

        Args:
            finding: The finding to display.
            **kwargs: Additional Screen arguments.
        """
        super().__init__(**kwargs)
        self.finding = finding

    def compose(self) -> ComposeResult:
        """Composes the detail screen layout."""
        yield Header()

        # Check VulnDB for extra context
        vuln_entry = None
        if self.finding.cwe_id:
            vuln_entry = get_vulndb_service().get_entry(self.finding.cwe_id)

        with VerticalScroll(id="detail_container"):
            yield Static(f"# {self.finding.title}", classes="detail_header")
            yield Static(f"**Severity:** {self.finding.severity} | **Status:** {self.finding.verification_status or 'Unverified'}")
            yield Static(f"**File:** {self.finding.file_path}")

            if self.finding.cwe_id:
                yield Static(f"**CWE:** {self.finding.cwe_id}")

            yield Label("Description")
            yield Markdown(self.finding.description or "N/A")

            if self.finding.vulnerable_code:
                yield Label("Vulnerable Code")
                yield Static(self.finding.vulnerable_code, classes="code_block")

            yield Label("Impact")
            yield Markdown(self.finding.impact or "N/A")

            yield Label("Remediation")
            yield Markdown(self.finding.remediation or "N/A")

            if vuln_entry:
                yield Label(f"Knowledge Base: {vuln_entry.id}")
                yield Markdown(vuln_entry.get_content())

            if self.finding.poc:
                yield Label("Proof of Concept")
                yield Static(self.finding.poc, classes="code_block")

            with Horizontal(id="action_buttons"):
                yield Button("Confirm", variant="success", id="btn_confirm")
                yield Button("False Positive", variant="error", id="btn_fp")
                yield Button("Fixed", variant="primary", id="btn_fixed")

        yield Footer()

    def action_back(self) -> None:
        """Pops the screen and returns to the previous one."""
        self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handles button clicks to override finding status."""
        if event.button.id == "btn_confirm":
            self.finding.verification_status = "Confirmed"
        elif event.button.id == "btn_fp":
            self.finding.verification_status = "False Positive"
        elif event.button.id == "btn_fixed":
            self.finding.verification_status = "Fixed"

        # Update DB via coordinator (accessible through app)
        from trashdig.tui.app import TrashDigApp  # noqa: PLC0415

        app = cast(TrashDigApp, self.app)
        app.coordinator.db.save_finding(app.coordinator.project_path, self.finding)
        app.refresh_status()
        self.app.notify(f"Status updated to: {self.finding.verification_status}")
