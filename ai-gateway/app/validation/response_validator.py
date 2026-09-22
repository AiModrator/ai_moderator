"""Validateur de réponse LLM (main.md §5.6).

Extrait, valide et coerce la sortie brute du LLM avant renvoi.
"""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import ValidationError

from app.errors import InvalidResponseError
from app.schemas.moderation import ModerationResponse, ResultItem


class ResponseValidator:
    """Valide et coerce la réponse brute du LLM.

    Règles (§5.6) :
    - Extraction du premier objet JSON valide (tolérance texte autour).
    - Schéma : `{ "results": [ { "id": str, "score": float, "reason": str } ] }`
    - `score` non-numérique → `InvalidResponseError`
    - `id` absent → entrée ignorée (log warning)
    - Item de la requête absent de `results` → score 0
    - `score` hors [0,1] → clamp dans [0,1]
    """

    def validate(
        self,
        raw_text: str,
        expected_ids: list[str],
    ) -> ModerationResponse:
        """Valide la réponse brute et retourne une `ModerationResponse`."""
        # 1. Extraction JSON
        parsed = self._extract_json(raw_text)

        # 2. Prétraitement : nettoyage des résultats avant validation Pydantic
        cleaned_parsed = self._pre_process_results(parsed)

        # 3. Validation schéma
        try:
            response = ModerationResponse.model_validate(cleaned_parsed)
        except ValidationError as exc:
            raise InvalidResponseError(f"Schéma invalide: {exc}") from exc

        # 4. Post-traitement : mapping id → score, clamp, items manquants
        return self._post_process(response, expected_ids)

    def _extract_json(self, text: str) -> dict[str, Any]:
        """Extrait le premier objet JSON valide d'un texte."""
        # Tentative 1 : JSON direct
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Tentative 2 : premier objet JSON {...} (regex non-gourmande)
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        raise InvalidResponseError("Aucun JSON valide trouvé dans la réponse")

    def _pre_process_results(self, parsed: dict[str, Any]) -> dict[str, Any]:
        """Nettoie les résultats avant validation Pydantic :
        - Filtre les items sans `id`
        - Déduplique par `id` (garde le premier)
        - Clamp `score` dans [0,1] (convertit non-numériques en erreur)
        """
        if "results" not in parsed or not isinstance(parsed["results"], list):
            return parsed

        seen_ids: set[str] = set()
        cleaned_results: list[dict] = []

        for item in parsed["results"]:
            if not isinstance(item, dict):
                continue
            item_id = item.get("id")
            if not item_id or not isinstance(item_id, str):
                # id absent ou invalide → ignorer
                continue
            if item_id in seen_ids:
                # Déjà vu → ignorer les doublons (garde le premier)
                continue
            seen_ids.add(item_id)

            # Clamp score
            score = item.get("score")
            if isinstance(score, (int, float)):
                score = max(0.0, min(1.0, float(score)))
            elif isinstance(score, str):
                try:
                    score = max(0.0, min(1.0, float(score)))
                except ValueError as exc:
                    raise InvalidResponseError(f"Score non-numérique: {score}") from exc
            else:
                # Type non géré → erreur
                raise InvalidResponseError(f"Score invalide: {score!r}")

            cleaned_item = dict(item)
            cleaned_item["score"] = score
            # Ensure required fields
            if "reason" not in cleaned_item:
                cleaned_item["reason"] = None
            cleaned_results.append(cleaned_item)

        # Reconstruire le dict nettoyé
        cleaned = dict(parsed)
        cleaned["results"] = cleaned_results
        return cleaned

    def _post_process(
        self, response: ModerationResponse, expected_ids: list[str]
    ) -> ModerationResponse:
        """Applique les règles de validation post-schéma."""
        results_by_id = {item.id: item for item in response.results}

        processed: list[ResultItem] = []
        seen_ids: set[str] = set()

        for expected_id in expected_ids:
            if expected_id in seen_ids:
                continue
            seen_ids.add(expected_id)

            if expected_id in results_by_id:
                item = results_by_id[expected_id]
                # Score déjà clampé par _pre_process_results
                processed.append(
                    ResultItem(
                        id=item.id,
                        score=item.score,
                        reason=item.reason,
                    )
                )
            else:
                # Item manquant → score 0
                processed.append(
                    ResultItem(id=expected_id, score=0.0, reason="absent from response")
                )

        return ModerationResponse(
            model=response.model,
            results=processed,
        )


__all__ = ["ResponseValidator"]
