"""Configuration de la journalisation structurée (structlog, stdout uniquement)."""

from __future__ import annotations

import logging
import sys

import structlog

from app.config.settings import Settings


def configure_logging(settings: Settings) -> None:
    """Configure structlog (format `json` ou `console`, niveau `LOG_LEVEL`) sur stdout."""
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            (
                structlog.processors.JSONRenderer()
                if settings.log_format == "json"
                else structlog.dev.ConsoleRenderer()
            ),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )


def get_logger() -> structlog.stdlib.BoundLogger:
    """Retourne un logger structlog (contexte lié via contextvars)."""
    return structlog.get_logger()


__all__ = ["configure_logging", "get_logger"]
