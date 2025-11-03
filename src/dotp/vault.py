"""Vault management for storing and retrieving TOTP secrets."""

import json
from pathlib import Path
from typing import Any
from urllib.parse import unquote
from dataclasses import dataclass, asdict

from .crypto import encrypt_data, decrypt_data


@dataclass
class TOTPEntry:
    """Represents a single TOTP entry in the vault."""

    label: str
    secret: str
    digits: int = 6
    algorithm: str = "SHA1"
    period: int = 30

    def to_dict(self) -> dict[str, Any]:
        """Convert entry to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TOTPEntry":
        """Create entry from dictionary."""
        return cls(**data)


class Vault:
    """Manages encrypted vault storage for TOTP entries."""

    def __init__(self, vault_path: Path):
        """Initialize vault with the given path.

        Args:
            vault_path: Path to the vault file
        """
        self.vault_path = vault_path
        self._entries: list[TOTPEntry] = []

    def exists(self) -> bool:
        """Check if vault file exists."""
        return self.vault_path.exists()

    def create(self, password: str) -> None:
        """Create a new encrypted vault file.

        Args:
            password: Password to encrypt the vault
        """
        data = json.dumps({"entries": []})
        encrypted, salt = encrypt_data(data, password)

        # Store salt + encrypted data
        vault_data = salt + encrypted
        self.vault_path.write_bytes(vault_data)

    def load(self, password: str) -> None:
        """Load and decrypt vault data.

        Args:
            password: Password to decrypt the vault

        Raises:
            InvalidToken: If password is incorrect
            FileNotFoundError: If vault doesn't exist
        """
        if not self.exists():
            raise FileNotFoundError(f"Vault not found at {self.vault_path}")

        vault_data = self.vault_path.read_bytes()
        salt = vault_data[:16]
        encrypted = vault_data[16:]

        decrypted = decrypt_data(encrypted, password, salt)
        data = json.loads(decrypted)

        self._entries = [TOTPEntry.from_dict(entry) for entry in data["entries"]]

    def save(self, password: str) -> None:
        """Save and encrypt vault data.

        Args:
            password: Password to encrypt the vault
        """
        data = json.dumps({"entries": [entry.to_dict() for entry in self._entries]})
        encrypted, salt = encrypt_data(data, password)

        vault_data = salt + encrypted
        self.vault_path.write_bytes(vault_data)

    def add_entry(self, entry: TOTPEntry) -> None:
        """Add a new TOTP entry to the vault.

        Args:
            entry: The TOTP entry to add
        """
        self._entries.append(entry)

    def get_entry_exact(self, label: str) -> TOTPEntry | None:
        """Get an entry by exact label match only.

        Args:
            label: The exact label to search for

        Returns:
            The matching entry or None if not found
        """
        label_lower = label.lower()
        for entry in self._entries:
            # Decode URL-encoded characters for comparison
            decoded_label = unquote(entry.label)
            if decoded_label.lower() == label_lower:
                return entry
        return None

    def get_entry(self, label: str) -> TOTPEntry | None:
        """Get an entry by label.

        Matches in order:
        1. Exact match (case-insensitive)
        2. Prefix match - returns first entry starting with the label

        Args:
            label: The label to search for

        Returns:
            The matching entry or None if not found
        """
        label_lower = label.lower()

        # Try exact match first (case-insensitive)
        exact_match = self.get_entry_exact(label)
        if exact_match:
            return exact_match

        # Try prefix match - return first match starting with label
        for entry in self._entries:
            # Decode URL-encoded characters for pattern matching
            decoded_label = unquote(entry.label)
            if decoded_label.lower().startswith(label_lower):
                return entry

        return None

    def list_entries(self) -> list[TOTPEntry]:
        """Get all entries in the vault.

        Returns:
            List of all TOTP entries
        """
        return self._entries.copy()

    def remove_entry(self, label: str) -> bool:
        """Remove an entry by label.

        Args:
            label: The label of the entry to remove

        Returns:
            True if entry was removed, False if not found
        """
        for i, entry in enumerate(self._entries):
            if entry.label.lower() == label.lower():
                self._entries.pop(i)
                return True
        return False

    def search_entries(self, query: str) -> list[TOTPEntry]:
        """Search entries by label containing the query string.

        Args:
            query: Search query string

        Returns:
            List of matching entries
        """
        query_lower = query.lower()
        return [entry for entry in self._entries if query_lower in entry.label.lower()]
