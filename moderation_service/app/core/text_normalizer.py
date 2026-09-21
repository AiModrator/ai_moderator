"""Normalisation de texte partagée (main.md §5.0) — fonction pure, sans I/O."""

from __future__ import annotations

import html
import re
import unicodedata
from dataclasses import dataclass, field
from urllib.parse import urlparse

_HTML_TAG_RE = re.compile(r"<[^<>]*>")
_CONTROL_RE = re.compile(r"[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f\u0080-\u009f\u200b-\u200f\ufeff\u2028\u2029]")
_WHITESPACE_RE = re.compile(r"\s+")

_URL_SCHEME_RE = re.compile(r"https?://[^\s<>\"')\]}]+", re.IGNORECASE)
_BARE_DOMAIN_RE = re.compile(r"(?<![\w@.-])(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}(?::\d{1,5})?(?:/[^\s<>\"')\]}]*)?", re.IGNORECASE)

_LEET_MAP = str.maketrans(
    {
        "@": "a",
        "4": "a",
        "3": "e",
        "1": "i",
        "!": "i",
        "0": "o",
        "$": "s",
        "5": "s",
        "7": "t",
    }
)
_TOKENS_SPLIT_RE = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class NormalizedText:
    """Résultat de `normalize()` (§5.0)."""

    raw: str
    lower: str
    deobfuscated: str
    urls: list[str] = field(default_factory=list)
    tokens: list[str] = field(default_factory=list)


def _decode_and_strip_html(text: str) -> str:
    """Décode les entités HTML puis supprime les balises (étapes 1 et 2)."""
    text = html.unescape(text)
    text = _HTML_TAG_RE.sub(" ", text)
    return text


def _clean_unicode(text: str) -> str:
    """NFKC + suppression caractères de contrôle et zero-width (étape 3)."""
    text = unicodedata.normalize("NFKC", text)
    text = _CONTROL_RE.sub("", text)
    return text


def normalize_url(raw_url: str) -> str:
    """Normalise une URL trouvée dans le texte (§5.2) : hôte en minuscules, fragment retiré.

    - Schéma absent → `http://` ajouté.
    - Hôte lowercased (`urllib.parse`).
    - Fragment (`#...`) supprimé.
    - Trailing `/` supprimé.
    """
    url = raw_url.strip()
    if not url:
        return url
    if not re.match(r"^[a-z][a-z0-9+.-]*://", url, re.IGNORECASE):
        url = "http://" + url
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return url
    host = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port else ""
    path = parsed.path if parsed.path != "/" else ""
    query = f"?{parsed.query}" if parsed.query else ""
    # netloc = host basé sur hostname (sans userinfo, sans casse), réencodage du chemin.
    rebuilt = f"{parsed.scheme}://{host}{port}{path}{query}"
    return rebuilt


def extract_urls(text: str) -> list[str]:
    """Extrait les URLs (schéma ou domaine nu) et les normalise, sans doublon.

    Les domaines nus sont cherchés dans une copie du texte où les URLs à schéma
    ont été masquées, pour ne pas re-détecter `a.com` dans `https://a.com/…`.
    """
    scheme_matches = _URL_SCHEME_RE.findall(text)
    masked = _URL_SCHEME_RE.sub(" ", text)
    bare_matches = _BARE_DOMAIN_RE.findall(masked)
    seen: set[str] = set()
    urls: list[str] = []
    for raw in [*scheme_matches, *bare_matches]:
        normalized = normalize_url(raw)
        if normalized and normalized not in seen:
            seen.add(normalized)
            urls.append(normalized)
    return urls


def tokens_of(lower: str) -> list[str]:
    """Découpe `lower` sur les non-alphanumériques (§5.0)."""
    return [t for t in _TOKENS_SPLIT_RE.split(lower) if t]


def deobfuscate(lower: str) -> str:
    """Remplace le leetspeak et supprime les séparateurs intra-mot (§5.0).

    - `@→a`, `4→a`, `3→e`, `1/!→i`, `0→o`, `$/5→s`, `7→t`.
    - `.`/`-`/`_` supprimés (intra-mot : `f.u.c.k` → `fuck`).
    - Espaces de lettres isolées retirés (`f u c k` → `fuck`), pas les mots normaux.
    """
    result = lower.translate(_LEET_MAP)
    result = result.replace(".", "").replace("-", "").replace("_", "")
    words = result.split()
    if len(words) >= 3 and all(len(w) == 1 for w in words):
        result = "".join(words)
    return result


def normalize(text: str) -> NormalizedText:
    """Normalise un texte (§5.0) : raw, lower, deobfuscated, urls, tokens."""
    raw = _decode_and_strip_html(text)
    raw = _clean_unicode(raw)
    raw = _WHITESPACE_RE.sub(" ", raw).strip()
    lower = raw.casefold()
    return NormalizedText(
        raw=raw,
        lower=lower,
        deobfuscated=deobfuscate(lower),
        urls=extract_urls(raw),
        tokens=tokens_of(lower),
    )


__all__ = ["NormalizedText", "normalize", "normalize_url", "extract_urls", "deobfuscate", "tokens_of"]
