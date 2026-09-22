"""Chiffrement Fernet pour les clés fournisseurs (au repos dans MongoDB)."""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from app.config.settings import Settings


class FernetCipher:
    """Wrapper autour de `cryptography.fernet.Fernet`."""

    def __init__(self, key: bytes | str) -> None:
        print(f"[DEBUG FernetCipher.__init__] key type: {type(key)}, key[:20]: {str(key)[:20]}...", flush=True)
        if isinstance(key, str):
            key = key.encode()
        self._fernet = Fernet(key)

    def encrypt(self, plaintext: str) -> str:
        """Chiffre une chaîne → retourne base64 (str)."""
        print(f"[DEBUG encrypt] plaintext: {plaintext[:20]}...", flush=True)
        result = self._fernet.encrypt(plaintext.encode()).decode()
        print(f"[DEBUG encrypt] result: {result[:50]}...", flush=True)
        return result

    def decrypt(self, ciphertext: str) -> str:
        """Déchiffre une chaîne base64 → retourne clair (str)."""
        print(f"[DEBUG decrypt] ciphertext: {ciphertext[:50]}...", flush=True)
        try:
            result = self._fernet.decrypt(ciphertext.encode()).decode()
            print(f"[DEBUG decrypt] result: {result[:20]}...", flush=True)
            return result
        except InvalidToken as exc:
            print("[DEBUG decrypt] InvalidToken!", flush=True)
            raise ValueError("déchiffrement invalide (clé ou données corrompues)") from exc


def build_cipher(settings: Settings) -> FernetCipher:
    """Construit le cipher depuis `ENCRYPTION_KEY` (validée dans Settings)."""
    return FernetCipher(settings.encryption_key)


__all__ = ["FernetCipher", "build_cipher"]
