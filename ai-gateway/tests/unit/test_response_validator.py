"""Tests unitaires du `ResponseValidator` (main.md §5.6)."""

from __future__ import annotations

import pytest

from app.errors import InvalidResponseError
from app.schemas.moderation import ModerationResponse
from app.validation.response_validator import ResponseValidator


class TestResponseValidator:
    def setup_method(self) -> None:
        self.validator = ResponseValidator()

    @pytest.mark.asyncio
    async def test_valid_json_direct(self) -> None:
        raw = '{"model": "m", "results": [{"id": "c-1", "score": 0.9, "reason": "ok"}]}'
        resp = self.validator.validate(raw, ["c-1"])
        assert isinstance(resp, ModerationResponse)
        assert resp.results[0].id == "c-1"
        assert resp.results[0].score == 0.9

    @pytest.mark.asyncio
    async def test_json_with_surrounding_text(self) -> None:
        raw = "Voici la réponse :\n```json\n{\"model\": \"m\", \"results\": [{\"id\": \"c-1\", \"score\": 0.8}]}\n```"
        resp = self.validator.validate(raw, ["c-1"])
        assert resp.results[0].score == 0.8

    @pytest.mark.asyncio
    async def test_score_clamped_above_1(self) -> None:
        raw = '{"model": "m", "results": [{"id": "c-1", "score": 1.5}]}'
        resp = self.validator.validate(raw, ["c-1"])
        assert resp.results[0].score == 1.0

    @pytest.mark.asyncio
    async def test_score_clamped_below_0(self) -> None:
        raw = '{"model": "m", "results": [{"id": "c-1", "score": -0.5}]}'
        resp = self.validator.validate(raw, ["c-1"])
        assert resp.results[0].score == 0.0

    @pytest.mark.asyncio
    async def test_non_numeric_score_error(self) -> None:
        raw = '{"model": "m", "results": [{"id": "c-1", "score": "very high"}]}'
        with pytest.raises(InvalidResponseError):
            self.validator.validate(raw, ["c-1"])

    @pytest.mark.asyncio
    async def test_missing_id_ignored(self) -> None:
        raw = '{"model": "m", "results": [{"score": 0.9}]}'
        # L'item sans id est ignoré (warning loggé mais pas d'erreur)
        resp = self.validator.validate(raw, ["c-1"])
        assert resp.results[0].score == 0.0  # item manquant → score 0

    @pytest.mark.asyncio
    async def test_unknown_id_ignored(self) -> None:
        raw = '{"model": "m", "results": [{"id": "unknown", "score": 0.9}]}'
        # L'id inconnu n'apparaît pas dans la réponse finale
        resp = self.validator.validate(raw, ["c-1"])
        assert resp.results[0].id == "c-1"
        assert resp.results[0].score == 0.0

    @pytest.mark.asyncio
    async def test_missing_item_score_zero(self) -> None:
        raw = '{"model": "m", "results": []}'
        resp = self.validator.validate(raw, ["c-1", "c-2"])
        assert resp.results[0].id == "c-1"
        assert resp.results[0].score == 0.0
        assert resp.results[1].id == "c-2"
        assert resp.results[1].score == 0.0

    @pytest.mark.asyncio
    async def test_malformed_json_error(self) -> None:
        with pytest.raises(InvalidResponseError):
            self.validator.validate("not json at all {{{", ["c-1"])

    @pytest.mark.asyncio
    async def test_extra_text_around_json(self) -> None:
        raw = "Premable text\n{\"model\":\"m\",\"results\":[{\"id\":\"c-1\",\"score\":0.7}]}\nPostamble"
        resp = self.validator.validate(raw, ["c-1"])
        assert resp.results[0].score == 0.7

    @pytest.mark.asyncio
    async def test_multiple_results_sorted_by_id_order(self) -> None:
        raw = '{"model":"m","results":[{"id":"c-2","score":0.6},{"id":"c-1","score":0.9}]}'
        resp = self.validator.validate(raw, ["c-1", "c-2"])
        assert [r.id for r in resp.results] == ["c-1", "c-2"]
        assert resp.results[0].score == 0.9
        assert resp.results[1].score == 0.6

    @pytest.mark.asyncio
    async def test_duplicate_ids_in_response_deduped(self) -> None:
        raw = '{"model":"m","results":[{"id":"c-1","score":0.9},{"id":"c-1","score":0.5}]}'
        resp = self.validator.validate(raw, ["c-1"])
        # Seul le premier est gardé
        assert len(resp.results) == 1
        assert resp.results[0].score == 0.9
