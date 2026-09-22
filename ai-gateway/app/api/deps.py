"""Dépendances d'authentification pour l'AI Gateway (main.md §7)."""

from __future__ import annotations

import secrets

from fastapi import Depends, Header, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config.settings import Settings


# Module-level singletons to avoid B008
_bearer_scheme = HTTPBearer(auto_error=False)


async def _get_settings(request: Request) -> Settings:
    return request.app.state.settings


async def require_gateway_key(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    settings: Settings = Depends(_get_settings),
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


async def require_admin_key(
    x_admin_key: str = Header(..., alias="X-Admin-Key"),
    settings: Settings = Depends(_get_settings),
) -> None:
    """Vérifie l'en-tête `X-Admin-Key`.

    - 401 si header absent ou clé incorrecte.
    - Comparaison en temps constant (`secrets.compare_digest`).
    """
    if not x_admin_key or not secrets.compare_digest(x_admin_key, settings.admin_api_key):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing X-Admin-Key header",
        )


__all__ = ["require_gateway_key", "require_admin_key"]
