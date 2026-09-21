"""`LinkFilter` — détection d'URLs dangereuses (main.md §5.2, signaux S1–S8)."""

from __future__ import annotations

import ipaddress
import re
from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from urllib.parse import urlparse

import structlog
from redis.asyncio import Redis

from app.core.text_normalizer import normalize_url
from app.filters.base import ItemFilter
from app.filters.registry import register_filter
from app.schemas.enums import FilterStatus, RiskClass, Source
from app.schemas.job import ContentItem
from app.schemas.result import Detection, FilterContext, FilterOutcome

_URL_SCHEME_RE = re.compile(r"https?://[^\s<>\"')\]}]+", re.IGNORECASE)
_BARE_DOMAIN_RE = re.compile(
    r"(?<![\w@.-])(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}(?::\d{1,5})?(?:/[^\s<>\"')\]}]*)?",
    re.IGNORECASE,
)

_BLOCKLIST_KEY = "mod:links:blocklist"

DEFAULT_SUSPICIOUS_TLDS = ("zip", "mov", "tk", "top", "xyz", "gq", "ml", "cf", "click", "work")

_SHORTENERS = frozenset(
    {"bit.ly", "tinyurl.com", "t.co", "goo.gl", "is.gd", "cutt.ly", "rb.gy", "shorturl.at"}
)
_BRAND_OFFICIAL = {
    "paypal": "paypal.com",
    "discord": "discord.com",
    "steam": "steampowered.com",
    "whop": "whop.com",
    "metamask": "metamask.io",
    "binance": "binance.com",
}
_OFFICIAL_DOMAINS = frozenset({*(_BRAND_OFFICIAL.values()), "steamcommunity.com"})
_KEYWORDS = frozenset({*_BRAND_OFFICIAL.keys(), "login", "verify", "wallet", "airdrop", "giveaway", "nitro"})


def _raw_urls(text: str) -> list[str]:
    """URLs brutes (schéma + domaines nus), sans doublon, ordre de première apparition."""
    scheme_matches = _URL_SCHEME_RE.findall(text)
    masked = _URL_SCHEME_RE.sub(" ", text)
    bare_matches = _BARE_DOMAIN_RE.findall(masked)
    return list(dict.fromkeys([*scheme_matches, *bare_matches]))


def _authority(raw: str) -> str:
    """Partie autorité d'une URL brute (utilisée pour S5 : `@`)."""
    match = re.match(r"^[a-z][a-z0-9+.-]*://", raw, re.IGNORECASE)
    rest = raw[match.end() :] if match else raw
    return rest.split("/", 1)[0].split("?", 1)[0].split("#", 1)[0]


def _script_mixed(host: str) -> bool:
    return "xn--" in host or any(ord(ch) > 0x7F for ch in host)


def _s6_trigger(host: str, path: str) -> bool:
    haystack = f"{host} {path}".casefold()
    if not any(keyword in haystack for keyword in _KEYWORDS):
        return False
    return not any(host == official or host.endswith("." + official) for official in _OFFICIAL_DOMAINS)


@dataclass(frozen=True)
class LinkAnalysis:
    """Signaux cumulés pour une URL (résultat interne de `_analyze`)."""

    url: str
    host: str
    malicious_signals: list[str] = field(default_factory=list)
    malicious_sum: float = 0.0
    phishing_signals: list[str] = field(default_factory=list)
    phishing_sum: float = 0.0


