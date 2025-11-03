"""Tests for import/export module."""

import json
from pathlib import Path
from dotp.importexport import (
    parse_otpauth_uri,
    export_to_otpauth,
    import_from_text,
    export_to_text,
    import_from_aegis,
    export_to_aegis,
)
from dotp.vault import TOTPEntry


def test_parse_otpauth_uri():
    """Test parsing otpauth URI."""
    uri = "otpauth://totp/GitHub?secret=JBSWY3DPEHPK3PXP&period=30&digits=6&algorithm=SHA1"
    entry = parse_otpauth_uri(uri)

    assert entry.label == "GitHub"
    assert entry.secret == "JBSWY3DPEHPK3PXP"
    assert entry.period == 30
    assert entry.digits == 6
    assert entry.algorithm == "SHA1"


def test_parse_otpauth_uri_url_encoded():
    """Test parsing otpauth URI with URL-encoded label."""
    uri = "otpauth://totp/GitHub:%20user@example.com?secret=JBSWY3DPEHPK3PXP&period=30&digits=6&algorithm=SHA1"
    entry = parse_otpauth_uri(uri)

    # Should decode URL-encoded characters
    assert entry.label == "GitHub: user@example.com"


def test_export_to_otpauth():
    """Test exporting entry to otpauth URI."""
    entry = TOTPEntry(
        label="GitHub",
        secret="JBSWY3DPEHPK3PXP",
        digits=6,
        algorithm="SHA1",
        period=30,
    )

    uri = export_to_otpauth(entry)
    assert uri.startswith("otpauth://totp/GitHub")
    assert "secret=JBSWY3DPEHPK3PXP" in uri
    assert "period=30" in uri
    assert "digits=6" in uri
    assert "algorithm=SHA1" in uri


def test_import_from_text(tmp_path):
    """Test importing from text file."""
    text_file = tmp_path / "test.txt"
    text_file.write_text(
        "otpauth://totp/GitHub?secret=SECRET1&period=30&digits=6&algorithm=SHA1\n"
        "otpauth://totp/GitLab?secret=SECRET2&period=30&digits=6&algorithm=SHA1\n"
    )

    entries = import_from_text(text_file)
    assert len(entries) == 2
    assert entries[0].label == "GitHub"
    assert entries[1].label == "GitLab"


def test_export_to_text(tmp_path):
    """Test exporting to text file."""
    entries = [
        TOTPEntry(label="GitHub", secret="SECRET1", digits=6, algorithm="SHA1", period=30),
        TOTPEntry(label="GitLab", secret="SECRET2", digits=6, algorithm="SHA1", period=30),
    ]

    text_file = tmp_path / "export.txt"
    export_to_text(entries, text_file)

    assert text_file.exists()
    content = text_file.read_text()
    assert "GitHub" in content
    assert "GitLab" in content
    assert "SECRET1" in content
    assert "SECRET2" in content


def test_import_from_aegis(tmp_path):
    """Test importing from Aegis JSON."""
    aegis_data = {
        "version": 2,
        "database": {
            "entries": [
                {
                    "type": "totp",
                    "name": "user@example.com",
                    "issuer": "GitHub",
                    "info": {
                        "secret": "SECRET1",
                        "digits": 6,
                        "period": 30,
                        "algorithm": "SHA1",
                    },
                }
            ]
        },
    }

    aegis_file = tmp_path / "aegis.json"
    aegis_file.write_text(json.dumps(aegis_data))

    entries = import_from_aegis(aegis_file)
    assert len(entries) == 1
    assert "GitHub" in entries[0].label
    assert entries[0].secret == "SECRET1"


def test_export_to_aegis(tmp_path):
    """Test exporting to Aegis JSON."""
    entries = [
        TOTPEntry(
            label="GitHub: user@example.com",
            secret="SECRET1",
            digits=6,
            algorithm="SHA1",
            period=30,
        ),
    ]

    aegis_file = tmp_path / "export.json"
    export_to_aegis(entries, aegis_file)

    assert aegis_file.exists()
    data = json.loads(aegis_file.read_text())

    assert data["version"] == 2
    assert len(data["database"]["entries"]) == 1
    entry = data["database"]["entries"][0]
    assert entry["type"] == "totp"
    assert entry["info"]["secret"] == "SECRET1"
