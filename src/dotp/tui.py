"""TUI interface for DOTP using Textual."""

import os
import sys
import subprocess
from pathlib import Path
from typing import Optional
from getpass import getpass

from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import DataTable, Header, Footer, Input, Label, Button, ProgressBar
from textual.screen import ModalScreen
from textual.binding import Binding
from textual import on, events
from cryptography.fernet import InvalidToken
from rich.text import Text
from urllib.parse import unquote

from .vault import Vault, TOTPEntry
from .totp import generate_token, get_time_remaining
from .config import get_default_vault_path, Config


class EntryModal(ModalScreen[Optional[TOTPEntry]]):
    """Modal screen for adding or editing an entry."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=True),
        Binding("ctrl+r", "toggle_secret", "Reveal Secret", show=True),
    ]

    def __init__(self, entry: Optional[TOTPEntry] = None, original_label: Optional[str] = None):
        """Initialize the modal.
        
        Args:
            entry: Entry to edit (None for new entry)
            original_label: Original label (for editing, to track label changes)
        """
        super().__init__()
        self.entry = entry
        self.original_label = original_label or (entry.label if entry else None)
        self.is_editing = entry is not None
        self.secret_revealed = False

    def compose(self) -> ComposeResult:
        """Compose the modal UI."""
        with Container(id="add-modal"):
            title = "Edit Entry" if self.is_editing else "Add New Entry"
            yield Label(title, id="modal-title")
            yield Label("Label:")
            yield Input(placeholder="e.g., GitHub", id="label-input")
            yield Label("Secret: (^R to reveal)")
            yield Input(placeholder="TOTP secret key", password=True, id="secret-input")
            yield Label("Digits (default: 6):")
            yield Input(placeholder="6", id="digits-input")
            yield Label("Algorithm (default: SHA1):")
            yield Input(placeholder="SHA1", id="algo-input")
            yield Label("Period (default: 30):")
            yield Input(placeholder="30", id="period-input")
            with Container(id="button-container"):
                button_label = "Save" if self.is_editing else "Add"
                yield Button(button_label, variant="primary", id="add-button")
                yield Button("Cancel", variant="default", id="cancel-button")

    def on_mount(self) -> None:
        """Prefill form if editing."""
        if self.entry:
            self.query_one("#label-input", Input).value = unquote(self.entry.label)
            self.query_one("#secret-input", Input).value = self.entry.secret
            self.query_one("#digits-input", Input).value = str(self.entry.digits)
            self.query_one("#algo-input", Input).value = self.entry.algorithm
            self.query_one("#period-input", Input).value = str(self.entry.period)

    def action_cancel(self) -> None:
        """Cancel and close modal."""
        self.dismiss(None)

    def action_toggle_secret(self) -> None:
        """Toggle secret visibility."""
        secret_input = self.query_one("#secret-input", Input)
        self.secret_revealed = not self.secret_revealed
        secret_input.password = not self.secret_revealed

    @on(Button.Pressed, "#add-button")
    def on_add_button(self) -> None:
        """Handle add/save button press."""
        label_input = self.query_one("#label-input", Input)
        secret_input = self.query_one("#secret-input", Input)
        digits_input = self.query_one("#digits-input", Input)
        algo_input = self.query_one("#algo-input", Input)
        period_input = self.query_one("#period-input", Input)

        label = label_input.value.strip()
        secret = secret_input.value.strip()

        if not label or not secret:
            return

        digits = int(digits_input.value) if digits_input.value else 6
        algo = algo_input.value.upper() if algo_input.value else "SHA1"
        period = int(period_input.value) if period_input.value else 30

        entry = TOTPEntry(
            label=label, secret=secret, digits=digits, algorithm=algo, period=period
        )
        # Return tuple: (entry, original_label) for edit tracking
        if self.is_editing:
            self.dismiss((entry, self.original_label))
        else:
            self.dismiss((entry, None))

    @on(Button.Pressed, "#cancel-button")
    def on_cancel_button(self) -> None:
        """Handle cancel button press."""
        self.dismiss(None)


class DOTPApp(App):
    """Main TUI application for DOTP."""

    CSS = """
    #add-modal {
        align: center middle;
        background: $surface;
        border: solid $primary;
        width: 90%;
        max-width: 60;
        height: auto;
        padding: 1 2;
    }

    #modal-title {
        text-align: center;
        text-style: bold;
        padding: 0 0 1 0;
    }

    #button-container {
        layout: horizontal;
        align: center middle;
        height: auto;
        padding: 1 0 0 0;
    }

    #button-container Button {
        margin: 0 1;
    }

    DataTable {
        height: 1fr;
    }

    DataTable > .datatable--header {
        text-style: bold;
        background: $primary;
    }

    DataTable > .datatable--cursor {
        background: $secondary;
    }

    #progress-bar {
        dock: top;
        height: 1;
    }

    #search-input {
        dock: bottom;
        height: 3;
        display: none;
    }

    #search-input.visible {
        display: block;
    }
    """

    BINDINGS = [
        Binding(
            "enter", "select_row", "Copy", show=True
        ),  # Handled by DataTable.RowSelected
        Binding("ctrl+enter", "copy_and_close", "Copy & Close", show=True),
        Binding("ctrl+a", "add_entry", "Add Entry", show=True),
        Binding("ctrl+e", "edit_entry", "Edit Entry", show=True),
        Binding("ctrl+q", "quit", "Quit", show=True),
        Binding("escape", "clear_search", "Clear Search", show=False),
    ]

    def __init__(
        self,
        vault_path: Path,
        password: str,
        close_on_copy: bool = False,
        clipboard_command: str = "wl-copy",
    ):
        """Initialize the TUI app.

        Args:
            vault_path: Path to the vault file
            password: Password to decrypt the vault
            close_on_copy: Whether to close app after copying
            clipboard_command: Command to use for clipboard
        """
        super().__init__()
        self.vault_path = vault_path
        self.password = password
        self.close_on_copy = close_on_copy
        self.clipboard_command = clipboard_command
        self.vault = Vault(vault_path)
        self.search_query = ""
        self.update_timer = None

    def compose(self) -> ComposeResult:
        """Compose the main UI."""
        yield Header()
        yield ProgressBar(total=30, show_eta=False, id="progress-bar")
        yield Input(placeholder="Type to search...", id="search-input")
        yield DataTable(id="entries-table")
        yield Footer()

    def on_mount(self) -> None:
        """Load vault and populate table on mount."""
        try:
            self.vault.load(self.password)
        except InvalidToken:
            self.notify("Invalid password", severity="error")
            self.exit()
            return

        table = self.query_one("#entries-table", DataTable)
        self._setup_columns()
        table.cursor_type = "row"

        self.refresh_table()
        self.update_progress()

        # Focus the table
        table.focus()

        # Set up auto-refresh timer
        self.update_timer = self.set_interval(1.0, self.refresh_tokens)

    def _setup_columns(self) -> None:
        """Setup table columns with responsive widths."""
        table = self.query_one("#entries-table", DataTable)
        # Clear existing columns if any
        table.clear(columns=True)

        # Calculate available width (accounting for borders, scrollbar, etc.)
        # Terminal width minus borders (2) and some padding (2)
        available_width = self.size.width - 4

        # Token column needs fixed width (e.g., "123 456" = 7 chars + padding)
        token_width = 10

        # Label gets remaining space
        label_width = max(15, available_width - token_width)

        table.add_column("Label", key="label", width=label_width)
        table.add_column("Token", key="token", width=token_width)

    def on_resize(self, event: events.Resize) -> None:
        """Handle terminal resize to adjust column widths."""
        try:
            self._setup_columns()
            self.refresh_table()
        except Exception:
            # Ignore errors during resize (table might not be ready)
            pass

    def refresh_table(self) -> None:
        """Refresh the table with current entries."""
        table = self.query_one("#entries-table", DataTable)
        table.clear()

        # Get entries based on search query
        if self.search_query:
            entries = self.vault.search_entries(self.search_query)
        else:
            entries = self.vault.list_entries()

        # Get label column width for truncation
        label_width = table.columns["label"].width

        # Add rows with colored tokens
        for entry in entries:
            token = generate_token(entry)
            # Decode URL-encoded labels for display
            decoded_label = unquote(entry.label)

            # Truncate label if needed
            if len(decoded_label) > label_width:
                decoded_label = decoded_label[: label_width - 1] + "…"

            # Create styled token in green with space separator
            styled_token = Text(token[:3] + " " + token[3:], style="bold green")
            table.add_row(decoded_label, styled_token, key=entry.label)

        # Select first row if available
        if table.row_count > 0:
            table.move_cursor(row=0)

    def refresh_tokens(self) -> None:
        """Refresh TOTP tokens in the table."""
        table = self.query_one("#entries-table", DataTable)

        # Update each token
        for row_key in table.rows:
            entry = self.vault.get_entry(str(row_key.value))
            if entry:
                token = generate_token(entry)
                # Add space separator for readability
                styled_token = Text(token[:3] + " " + token[3:], style="bold green")
                table.update_cell(row_key, "token", styled_token)

        self.update_progress()

    def update_progress(self) -> None:
        """Update the progress bar based on time remaining."""
        time_remaining = get_time_remaining()
        progress = self.query_one("#progress-bar", ProgressBar)
        progress.update(progress=time_remaining)

    def on_key(self, event: events.Key) -> None:
        """Handle key presses for search functionality."""
        search_input = self.query_one("#search-input", Input)
        table = self.query_one("#entries-table", DataTable)

        # If Enter pressed in search input, focus the table
        if search_input.has_focus and event.key == "enter":
            table.focus()
            event.prevent_default()
            event.stop()
            return

        # If table has focus and user types backspace or printable char (not ctrl/arrow keys)
        # and search is visible, refocus search
        if table.has_focus and search_input.has_class("visible"):
            if event.key == "backspace" or (
                event.is_printable and not event.key.startswith("ctrl")
            ):
                search_input.focus()
                # If it's a printable character, append it
                if event.is_printable and not event.key.startswith("ctrl"):
                    search_input.value += event.character

                    def move_cursor():
                        search_input.cursor_position = len(search_input.value)

                    self.call_after_refresh(move_cursor)
                event.prevent_default()
                event.stop()
                return

        # If search input is not focused and user types a printable character
        if (
            not search_input.has_focus
            and event.is_printable
            and not event.key.startswith("ctrl")
        ):
            # Show search input and set its value to include the typed character
            search_input.add_class("visible")
            search_input.value = event.character
            search_input.focus()

            # Use call_after_refresh to move cursor after focus completes
            def move_cursor():
                search_input.cursor_position = len(search_input.value)

            self.call_after_refresh(move_cursor)
            event.prevent_default()
            event.stop()

    @on(Input.Changed, "#search-input")
    def on_search_input(self, event: Input.Changed) -> None:
        """Handle search input changes."""
        self.search_query = event.value
        self.refresh_table()

        # Hide search input if empty
        search_input = self.query_one("#search-input", Input)
        if not event.value:
            search_input.remove_class("visible")
            # Refocus table
            table = self.query_one("#entries-table", DataTable)
            table.focus()

    @on(DataTable.RowSelected)
    def on_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection (Enter key)."""
        if event.row_key is None:
            return

        label = str(event.row_key.value)
        entry = self.vault.get_entry(label)
        if entry:
            token = generate_token(entry)
            self.copy_to_clipboard(token)
            self.notify(f"Copied token for '{label}'", severity="information")

            if self.close_on_copy:
                self.exit()

    def copy_to_clipboard(self, text: str) -> None:
        """Copy text to clipboard using configured command.

        Args:
            text: Text to copy to clipboard
        """
        try:
            # Use Popen to avoid blocking - clipboard manager may keep process alive
            process = subprocess.Popen(
                self.clipboard_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True,
            )
            # Write the text and close stdin
            process.stdin.write(text.encode())
            process.stdin.close()
            # Don't wait for the process - let it run in background
        except Exception as e:
            self.notify(f"Failed to copy to clipboard: {e}", severity="error")

    def action_add_entry(self) -> None:
        """Show modal to add a new entry."""

        def handle_entry(result) -> None:
            if result:
                entry, _ = result
                # Check if label already exists
                if self.vault.get_entry(entry.label):
                    self.notify(
                        f"Entry '{entry.label}' already exists", severity="error"
                    )
                    return

                self.vault.add_entry(entry)
                self.vault.save(self.password)
                self.refresh_table()
                self.notify(f"Added entry '{entry.label}'", severity="information")

        self.push_screen(EntryModal(), handle_entry)

    def action_edit_entry(self) -> None:
        """Show modal to edit the selected entry."""
        table = self.query_one("#entries-table", DataTable)
        if table.cursor_row is None or table.row_count == 0:
            self.notify("No entry selected", severity="warning")
            return

        # Get the row key from the cursor position
        row_key = list(table.rows.keys())[table.cursor_row]
        label = str(row_key.value)
        entry = self.vault.get_entry(label)
        
        if not entry:
            self.notify("Entry not found", severity="error")
            return

        def handle_entry(result) -> None:
            if result:
                updated_entry, original_label = result
                
                # If label changed, check for duplicates
                if updated_entry.label != original_label:
                    if self.vault.get_entry(updated_entry.label):
                        self.notify(
                            f"Entry '{updated_entry.label}' already exists", severity="error"
                        )
                        return
                    # Remove old entry
                    self.vault.remove_entry(original_label)
                else:
                    # Same label, just remove to update
                    self.vault.remove_entry(original_label)
                
                # Add updated entry
                self.vault.add_entry(updated_entry)
                self.vault.save(self.password)
                self.refresh_table()
                self.notify(f"Updated entry '{updated_entry.label}'", severity="information")

        self.push_screen(EntryModal(entry=entry, original_label=label), handle_entry)

    def action_select_row(self) -> None:
        """Dummy action for Enter key - actual handling in DataTable.RowSelected event."""
        pass

    def action_copy_and_close(self) -> None:
        """Copy token and close app (Ctrl+Enter)."""
        table = self.query_one("#entries-table", DataTable)
        if table.cursor_row is not None and table.row_count > 0:
            # Get the row key from the cursor position
            row_key = list(table.rows.keys())[table.cursor_row]
            label = str(row_key.value)
            entry = self.vault.get_entry(label)
            if entry:
                token = generate_token(entry)
                self.copy_to_clipboard(token)
                self.notify(f"Copied token for '{label}'", severity="information")
                self.exit()

    def action_clear_search(self) -> None:
        """Clear search input."""
        search_input = self.query_one("#search-input", Input)
        search_input.value = ""
        search_input.remove_class("visible")
        # Refocus table
        table = self.query_one("#entries-table", DataTable)
        table.focus()


def run_tui(vault_path: Optional[Path] = None) -> None:
    """Run the TUI application.

    Args:
        vault_path: Optional path to vault file
    """
    vault_path = get_default_vault_path(vault_path)

    if not vault_path.exists():
        print(f"Error: Vault not found at {vault_path}")
        print("Run 'dotp init' to create a new vault")
        sys.exit(1)

    # Get password from env or prompt
    password = os.environ.get("DOTP_PASSWD")
    if not password:
        password = getpass("Enter vault password: ")

    # Load config
    config = Config.load()

    # Run the app
    app = DOTPApp(
        vault_path=vault_path,
        password=password,
        close_on_copy=config.close_on_copy,
        clipboard_command=config.clipboard_command,
    )
    app.run()
