"""Client MongoDB async (motor) et vérification de dépendance."""

from __future__ import annotations

import asyncio

import motor.motor_asyncio as motor
from pymongo import ASCENDING, DESCENDING

from app.config.settings import Settings


def create_mongo_client(settings: Settings) -> motor.AsyncIOMotorClient:
    """Construit le client `motor` depuis la configuration."""
    return motor.AsyncIOMotorClient(settings.mongodb_uri)


def get_database(client: motor.AsyncIOMotorClient, settings: Settings) -> motor.AsyncIOMotorDatabase:
    """Retourne la base de données configurée."""
    return client[settings.mongodb_db]


async def check_mongo(client: motor.AsyncIOMotorClient, timeout_sec: float = 2.0) -> bool:
    """PING MongoDB ; True si joignable, False sinon (aucune exception ne sort)."""
    try:
        await asyncio.wait_for(client.admin.command("ping"), timeout=timeout_sec)
        return True
    except Exception:
        return False


async def ensure_indexes(db: motor.AsyncIOMotorDatabase, settings: Settings) -> None:
    """Crée les index requis sur les collections (idempotent)."""
    # providers : unique name
    await db.providers.create_index("name", unique=True)
    # models : unique id
    await db.models.create_index("id", unique=True)
    # budgets : unique accountId
    await db.budgets.create_index("accountId", unique=True)
    # usage : index composé {accountId: 1, timestamp: -1} + TTL
    await db.usage.create_index([("accountId", ASCENDING), ("timestamp", DESCENDING)])
    await db.usage.create_index(
        "timestamp",
        expireAfterSeconds=settings.usage_retention_days * 24 * 3600,
    )


__all__ = [
    "check_mongo",
    "create_mongo_client",
    "get_database",
    "ensure_indexes",
]