@register_filter
class LinkFilter(ItemFilter):
    """Détection d'URLs dangereuses : signaux additifs §5.2, agrégés par classe.

    - `MALICIOUS_LINK` ← somme S1, S3, S4, S7, S8.
    - `PHISHING` ← somme S2, S5, S6.
    - Hôtes allowlistés (et sous-domaines) → URL ignorée.
    - Blocklist Redis (`SISMEMBER`) optionnelle et non bloquante : Redis KO → S8
      ignoré + log `debug`, aucune `TransientFilterError`.
    """

    NAME = "LinkFilter"
    HANDLED_CLASSES = frozenset({RiskClass.MALICIOUS_LINK, RiskClass.PHISHING})

    def __init__(
        self,
        *,
        allowlist: Iterable[str] | None = None,
        suspicious_tlds: Iterable[str] | None = None,
        redis: Redis | None = None,
        timeout_sec: float = 10.0,
    ) -> None:
        self._redis = redis
        self._allowlist = {domain.casefold().lstrip(".") for domain in (allowlist or [])}
        self._suspicious_tlds = {tld.casefold().lstrip(".") for tld in (suspicious_tlds or DEFAULT_SUSPICIOUS_TLDS)}
        self.TIMEOUT_SEC = timeout_sec
        self._logger = structlog.get_logger()

    def is_applicable(self, item: ContentItem) -> bool:
        if item.text is None or not item.text.strip():
            return False
        return bool(_raw_urls(item.text))

    async def evaluate(self, item: ContentItem, ctx: FilterContext) -> FilterOutcome:
        content_id = item.content_id
        if item.text is None or not item.text.strip():
            return FilterOutcome(content_id=content_id, status=FilterStatus.SKIPPED)

        raw_urls = _raw_urls(item.text)
        if not raw_urls:
            return FilterOutcome(content_id=content_id, status=FilterStatus.SKIPPED)

        analyses = [self._analyze(raw) for raw in raw_urls]
        analyses = [a for a in analyses if a is not None]

        blocked = await self._blocked_hosts({a.host for a in analyses})
        analyses = [
            replace(
                analysis,
                malicious_signals=[*analysis.malicious_signals, "S8"],
                malicious_sum=analysis.malicious_sum + 1.0,
            )
            if analysis.host in blocked
            else analysis
            for analysis in analyses
        ]

        best_malicious = max((a for a in analyses), key=lambda a: a.malicious_sum, default=None)
        best_phishing = max((a for a in analyses), key=lambda a: a.phishing_sum, default=None)

        detections: list[Detection] = []
        if RiskClass.MALICIOUS_LINK in ctx.target_classes and best_malicious and best_malicious.malicious_sum > 0:
            score = min(best_malicious.malicious_sum, 1.0)
            detections.append(
                Detection(
                    risk_class=RiskClass.MALICIOUS_LINK,
                    score=score,
                    source=Source.TEXT,
                    filter=self.NAME,
                    detail=f"url={best_malicious.url} signals={best_malicious.malicious_signals}",
                )
            )
        if RiskClass.PHISHING in ctx.target_classes and best_phishing and best_phishing.phishing_sum > 0:
            score = min(best_phishing.phishing_sum, 1.0)
            detections.append(
                Detection(
                    risk_class=RiskClass.PHISHING,
                    score=score,
                    source=Source.TEXT,
                    filter=self.NAME,
                    detail=f"url={best_phishing.url} signals={best_phishing.phishing_signals}",
                )
            )
        return FilterOutcome(content_id=content_id, status=FilterStatus.COMPLETED, detections=detections)

    def _analyze(self, raw: str) -> LinkAnalysis | None:
        normalized = normalize_url(raw)
        parsed = urlparse(normalized)
        host = (parsed.hostname or "").casefold()
        path = parsed.path or ""

        if not host or host in self._allowlist or any(host.endswith("." + domain) for domain in self._allowlist):
            return None

        malicious: list[str] = []
        malicious_sum = 0.0
        phishing: list[str] = []
        phishing_sum = 0.0

        if self._is_ip(host):
            malicious.append("S1")
            malicious_sum += 0.50
        if _script_mixed(host):
            phishing.append("S2")
            phishing_sum += 0.50
        if self._is_shortener(host):
            malicious.append("S3")
            malicious_sum += 0.30
        if self._suspicious_tld(host):
            malicious.append("S4")
            malicious_sum += 0.30
        if "@" in _authority(raw):
            phishing.append("S5")
            phishing_sum += 0.60
        if _s6_trigger(host, path):
            phishing.append("S6")
            phishing_sum += 0.50
        if self._deep_subdomain(host):
            malicious.append("S7")
            malicious_sum += 0.20

        return LinkAnalysis(
            url=normalized,
            host=host,
            malicious_signals=malicious,
            malicious_sum=malicious_sum,
            phishing_signals=phishing,
            phishing_sum=phishing_sum,
        )

    async def _blocked_hosts(self, hosts: set[str]) -> set[str]:
        if not hosts or self._redis is None:
            return set()
        try:
            pipe = self._redis.pipeline()
            for host in hosts:
                pipe.sismember(_BLOCKLIST_KEY, host)
            results = await pipe.execute()
            return {host for host, is_member in zip(hosts, results, strict=False) if is_member}
        except Exception:  # Redis KO → S8 ignoré, non bloquant (main.md §5.2)
            self._logger.debug("link_blocklist_unavailable", filter="LinkFilter")
            return set()

    @staticmethod
    def _is_ip(host: str) -> bool:
        try:
            ipaddress.ip_address(host)
        except ValueError:
            return False
        return True

    def _is_shortener(self, host: str) -> bool:
        return any(host == shortener or host.endswith("." + shortener) for shortener in _SHORTENERS)

    def _suspicious_tld(self, host: str) -> bool:
        if "." not in host:
            return False
        return host.rsplit(".", 1)[1] in self._suspicious_tlds

    @staticmethod
    def _deep_subdomain(host: str) -> bool:
        depth = len(host.split(".")) - 2
        return depth >= 4


__all__ = ["LinkFilter", "LinkAnalysis", "_raw_urls"]
