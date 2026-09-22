"""Repository pour les fournisseurs (collection `providers`).

Gère le chiffrement/déchiffrement des clés API via Fernet.
"""

from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorCollection

from app.config.security import FernetCipher
from app.schemas.providers import ProviderDocument, ProviderKind


def _doc_to_provider(doc: dict, cipher: FernetCipher | None = None, mask_key: bool = False) -> ProviderDocument:
    """Convertit un document MongoDB en ProviderDocument."""
    data = {k: v for k, v in doc.items() if k != "_id"}
    if mask_key:
        data["apiKeyEncrypted"] = "***" if data.get("apiKeyEncrypted") else None
    elif cipher and data.get("apiKeyEncrypted"):
        data["apiKeyEncrypted"] = cipher.decrypt(data["apiKeyEncrypted"])
    return ProviderDocument.model_validate(data)


class ProviderRepository:
    """Accès à la collection `providers` avec chiffrement des clés."""

    def __init__(self, collection: AsyncIOMotorCollection, cipher: FernetCipher) -> None:
        self._col = collection
        self._cipher = cipher

    async def create(
        self,
        *,
        name: str,
        kind: ProviderKind,
        display_name: str,
        base_url: str,
        api_key: str | None = None,
        enabled: bool = True,
    ) -> ProviderDocument:
        """Crée un provider ; chiffre `api_key` si fourni."""
        print(f"[DEBUG create] cipher id: {id(self._cipher)}", flush=True)
        doc = {
            "name": name,
            "kind": kind.value,
            "displayName": display_name,
            "baseUrl": base_url,
            "apiKeyEncrypted": self._cipher.encrypt(api_key) if api_key else None,
            "enabled": enabled,
        }
        await self._col.insert_one(doc)
        return _doc_to_provider(doc)

    async def get(self, name: str) -> ProviderDocument | None:
        """Récupère un provider ; masque la clé pour l'admin."""
        doc = await self._col.find_one({"name": name})
        if not doc:
            return None
        return _doc_to_provider(doc, mask_key=True)

    async def get_active(self, name: str) -> ProviderDocument | None:
        """Récupère un provider activé ; clé **déchiffrée** pour l'adaptateur."""
        doc = await self._col.find_one({"name": name, "enabled": True})
        if not doc:
            return None
        return _doc_to_provider(doc, cipher=self._cipher)

    async def find_enabled(self) -> list[ProviderDocument]:
        """Retourne les providers enabled avec la clé **déchiffrée** pour l'adaptateur."""
        cursor = self._col.find({"enabled": True})
        providers: list[ProviderDocument] = []
        async for doc in cursor:
            providers.append(_doc_to_provider(doc, cipher=self._cipher))
        return providers

    async def update(
        self,
        name: str,
        *,
        display_name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        enabled: bool | None = None,
    ) -> ProviderDocument | None:
        """Met à jour un provider ; chiffre la nouvelle clé si fournie."""
        update: dict = {}
        if display_name is not None:
            update["displayName"] = display_name
        if base_url is not None:
            update["baseUrl"] = base_url
        if api_key is not None:
            update["apiKeyEncrypted"] = self._cipher.encrypt(api_key)
        if enabled is not None:
            update["enabled"] = enabled
        if not update:
            return await self.get(name)
        await self._col.update_one({"name": name}, {"$set": update})
        return await self.get(name)

    async def delete(self, name: str) -> bool:
        """Supprime un provider (soft delete via enabled=False)."""
        result = await self._col.update_one({"name": name}, {"$set": {"enabled": False}})
        return result.modified_count > 0


__all__ = ["ProviderRepository"]
