"""Chiffrement Fernet pour les clés fournisseurs (au repos dans MongoDB)."""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from app.config.settings import Settings


class FernetCipher:
    """Wrapper autour de `cryptography.fernet.Fernet`."""

    def __init__(self, key: bytes | str) -> None:
        if isinstance(key, str):
            key = key.encode()
        self._fernet = Fernet(key)

    def encrypt(self, plaintext: str) -> str:
        """Chiffre une chaîne → retourne base64 (str)."""
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        """Déchiffre une chaîne base64 → retourne clair (str)."""
        try:
            return self._fernet.decrypt(ciphertext.encode()).decode()
        except InvalidToken as exc:
            raise ValueError("déchiffrement invalide (clé ou données corrompues)") from exc


def build_cipher(settings: Settings) -> FernetCipher:
    """Construit le cipher depuis `ENCRYPTION_KEY` (validée dans Settings)."""
    return FernetCipher(settings.encryption_key)


__all__ = ["FernetCipher", "build_cipher"]
