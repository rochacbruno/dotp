"""CLI commands for DOTP using cyclopts."""

import os
import sys
from pathlib import Path
from typing import Optional, Annotated
from getpass import getpass
from urllib.parse import unquote
import cyclopts
from rich.console import Console
from rich.table import Table
from cryptography.fernet import InvalidToken

from .vault import Vault, TOTPEntry
from .totp import generate_token, get_valid_until_time
from .config import get_default_vault_path
from .importexport import (
    import_from_text,
    export_to_text,
    import_from_aegis,
    export_to_aegis,
)
from xdg_base_dirs import xdg_config_home

app = cyclopts.App(name="dotp", help="Dank One Time Password Manager")
console = Console()


def get_password(prompt: str = "Enter vault password: ") -> str:
    """Get password from environment or prompt user.

    Args:
        prompt: The prompt to display to the user

    Returns:
        The password string
    """
    password = os.environ.get("DOTP_PASSWD")
    if password:
        return password
    return getpass(prompt)


def validate_password(password: str) -> bool:
    """Validate that password is 6 digits.

    Args:
        password: The password to validate

    Returns:
        True if valid, False otherwise
    """
    return len(password) == 6 and password.isdigit()


@app.command
def init(
    path: Annotated[
        Optional[Path], cyclopts.Parameter(help="Path to vault file")
    ] = None,
) -> None:
    """Initialize a new encrypted vault."""
    vault_path = path or (xdg_config_home() / "dotp" / ".vault.dotp")

    if vault_path.exists():
        console.print(f"[red]Error: Vault already exists at {vault_path}[/red]")
        sys.exit(1)

    console.print(f"Starting new vault at {vault_path}")

    # Check if password is provided via environment
    password = os.environ.get("DOTP_PASSWD")
    if password:
        if not validate_password(password):
            console.print("[red]Error: DOTP_PASSWD must be exactly 6 digits[/red]")
            sys.exit(1)
    else:
        # Interactive password input
        while True:
            password = getpass("Type a 6 digit password to encrypt your vault: ")
            if not validate_password(password):
                console.print("[red]Password must be exactly 6 digits[/red]")
                continue

            repeat = getpass("Repeat: ")
            if password != repeat:
                console.print("[red]Passwords do not match[/red]")
                continue
            break

    # Ensure parent directory exists
    vault_path.parent.mkdir(parents=True, exist_ok=True)

    vault = Vault(vault_path)
    vault.create(password)

    console.print("[green]Vault created and encrypted[/green]")


@app.command
def add(
    label: Annotated[
        Optional[str], cyclopts.Parameter(help="Label for the entry")
    ] = None,
    secret: Annotated[Optional[str], cyclopts.Parameter(help="TOTP secret key")] = None,
    digits: Annotated[int, cyclopts.Parameter(help="Number of digits")] = 6,
    algo: Annotated[str, cyclopts.Parameter(help="Hash algorithm")] = "SHA1",
    period: Annotated[int, cyclopts.Parameter(help="Token period in seconds")] = 30,
    path: Annotated[
        Optional[Path], cyclopts.Parameter(help="Path to vault file")
    ] = None,
) -> None:
    """Add a new TOTP entry to the vault."""
    vault_path = get_default_vault_path(path)

    if not vault_path.exists():
        console.print(f"[red]Error: Vault not found at {vault_path}[/red]")
        console.print("Run 'dotp init' to create a new vault")
        sys.exit(1)

    # Get label if not provided
    if not label:
        label = input("Label: ")

    # Get secret if not provided
    if not secret:
        secret = getpass("Secret: ")

    password = get_password()

    vault = Vault(vault_path)
    try:
        vault.load(password)
    except InvalidToken:
        console.print("[red]Error: Invalid password[/red]")
        sys.exit(1)

    # Check if label already exists (exact match only)
    if vault.get_entry_exact(label):
        console.print(f"[red]Error: Entry with label '{label}' already exists[/red]")
        sys.exit(1)

    entry = TOTPEntry(
        label=label, secret=secret, digits=digits, algorithm=algo, period=period
    )
    vault.add_entry(entry)
    vault.save(password)

    console.print(f"[green]Added entry '{label}'[/green]")


