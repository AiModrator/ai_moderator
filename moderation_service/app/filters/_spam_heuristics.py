"""Heuristiques textuelles du SpamFilter (main.md §5.1, H1–H5) — fonctions pures."""

from __future__ import annotations

import re

_UPPERCASE_LETTER_RE = re.compile(r"[A-Z]")
_LOWERCASE_LETTER_RE = re.compile(r"[a-z]")
_CHAR_REPETITION_RE = re.compile(r"(.)\1{6,}")
_EMOJI_RE = re.compile(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]")


def uppercase_ratio(raw: str) -> float | None:
    """H1 — ratio lettres majuscules / lettres ; None si aucune lettre."""
    upper = len(_UPPERCASE_LETTER_RE.findall(raw))
    lower = len(_LOWERCASE_LETTER_RE.findall(raw))
    total = upper + lower
    if total == 0:
        return None
    return upper / total


def has_char_repetition(raw: str) -> bool:
    """H2 — répétition d'un caractère 7 × consécutives ou plus."""
    return bool(_CHAR_REPETITION_RE.search(raw))


def has_link_flood(urls: list[str]) -> bool:
    """H3 — au moins 4 URLs dans le texte."""
    return len(urls) >= 4


def has_token_repeat(tokens: list[str]) -> bool:
    """H4 — ≥ 8 tokens et le token le plus fréquent ≥ 50 % des tokens."""
    if len(tokens) < 8:
        return False
    counts: dict[str, int] = {}
    for token in tokens:
        counts[token] = counts.get(token, 0) + 1
    most_frequent = max(counts.values())
    return most_frequent * 2 >= len(tokens)


def emoji_count(raw: str) -> int:
    """H5 — nombre de code points dans les plages emoji."""
    return len(_EMOJI_RE.findall(raw))


def compute_heuristics(
    *,
    raw: str,
    urls: list[str],
    tokens: list[str],
    min_chars: int = 20,
) -> list[str]:
    """Retourne les codes d'heuristiques déclenchées (aucune si texte < `min_chars`)."""
    if len(raw) < min_chars:
        return []
    triggered: list[str] = []
    ratio = uppercase_ratio(raw)
    if ratio is not None and ratio >= 0.70:
        triggered.append("H1")
    if has_char_repetition(raw):
        triggered.append("H2")
    if has_link_flood(urls):
        triggered.append("H3")
    if has_token_repeat(tokens):
        triggered.append("H4")
    if emoji_count(raw) >= 15:
        triggered.append("H5")
    return triggered


__all__ = [
    "uppercase_ratio",
    "has_char_repetition",
    "has_link_flood",
    "has_token_repeat",
    "emoji_count",
    "compute_heuristics",
]
