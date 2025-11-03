"""Encryption and decryption utilities for vault security."""

import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64


def derive_key(password: str, salt: bytes) -> bytes:
    """Derive a secret key from the given password and salt using PBKDF2HMAC.

    Args:
        password: The password to derive the key from
        salt: The salt bytes to use in key derivation

    Returns:
        The derived key as bytes
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,  # OWASP recommended minimum
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key


def encrypt_data(data: str, password: str) -> tuple[bytes, bytes]:
    """Encrypt data with the given password.

    Args:
        data: The string data to encrypt
        password: The password to use for encryption

    Returns:
        A tuple of (encrypted_data, salt)
    """
    salt = os.urandom(16)
    key = derive_key(password, salt)
    fernet = Fernet(key)
    encrypted = fernet.encrypt(data.encode())
    return encrypted, salt


def decrypt_data(encrypted_data: bytes, password: str, salt: bytes) -> str:
    """Decrypt data with the given password and salt.

    Args:
        encrypted_data: The encrypted data bytes
        password: The password to use for decryption
        salt: The salt used during encryption

    Returns:
        The decrypted string data

    Raises:
        cryptography.fernet.InvalidToken: If the password is incorrect
    """
    key = derive_key(password, salt)
    fernet = Fernet(key)
    decrypted = fernet.decrypt(encrypted_data)
    return decrypted.decode()
