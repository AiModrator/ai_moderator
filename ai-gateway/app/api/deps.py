"""Dépendances d'authentification pour l'AI Gateway (main.md §7)."""

from __future__ import annotations

import secrets

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config.settings import Settings


async def require_gateway_key(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False)),
    settings: Settings = Depends(lambda: Request.app.state.settings),
) -> None:
    """Vérifie l'en-tête `Authorization: Bearer <GATEWAY_API_KEY>`.

    - 401 si header absent, format invalide ou clé incorrecte.
    - Comparaison en temps constant (`secrets.compare_digest`).
    """
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not secrets.compare_digest(credentials.credentials, settings.gateway_api_key):
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )


__all__ = ["require_gateway_key"]
