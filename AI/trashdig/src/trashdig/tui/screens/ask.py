from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static


class AskModal(ModalScreen[str]):
    """A modal dialog for asking the user a question."""

    DEFAULT_CSS = """
    AskModal {
        align: center middle;
    }
    #ask_dialog {
        width: 60;
        height: auto;
        padding: 1 2;
        background: $boost;
        border: thick $accent;
    }
    #ask_question {
        margin-bottom: 1;
    }
    #ask_buttons {
        height: auto;
        align: right middle;
        margin-top: 1;
    }
    #ask_buttons Button {
        margin-left: 1;
    }
    """

    def __init__(self, question: str, **kwargs: Any) -> None:
        """Initializes the modal.

        Args:
            question: The question to display.
            **kwargs: Additional ModalScreen arguments.
        """
        super().__init__(**kwargs)
        self.question = question

    def compose(self) -> ComposeResult:
        """Composes the modal layout."""
        with Static(id="ask_dialog"):
            yield Label("[bold red]Agent Question[/bold red]")
            yield Static(self.question, id="ask_question")
            yield Input(placeholder="Your answer...", id="ask_input")
            with Horizontal(id="ask_buttons"):
                yield Button("Submit", variant="primary", id="btn_submit")
                yield Button("Skip", variant="default", id="btn_skip")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handles button clicks."""
        if event.button.id == "btn_submit":
            answer = self.query_one("#ask_input", Input).value
            self.dismiss(answer)
        elif event.button.id == "btn_skip":
            self.dismiss("")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handles input submission via Enter."""
        self.dismiss(event.value)
