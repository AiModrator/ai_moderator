"""Repository pour les modèles (collection `models` - Model Registry)."""

from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorCollection

from app.schemas.providers import ModelDocument


def _doc_to_model(doc: dict) -> ModelDocument:
    """Convertit un document MongoDB en ModelDocument."""
    data = {k: v for k, v in doc.items() if k != "_id"}
    return ModelDocument.model_validate(data)


class ModelRepository:
    """Accès à la collection `models` (Model Registry)."""

    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        self._col = collection

    async def create(self, model: ModelDocument) -> ModelDocument:
        """Crée un modèle (id unique)."""
        doc = model.model_dump(by_alias=True)
        await self._col.insert_one(doc)
        return model

    async def get(self, model_id: str) -> ModelDocument | None:
        doc = await self._col.find_one({"id": model_id})
        return _doc_to_model(doc) if doc else None

    async def find_enabled(self) -> list[ModelDocument]:
        """Retourne tous les modèles enabled, triés par priority puis costInput."""
        cursor = self._col.find({"enabled": True}).sort([("priority", 1), ("costInput", 1)])
        models: list[ModelDocument] = []
        async for doc in cursor:
            models.append(_doc_to_model(doc))
        return models

    async def update(
        self,
        model_id: str,
        *,
        display_name: str | None = None,
        capabilities: list | None = None,
        tasks: list | None = None,
        max_input_tokens: int | None = None,
        max_output_tokens: int | None = None,
        cost_input: float | None = None,
        cost_output: float | None = None,
        priority: int | None = None,
        enabled: bool | None = None,
    ) -> ModelDocument | None:
        """Met à jour un modèle."""
        update: dict = {}
        if display_name is not None:
            update["displayName"] = display_name
        if capabilities is not None:
            update["capabilities"] = capabilities
        if tasks is not None:
            update["tasks"] = tasks
        if max_input_tokens is not None:
            update["maxInputTokens"] = max_input_tokens
        if max_output_tokens is not None:
            update["maxOutputTokens"] = max_output_tokens
        if cost_input is not None:
            update["costInput"] = cost_input
        if cost_output is not None:
            update["costOutput"] = cost_output
        if priority is not None:
            update["priority"] = priority
        if enabled is not None:
            update["enabled"] = enabled
        if not update:
            return await self.get(model_id)
        await self._col.update_one({"id": model_id}, {"$set": update})
        return await self.get(model_id)

    async def delete(self, model_id: str) -> bool:
        """Désactive un modèle (soft delete via enabled=False)."""
        doc = await self._col.find_one({"id": model_id})
        if not doc:
            return False
        if doc.get("enabled", True):
            result = await self._col.update_one({"id": model_id}, {"$set": {"enabled": False}})
            return result.modified_count > 0
        return True  # déjà désactivé, considéré comme supprimé


__all__ = ["ModelRepository"]
