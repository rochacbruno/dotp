"""Import and export functionality for vault data."""

import json
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote
from .vault import TOTPEntry


def parse_otpauth_uri(uri: str) -> TOTPEntry:
    """Parse an otpauth:// URI into a TOTPEntry.

    Args:
        uri: The otpauth URI string

    Returns:
        TOTPEntry parsed from the URI
    """
    parsed = urlparse(uri)
    params = parse_qs(parsed.query)

    # Extract label from path and decode URL-encoded characters
    label = unquote(parsed.path.lstrip("/"))

    # Extract parameters with defaults
    secret = params.get("secret", [""])[0]
    period = int(params.get("period", ["30"])[0])
    digits = int(params.get("digits", ["6"])[0])
    algorithm = params.get("algorithm", ["SHA1"])[0]

    return TOTPEntry(
        label=label, secret=secret, digits=digits, algorithm=algorithm, period=period
    )


def export_to_otpauth(entry: TOTPEntry) -> str:
    """Convert a TOTPEntry to otpauth URI format.

    Args:
        entry: The TOTP entry to export

    Returns:
        otpauth URI string
    """
    return (
        f"otpauth://totp/{entry.label}"
        f"?period={entry.period}"
        f"&digits={entry.digits}"
        f"&algorithm={entry.algorithm}"
        f"&secret={entry.secret}"
    )


def import_from_text(file_path: Path) -> list[TOTPEntry]:
    """Import entries from a text file with otpauth URIs.

    Args:
        file_path: Path to the text file

    Returns:
        List of imported TOTPEntry objects
    """
    entries = []
    with open(file_path, "r") as f:
        for line in f:
            line = line.strip()
            if line and line.startswith("otpauth://"):
                try:
                    entry = parse_otpauth_uri(line)
                    entries.append(entry)
                except Exception:
                    # Skip invalid entries
                    continue
    return entries


def export_to_text(entries: list[TOTPEntry], file_path: Path) -> None:
    """Export entries to a text file with otpauth URIs.

    Args:
        entries: List of TOTP entries to export
        file_path: Path to write the text file
    """
    with open(file_path, "w") as f:
        for entry in entries:
            uri = export_to_otpauth(entry)
            f.write(uri + "\n")


def import_from_aegis(file_path: Path) -> list[TOTPEntry]:
    """Import entries from Aegis JSON export format.

    Args:
        file_path: Path to the Aegis JSON file

    Returns:
        List of imported TOTPEntry objects
    """
    with open(file_path, "r") as f:
        data = json.load(f)

    entries = []
    for item in data.get("database", {}).get("entries", []):
        if item.get("type") == "totp":
            info = item.get("info", {})
            label = item.get("name", "Unknown")
            issuer = item.get("issuer", "")

            # Include issuer in label if present
            if issuer and issuer not in label:
                label = f"{issuer}: {label}"

            entry = TOTPEntry(
                label=label,
                secret=info.get("secret", ""),
                digits=info.get("digits", 6),
                algorithm=info.get("algorithm", "SHA1"),
                period=info.get("period", 30),
            )
            entries.append(entry)

    return entries


def export_to_aegis(entries: list[TOTPEntry], file_path: Path) -> None:
    """Export entries to Aegis JSON format.

    Args:
        entries: List of TOTP entries to export
        file_path: Path to write the JSON file
    """
    aegis_entries = []
    for i, entry in enumerate(entries):
        # Split label into issuer and name if it contains ':'
        parts = entry.label.split(":", 1)
        if len(parts) == 2:
            issuer = parts[0].strip()
            name = parts[1].strip()
        else:
            issuer = entry.label
            name = entry.label

        aegis_entry = {
            "type": "totp",
            "uuid": f"generated-{i:08x}",
            "name": name,
            "issuer": issuer,
            "icon": "",
            "info": {
                "secret": entry.secret,
                "digits": entry.digits,
                "period": entry.period,
                "algorithm": entry.algorithm,
            },
            "tags": [],
        }
        aegis_entries.append(aegis_entry)

    data = {"version": 2, "database": {"entries": aegis_entries, "folders": []}}

    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)
