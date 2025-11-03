"""DOTP - Dank One Time Password Manager."""

import sys
from pathlib import Path

from .cli import app as cli_app
from .tui import run_tui


def main() -> None:
    """Main entry point for DOTP.

    If called with arguments, run CLI commands.
    If called without arguments, run TUI.
    Special case: `--path` alone launches TUI with custom vault.
    """
    # Check if only --path argument is provided (for TUI with custom vault)
    if len(sys.argv) == 3 and sys.argv[1] == "--path":
        vault_path = Path(sys.argv[2])
        run_tui(vault_path)
    elif len(sys.argv) > 1:
        # Run CLI (handles its own --path parsing)
        cli_app()
    else:
        # Run TUI with default vault
        run_tui()
