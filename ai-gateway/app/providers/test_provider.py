"""Fournisseur Test déterministe (main.md §5.3).

Aucun appel réseau, aucune clé. Traite un `ProviderRequest` complet
(prompt déjà construit) et renvoie un `ProviderResponse` déterministe.
"""

from __future__ import annotations

import json
import time
from typing import Any

from app.errors import ProviderTransientError
from app.providers.base import ProviderAdapter, ProviderRequest, ProviderResponse, RetryPolicy


class TestProviderAdapter(ProviderAdapter):
    """Provider de test — comportement déterministe selon le contenu.

    Conventions :
    - Contenu contenant `__SCORE:{0..1}__` → renvoie ce score.
    - Contenu == `"__ERROR__"` → lève `ProviderTransientError`.
    - Contenu == `"__INVALID__"` → renvoie un texte non-JSON (pour tester le validator).
    - Sinon → score 0.
    """

    KIND = "test"

    def __init__(
        self,
        config: Any,  # inutilisé (pas de clé)
        client: Any,  # inutilisé
        retry: RetryPolicy,
    ) -> None:
        super().__init__(config, client, retry)

    async def run(self, req: ProviderRequest) -> ProviderResponse:
        """Extrait le contenu du prompt utilisateur et applique les conventions."""
        t0 = time.perf_counter()

        # Extrait les items (id + texte) du dernier message user
        items = self._extract_user_items(req.messages)

        # Détermine le score selon la convention
        score, raw_text = self._determine_score(items)

        # Simule un délai minimal
        latency_ms = (time.perf_counter() - t0) * 1000

        return ProviderResponse(
            raw_text=raw_text,
            input_tokens=self._estimate_input_tokens(req.messages),
            output_tokens=len(raw_text) // 4 + 1,
            latency_ms=latency_ms,
            model="test-model",
        )

    def _extract_user_items(self, messages: list[dict]) -> list[dict]:
        """Récupère la liste `[{id, text}]` envoyée dans le dernier message user."""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                content = msg.get("content")
                if isinstance(content, str):
                    try:
                        data = json.loads(content)
                        if isinstance(data, list):
                            return [{"id": i.get("id", ""), "text": i.get("text", "") or ""} for i in data]
                    except json.JSONDecodeError:
                        return [{"id": "", "text": content}]
                if isinstance(content, list):
                    # Format multi-part (texte + images)
                    for part in content:
                        if part.get("type") == "text":
                            text = part.get("text", "")
                            return [{"id": "", "text": text}]
        return []

    def _determine_score(self, items: list[dict]) -> tuple[float, str]:
        """Applique les conventions de test au contenu.

        Réponse au format attendu par `ResponseValidator` :
        `{"results": [{"id", "score", "reason"}]}`.
        """
        joined = " ".join(i.get("text", "") for i in items)

        # Convention __ERROR__
        if joined.strip() == "__ERROR__":
            raise ProviderTransientError("Test provider: erreur simulée")

        # Convention __INVALID__
        if "__INVALID__" in joined:
            return 0.0, "not valid json at all {{{"

        # Convention __SCORE:X__ → score fixé, sinon 0 pour chaque item
        if "__SCORE:" in joined:
            import re

            match = re.search(r"__SCORE:([01](?:\.\d+)?)__", joined)
            score = float(match.group(1)) if match else 0.0
        else:
            score = 0.0

        results = [
            {"id": item["id"] or f"item-{i}", "score": score, "reason": "test"}
            for i, item in enumerate(items)
        ]
        if not results:
            results = [{"id": "unknown", "score": score, "reason": "test"}]

        # raw_text = contenu LLM direct (équivalent choices[0].message.content d'OpenRouter)
        return score, json.dumps({"results": results}, ensure_ascii=False)

    def _estimate_input_tokens(self, messages: list[dict]) -> int:
        """Estimation grossière : 1 token ≈ 4 caractères."""
        total_chars = sum(len(m.get("content", "")) for m in messages)
        return max(1, (total_chars + 3) // 4)


__all__ = ["TestProviderAdapter"]
