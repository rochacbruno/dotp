"""DOTP - Dank One Time Password Manager."""

import sys

from .cli import app as cli_app
from .tui import run_tui


def main() -> None:
    """Main entry point for DOTP.

    If called with arguments, run CLI commands.
    If called without arguments, run TUI.
    """
    # Check if any arguments were provided (excluding the program name)
    if len(sys.argv) > 1:
        # Run CLI
        cli_app()
    else:
        # Run TUI
        run_tui()
