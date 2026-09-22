"""Endpoint de santé `GET /health` (main.md §2.3)."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorClient

from app.db import check_mongo

router = APIRouter()


@router.get("/health", tags=["health"])
async def health(request: Request) -> JSONResponse:
    mongo_client: AsyncIOMotorClient = request.app.state.mongo_client
    mongo_ok = await check_mongo(mongo_client)
    return JSONResponse(
        status_code=200 if mongo_ok else 503,
        content={
            "status": "ok" if mongo_ok else "degraded",
            "mongo": mongo_ok,
            "providers": ["openrouter", "test"],
        },
    )


__all__ = ["router"]
