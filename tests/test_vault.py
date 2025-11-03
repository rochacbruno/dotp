"""Tests for vault module."""

import pytest
from pathlib import Path
from dotp.vault import Vault, TOTPEntry
from cryptography.fernet import InvalidToken


@pytest.fixture
def temp_vault(tmp_path):
    """Create a temporary vault for testing."""
    vault_path = tmp_path / "test_vault.dotp"
    return vault_path


def test_vault_create_and_load(temp_vault):
    """Test creating and loading a vault."""
    password = "123456"
    vault = Vault(temp_vault)
    vault.create(password)

    assert temp_vault.exists()

    # Load the vault
    vault2 = Vault(temp_vault)
    vault2.load(password)
    assert vault2.list_entries() == []


def test_vault_add_entry(temp_vault):
    """Test adding an entry to the vault."""
    password = "123456"
    vault = Vault(temp_vault)
    vault.create(password)

    entry = TOTPEntry(label="GitHub", secret="JBSWY3DPEHPK3PXP")
    vault.add_entry(entry)
    vault.save(password)

    # Load and verify
    vault2 = Vault(temp_vault)
    vault2.load(password)
    entries = vault2.list_entries()

    assert len(entries) == 1
    assert entries[0].label == "GitHub"
    assert entries[0].secret == "JBSWY3DPEHPK3PXP"


def test_vault_get_entry(temp_vault):
    """Test getting an entry by label."""
    password = "123456"
    vault = Vault(temp_vault)
    vault.create(password)

    entry = TOTPEntry(label="GitHub", secret="JBSWY3DPEHPK3PXP")
    vault.add_entry(entry)

    found = vault.get_entry("GitHub")
    assert found is not None
    assert found.label == "GitHub"

    # Case insensitive
    found = vault.get_entry("github")
    assert found is not None


def test_vault_get_entry_prefix_match(temp_vault):
    """Test getting an entry by prefix matching."""
    password = "123456"
    vault = Vault(temp_vault)
    vault.create(password)

    entry = TOTPEntry(label="GitHub: user@example.com", secret="JBSWY3DPEHPK3PXP")
    vault.add_entry(entry)

    # Prefix match
    found = vault.get_entry("GitHub")
    assert found is not None
    assert found.label == "GitHub: user@example.com"


def test_vault_get_entry_url_decoded(temp_vault):
    """Test getting an entry with URL-encoded label."""
    password = "123456"
    vault = Vault(temp_vault)
    vault.create(password)

    # Entry with URL-encoded label
    entry = TOTPEntry(label="GitHub:%20user@example.com", secret="JBSWY3DPEHPK3PXP")
    vault.add_entry(entry)

    # Should match decoded version
    found = vault.get_entry("GitHub: user@example.com")
    assert found is not None


def test_vault_search_entries(temp_vault):
    """Test searching entries."""
    password = "123456"
    vault = Vault(temp_vault)
    vault.create(password)

    vault.add_entry(TOTPEntry(label="GitHub", secret="SECRET1"))
    vault.add_entry(TOTPEntry(label="GitLab", secret="SECRET2"))
    vault.add_entry(TOTPEntry(label="Bitbucket", secret="SECRET3"))

    results = vault.search_entries("git")
    assert len(results) == 2
    labels = [e.label for e in results]
    assert "GitHub" in labels
    assert "GitLab" in labels


def test_vault_remove_entry(temp_vault):
    """Test removing an entry."""
    password = "123456"
    vault = Vault(temp_vault)
    vault.create(password)

    vault.add_entry(TOTPEntry(label="GitHub", secret="SECRET1"))
    assert len(vault.list_entries()) == 1

    removed = vault.remove_entry("GitHub")
    assert removed is True
    assert len(vault.list_entries()) == 0


def test_vault_invalid_password(temp_vault):
    """Test loading vault with invalid password."""
    password = "123456"
    wrong_password = "654321"

    vault = Vault(temp_vault)
    vault.create(password)

    vault2 = Vault(temp_vault)
    with pytest.raises(InvalidToken):
        vault2.load(wrong_password)
