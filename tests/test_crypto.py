"""Tests for crypto module."""

import pytest
from dotp.crypto import encrypt_data, decrypt_data


def test_encrypt_decrypt():
    """Test encryption and decryption."""
    password = "123456"
    data = "test data"

    encrypted, salt = encrypt_data(data, password)
    decrypted = decrypt_data(encrypted, password, salt)

    assert decrypted == data


def test_decrypt_wrong_password():
    """Test decryption with wrong password raises error."""
    password = "123456"
    wrong_password = "654321"
    data = "test data"

    encrypted, salt = encrypt_data(data, password)

    with pytest.raises(Exception):
        decrypt_data(encrypted, wrong_password, salt)


def test_encrypt_produces_different_output():
    """Test that same data encrypted twice produces different ciphertext."""
    password = "123456"
    data = "test data"

    encrypted1, salt1 = encrypt_data(data, password)
    encrypted2, salt2 = encrypt_data(data, password)

    # Different salts should produce different encrypted data
    assert salt1 != salt2
    assert encrypted1 != encrypted2
