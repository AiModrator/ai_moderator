"""Package API."""

from __future__ import annotations

from app.api.health import router as health_router

__all__ = ["health_router"]
