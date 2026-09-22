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

        # Extrait le contenu de l'utilisateur (dernier message user)
        user_content = self._extract_user_content(req.messages)

        # Détermine le score selon la convention
        score, raw_text = self._determine_score(user_content)

        # Simule un délai minimal
        latency_ms = (time.perf_counter() - t0) * 1000

        return ProviderResponse(
            raw_text=raw_text,
            input_tokens=self._estimate_input_tokens(req.messages),
            output_tokens=len(raw_text) // 4 + 1,
            latency_ms=latency_ms,
            model="test-model",
        )

    def _extract_user_content(self, messages: list[dict]) -> str:
        """Retourne le contenu du dernier message user, ou chaîne vide."""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                content = msg.get("content")
                if isinstance(content, str):
                    return content
                if isinstance(content, list):
                    # Format multi-part (texte + images)
                    for part in content:
                        if part.get("type") == "text":
                            return part.get("text", "")
        return ""

    def _determine_score(self, content: str) -> tuple[float, str]:
        """Applique les conventions de test au contenu."""
        # Convention __SCORE:X__
        if "__SCORE:" in content:
            import re

            match = re.search(r"__SCORE:([01](?:\.\d+)?)__", content)
            if match:
                score = float(match.group(1))
                return score, json.dumps(
                    {
                        "model": "test-model",
                        "choices": [
                            {
                                "message": {"content": json.dumps({"score": score, "reason": "test"})}
                            }
                        ],
                    }
                )

        # Convention __ERROR__
        if content == "__ERROR__":
            raise ProviderTransientError("Test provider: erreur simulée")

        # Convention __INVALID__
        if content == "__INVALID__":
            return 0.0, "not valid json at all {{{"

        # Défaut
        return 0.0, json.dumps(
            {"model": "test-model", "choices": [{"message": {"content": "0"}}]}
        )

    def _estimate_input_tokens(self, messages: list[dict]) -> int:
        """Estimation grossière : 1 token ≈ 4 caractères."""
        total_chars = sum(len(m.get("content", "")) for m in messages)
        return max(1, (total_chars + 3) // 4)


__all__ = ["TestProviderAdapter"]
