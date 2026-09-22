"""Client MongoDB async (motor) et vérification de dépendance."""

from __future__ import annotations

import asyncio

import motor.motor_asyncio as motor

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


__all__ = ["create_mongo_client", "get_database", "check_mongo"]
