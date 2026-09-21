"""Instanciation des filtres du pipeline depuis `Settings` (main.md §4.2).

Résout les dépendances d'infrastructure des filtres réels (Redis, AI Gateway,
LexiconRepository) à partir de la configuration. En test, la factory par défaut
se contente d'instancier les classes sans argument (filtres de test).
"""

from __future__ import annotations

from redis.asyncio import Redis

from app.clients.ai_gateway import AIGatewayClient
from app.config.settings import Settings
from app.filters.base import BaseFilter
from app.filters.image_ai_filter import ImageAIFilter
from app.filters.lexicon_filter import LexiconFilter
from app.filters.lexicon_repository import LexiconRepository
from app.filters.link_filter import LinkFilter
from app.filters.spam_filter import SpamFilter
from app.filters.text_ai_filter import TextAIFilter


class FilterFactory:
    """Fabrique d'instances de filtres à partir de la config du service."""

    def __init__(
        self,
        settings: Settings,
        *,
        redis: Redis | None = None,
        gateway: AIGatewayClient | None = None,
        lexicon: LexiconRepository | None = None,
    ) -> None:
        self._settings = settings
        self._redis = redis
        self._gateway = gateway
        self._lexicon = lexicon

    def build(self, cls: type[BaseFilter]) -> BaseFilter:
        """Construit l'instance réelle du filtre ; repli `cls()` pour les filtres de test."""
        name = cls.NAME
        s = self._settings
        if name == "SpamFilter":
            return SpamFilter(
                self._redis,
                dup_window_sec=s.spam_dup_window_sec,
                flood_window_sec=s.spam_flood_window_sec,
                flood_threshold=s.spam_flood_threshold,
                timeout_sec=s.filter_timeout_sec,
            )
        if name == "LinkFilter":
            return LinkFilter(
                allowlist=s.link_allowlist_domains,
                suspicious_tlds=s.link_suspicious_tlds,
                redis=self._redis,
                timeout_sec=s.filter_timeout_sec,
            )
        if name == "LexiconFilter":
            repository = self._lexicon or LexiconRepository()
            return LexiconFilter(
                repository,
                max_score=s.lexicon_max_score,
                timeout_sec=s.filter_timeout_sec,
            )
        if name in ("TextAIFilter", "ImageAIFilter"):
            gateway = self._gateway or AIGatewayClient(
                s.ai_gateway_url,
                api_key=s.ai_gateway_api_key,
                timeout_sec=s.ai_request_timeout_sec,
                max_parallel=s.ai_max_parallel_requests,
            )
            if name == "TextAIFilter":
                return TextAIFilter(
                    gateway,
                    min_chars=s.ai_text_min_chars,
                    batch_size=s.ai_text_batch_size,
                    max_chars_per_item=s.ai_text_max_chars_per_item,
                    timeout_sec=s.filter_timeout_sec,
                )
            return ImageAIFilter(gateway, max_images_per_item=s.max_images_per_item, timeout_sec=s.filter_timeout_sec)
        return cls()


def default_filter_factory(settings: Settings, *, redis: Redis | None = None) -> FilterFactory:
    """Fabrique prête pour la production (Redis requis pour SpamFilter/LinkFilter)."""
    return FilterFactory(settings, redis=redis)


__all__ = ["FilterFactory", "default_filter_factory"]
