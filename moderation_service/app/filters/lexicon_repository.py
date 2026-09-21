"""`LexiconRepository` — chargement / compilation des lexiques (main.md §5.3).

Ressources : `app/resources/lexicons/{RISK_CLASS}.txt`, une entrée par ligne
`pattern|SCORE`. `pattern` est un littéral (mot/expression) ou une regex si
préfixé `re:`. Lignes vides et commentaires `#` ignorés. Les regex sont
compilées avec frontières de mots `\b` et insensibles à la casse, avec cache
de compilation rafraîchi par TTL (`purge_caches()`).
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path

import structlog

from app.schemas.enums import RiskClass

RESOURCES_DIR = Path(__file__).resolve().parent.parent / "resources" / "lexicons"


@dataclass(frozen=True)
class LexiconPattern:
    """Pattern lexicographique compilé, avec son poids de base."""

    pattern: str
    score: float
    regex: re.Pattern[str]


class LexiconRepository:
    """Cache en mémoire des lexiques, chargés une fois puis rafraîchis par TTL."""

    def __init__(
        self,
        directory: str | Path = RESOURCES_DIR,
        *,
        cache_ttl_sec: float = 300.0,
        logger: structlog.stdlib.BoundLogger | None = None,
    ) -> None:
        self._dir = Path(directory)
        self._cache_ttl_sec = cache_ttl_sec
        self._logger = logger or structlog.get_logger()
        self._patterns: dict[RiskClass, list[LexiconPattern]] | None = None
        self._loaded_at: float | None = None

    def load(self) -> None:
        """Charge tous les fichiers `*.txt` du répertoire (échec de lecture → erreur)."""
        if not self._dir.is_dir():
            raise FileNotFoundError(f"lexicons directory not found: {self._dir}")
        loaded: dict[RiskClass, list[LexiconPattern]] = {}
        for path in sorted(self._dir.glob("*.txt")):
            risk_class = self._risk_class_from_filename(path.stem)
            if risk_class is None:
                self._logger.warning("lexicon_unknown_class", file=path.name)
                continue
            loaded[risk_class] = self._parse_file(path)
        self._patterns = loaded
        self._loaded_at = time.monotonic()

    def patterns_for(self, risk_class: RiskClass) -> list[LexiconPattern]:
        """Patterns compilés d'une classe (liste copiée, jamais partagée par mutation)."""
        self._ensure_loaded()
        return list(self._patterns.get(risk_class, []))

    def purge_caches(self) -> None:
        """Invalide le cache : le prochain `patterns_for` recharge les fichiers."""
        self._patterns = None
        self._loaded_at = None

    def _ensure_loaded(self) -> None:
        stale = self._patterns is not None and self._cache_ttl_sec > 0 and (
            time.monotonic() - (self._loaded_at or 0.0)
        ) > self._cache_ttl_sec
        if self._patterns is None or stale:
            self.load()

    @staticmethod
    def _risk_class_from_filename(stem: str) -> RiskClass | None:
        try:
            return RiskClass[stem.upper()]
        except KeyError:
            return None

    def _parse_file(self, path: Path) -> list[LexiconPattern]:
        patterns: list[LexiconPattern] = []
        for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            pattern, separator, score_str = line.rpartition("|")
            if not separator:
                self._logger.warning("lexicon_invalid_line", file=path.name, line=line_number)
                continue
            try:
                score = float(score_str)
            except ValueError:
                self._logger.warning("lexicon_invalid_score", file=path.name, line=line_number, value=score_str)
                continue
            if not 0.0 <= score <= 1.0:
                self._logger.warning("lexicon_score_out_of_range", file=path.name, line=line_number, value=score)
                continue
            regex = self._compile(pattern.strip())
            if regex is None:
                self._logger.warning("lexicon_invalid_regex", file=path.name, line=line_number, pattern=pattern)
                continue
            patterns.append(LexiconPattern(pattern=pattern.strip(), score=score, regex=regex))
        return patterns

    @staticmethod
    def _compile(pattern: str) -> re.Pattern[str] | None:
        body = pattern[3:] if pattern.startswith("re:") else re.escape(pattern)
        try:
            return re.compile(rf"\b(?:{body})\b", re.IGNORECASE)
        except re.error:
            return None


__all__ = ["LexiconRepository", "LexiconPattern", "RESOURCES_DIR"]
