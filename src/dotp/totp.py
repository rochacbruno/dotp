"""TOTP token generation utilities."""

import pyotp
from datetime import datetime
from .vault import TOTPEntry


def generate_token(entry: TOTPEntry) -> str:
    """Generate a TOTP token for the given entry.

    Args:
        entry: The TOTP entry to generate token for

    Returns:
        The current TOTP token as a string
    """
    totp = pyotp.TOTP(
        entry.secret,
        digits=entry.digits,
        digest=entry.algorithm.lower(),
        interval=entry.period,
    )
    return totp.now()


def get_time_remaining() -> int:
    """Get seconds remaining until next token refresh.

    Returns:
        Number of seconds until the next 30-second window
    """
    now = datetime.now()
    seconds = now.second
    return 30 - (seconds % 30)


def get_valid_until_time() -> str:
    """Get the time when the current token will expire.

    Returns:
        Time string in HH:MM:SS format
    """
    now = datetime.now()
    seconds_remaining = get_time_remaining()
    total_seconds = now.hour * 3600 + now.minute * 60 + now.second + seconds_remaining

    hours = (total_seconds // 3600) % 24
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60

    return f"{hours:02d}:{minutes:02d}:{secs:02d}"
