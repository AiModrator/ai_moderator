"""Tests unitaires du chiffrement Fernet (main.md §7, §3.1)."""

from __future__ import annotations

import pytest
from cryptography.fernet import Fernet

from app.config.security import FernetCipher


class TestFernetCipher:
    def test_round_trip(self) -> None:
        key = Fernet.generate_key()
        cipher = FernetCipher(key)
        plaintext = "ma-clé-secrète-123"
        encrypted = cipher.encrypt(plaintext)
        decrypted = cipher.decrypt(encrypted)
        assert decrypted == plaintext
        assert encrypted != plaintext

    def test_invalid_key_raises(self) -> None:
        # Fernet key must be 32 url-safe base64-encoded bytes
        with pytest.raises(ValueError, match="Fernet key must be 32"):
            FernetCipher(b"invalid-key")

    def test_different_key_fails_decrypt(self) -> None:
        key1 = Fernet.generate_key()
        key2 = Fernet.generate_key()
        cipher1 = FernetCipher(key1)
        cipher2 = FernetCipher(key2)
        encrypted = cipher1.encrypt("secret")
        with pytest.raises(ValueError, match="déchiffrement invalide"):
            cipher2.decrypt(encrypted)

    def test_str_key_input(self) -> None:
        key = Fernet.generate_key().decode()
        cipher = FernetCipher(key)  # str input
        assert cipher.decrypt(cipher.encrypt("test")) == "test"
