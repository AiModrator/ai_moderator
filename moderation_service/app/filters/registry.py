"""Registre des filtres : nom → classe (main.md §4.2)."""

from __future__ import annotations

from app.filters.base import BaseFilter

FILTER_REGISTRY: dict[str, type[BaseFilter]] = {}


def register_filter(cls: type[BaseFilter]) -> type[BaseFilter]:
    """Enregistre une classe de filtre dans le registre global (par `NAME`)."""
    name = cls.NAME
    if not name:
        raise ValueError(f"{cls.__name__} must define NAME")
    if name in FILTER_REGISTRY:
        raise ValueError(f"duplicate filter registration: {name}")
    FILTER_REGISTRY[name] = cls
    return cls


def get_filters() -> list[type[BaseFilter]]:
    """Retourne les classes de filtres enregistrées, dans l'ordre d'enregistrement."""
    return list(FILTER_REGISTRY.values())


__all__ = ["FILTER_REGISTRY", "register_filter", "get_filters"]