@app.command
def list(
    path: Annotated[
        Optional[Path], cyclopts.Parameter(help="Path to vault file")
    ] = None,
) -> None:
    """List all entries and their current tokens."""
    vault_path = get_default_vault_path(path)

    if not vault_path.exists():
        console.print(f"[red]Error: Vault not found at {vault_path}[/red]")
        sys.exit(1)

    password = get_password()

    vault = Vault(vault_path)
    try:
        vault.load(password)
    except InvalidToken:
        console.print("[red]Error: Invalid password[/red]")
        sys.exit(1)

    entries = vault.list_entries()
    if not entries:
        console.print("No entries in vault")
        return

    # Create table
    table = Table(title=f"Valid until: {get_valid_until_time()}")
    table.add_column("Label", style="cyan")
    table.add_column("Token", style="green")

    for entry in entries:
        token = generate_token(entry)
        # Decode URL-encoded characters for display
        decoded_label = unquote(entry.label)
        table.add_row(decoded_label, token)

    console.print(table)


@app.command
def get(
    label: Annotated[str, cyclopts.Parameter(help="Label of the entry")],
    path: Annotated[
        Optional[Path], cyclopts.Parameter(help="Path to vault file")
    ] = None,
) -> None:
    """Get the token for a specific entry."""
    vault_path = get_default_vault_path(path)

    if not vault_path.exists():
        console.print(f"[red]Error: Vault not found at {vault_path}[/red]")
        sys.exit(1)

    password = get_password()

    vault = Vault(vault_path)
    try:
        vault.load(password)
    except InvalidToken:
        console.print("[red]Error: Invalid password[/red]")
        sys.exit(1)

    entry = vault.get_entry(label)
    if not entry:
        console.print(f"[red]Error: Entry '{label}' not found[/red]")
        sys.exit(1)

    token = generate_token(entry)
    # Clean output when using envvar (for piping)
    if os.environ.get("DOTP_PASSWD"):
        print(token)
    else:
        console.print(token)


@app.command(name="import")
def import_cmd(
    file_path: Annotated[Path, cyclopts.Parameter(help="File to import from")],
    aegis: Annotated[
        bool, cyclopts.Parameter(help="Import from Aegis JSON format")
    ] = False,
    path: Annotated[
        Optional[Path], cyclopts.Parameter(help="Path to vault file")
    ] = None,
) -> None:
    """Import entries from a file."""
    vault_path = get_default_vault_path(path)

    if not vault_path.exists():
        console.print(f"[red]Error: Vault not found at {vault_path}[/red]")
        console.print("Run 'dotp init' to create a new vault")
        sys.exit(1)

    if not file_path.exists():
        console.print(f"[red]Error: Import file not found at {file_path}[/red]")
        sys.exit(1)

    password = get_password()

    vault = Vault(vault_path)
    try:
        vault.load(password)
    except InvalidToken:
        console.print("[red]Error: Invalid password[/red]")
        sys.exit(1)

    # Import entries
    if aegis:
        entries = import_from_aegis(file_path)
    else:
        entries = import_from_text(file_path)

    added = 0
    skipped = 0
    for entry in entries:
        # Use exact match only for duplicate detection during import
        if vault.get_entry_exact(entry.label):
            skipped += 1
            continue
        vault.add_entry(entry)
        added += 1

    vault.save(password)

    console.print(f"[green]Imported {added} entries[/green]")
    if skipped > 0:
        console.print(f"[yellow]Skipped {skipped} duplicate entries[/yellow]")


@app.command(name="export")
def export_cmd(
    file_path: Annotated[Path, cyclopts.Parameter(help="File to export to")],
    aegis: Annotated[
        bool, cyclopts.Parameter(help="Export to Aegis JSON format")
    ] = False,
    path: Annotated[
        Optional[Path], cyclopts.Parameter(help="Path to vault file")
    ] = None,
) -> None:
    """Export entries to a file."""
    vault_path = get_default_vault_path(path)

    if not vault_path.exists():
        console.print(f"[red]Error: Vault not found at {vault_path}[/red]")
        sys.exit(1)

    password = get_password()

    vault = Vault(vault_path)
    try:
        vault.load(password)
    except InvalidToken:
        console.print("[red]Error: Invalid password[/red]")
        sys.exit(1)

    entries = vault.list_entries()

    # Export entries
    if aegis:
        export_to_aegis(entries, file_path)
    else:
        export_to_text(entries, file_path)

    console.print(f"[green]Exported {len(entries)} entries to {file_path}[/green]")
