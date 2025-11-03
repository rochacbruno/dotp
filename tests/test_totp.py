"""Tests for TOTP module."""

import time
from dotp.totp import generate_token, get_time_remaining, get_valid_until_time
from dotp.vault import TOTPEntry


def test_generate_token():
    """Test TOTP token generation."""
    entry = TOTPEntry(
        label="Test",
        secret="JBSWY3DPEHPK3PXP",
        digits=6,
        algorithm="SHA1",
        period=30,
    )

    token = generate_token(entry)
    assert len(token) == 6
    assert token.isdigit()


def test_generate_token_different_digits():
    """Test TOTP token generation with different digit count."""
    entry = TOTPEntry(
        label="Test",
        secret="JBSWY3DPEHPK3PXP",
        digits=8,
        algorithm="SHA1",
        period=30,
    )

    token = generate_token(entry)
    assert len(token) == 8
    assert token.isdigit()


def test_get_time_remaining():
    """Test getting time remaining."""
    remaining = get_time_remaining()
    assert 0 <= remaining <= 30


def test_get_valid_until_time():
    """Test getting valid until time."""
    valid_until = get_valid_until_time()
    assert ":" in valid_until
    # Format should be HH:MM:SS
    parts = valid_until.split(":")
    assert len(parts) == 3
    assert all(p.isdigit() for p in parts)


def test_token_changes_after_period():
    """Test that token changes after the period expires."""
    entry = TOTPEntry(
        label="Test",
        secret="JBSWY3DPEHPK3PXP",
        digits=6,
        algorithm="SHA1",
        period=1,  # 1 second period for testing
    )

    token1 = generate_token(entry)
    time.sleep(1.1)  # Wait for period to expire
    token2 = generate_token(entry)

    # Tokens should be different after period expires
    assert token1 != token2
