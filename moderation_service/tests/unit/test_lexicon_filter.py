"""Tests unitaires du `LexiconFilter` / `LexiconRepository` (main.md §5.3) — Tâche 04."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.filters.lexicon_filter import LexiconFilter
from app.filters.lexicon_repository import LexiconRepository
from app.filters.registry import FILTER_REGISTRY
from app.schemas.enums import ContentType, FilterStatus, RiskClass
from app.schemas.job import ContentItem
from app.schemas.result import FilterContext
from tests.fixtures.payloads import make_item

INSULT_FILE = "idiot|0.45\nstupid|0.45\nmerde|0.90\nfuck|0.55\nson of a bitch|0.60\nre:st[u4]pid|0.50\n"
SCAM_FILE = "free money|0.65\n"


@pytest.fixture()
def repo(tmp_path) -> LexiconRepository:
    (tmp_path / "insult.txt").write_text(INSULT_FILE, encoding="utf-8")
    (tmp_path / "scam.txt").write_text(SCAM_FILE, encoding="utf-8")
    return LexiconRepository(tmp_path)


def _target(*classes: RiskClass) -> FilterContext:
    return FilterContext(
        batch_id="batch-1",
        community_ref="community-A",
        attempt=0,
        target_classes=set(classes),
    )


async def _evaluate(repo: LexiconRepository, text: str | None, *classes: RiskClass):
    flt = LexiconFilter(repo)
    if text is None or not text.strip():
        item = ContentItem.model_construct(
            content_id="c-1",
            content_type=ContentType.COMMENT,
            user_ref="u-1",
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
            text=text or "",
            attachments=[],
        )
    else:
        item = make_item(text=text, user_ref="u-1", content_id="c-1")
    return await flt.evaluate(item, _target(*classes))


@pytest.mark.unit
def test_registered_in_registry(repo: LexiconRepository) -> None:
    assert FILTER_REGISTRY["LexiconFilter"] is LexiconFilter
    assert RiskClass.INSULT in LexiconFilter.HANDLED_CLASSES


@pytest.mark.unit
def test_repository_load_and_patterns(repo: LexiconRepository) -> None:
    patterns = repo.patterns_for(RiskClass.INSULT)
    assert len(patterns) >= 4
    by_name = {p.pattern: p.score for p in patterns}
    assert by_name["idiot"] == 0.45
    assert by_name["merde"] == 0.90
    assert repo.patterns_for(RiskClass.SCAM)[0].pattern == "free money"


@pytest.mark.unit
def test_repository_ignores_empty_and_comments(tmp_path) -> None:
    (tmp_path / "self_harm.txt").write_text(
        "# commentaire\n\ncut myself|0.70\n  \n  \n", encoding="utf-8"
    )
    repo = LexiconRepository(tmp_path)
    patterns = repo.patterns_for(RiskClass.SELF_HARM)
    assert len(patterns) == 1


@pytest.mark.unit
def test_repository_purge_caches(repo: LexiconRepository) -> None:
    assert repo.patterns_for(RiskClass.INSULT)
    repo.purge_caches()
    assert repo._patterns is None
    assert repo.patterns_for(RiskClass.INSULT)


@pytest.mark.unit
async def test_case_insensitive_match(repo: LexiconRepository) -> None:
    outcome = await _evaluate(repo, "YOU ARE AN IDIOT", RiskClass.INSULT)
    assert outcome.status == FilterStatus.COMPLETED
    assert len(outcome.detections) == 1
    assert outcome.detections[0].risk_class == RiskClass.INSULT
    assert outcome.detections[0].score == 0.45


@pytest.mark.unit
async def test_match_on_deobfuscated(repo: LexiconRepository) -> None:
    outcome = await _evaluate(repo, "f.u.c.k you", RiskClass.INSULT)
    assert len(outcome.detections) == 1
    assert outcome.detections[0].risk_class == RiskClass.INSULT
    assert outcome.detections[0].score == 0.55


@pytest.mark.unit
async def test_regex_pattern_match_on_deobfuscated(repo: LexiconRepository) -> None:
    outcome = await _evaluate(repo, "you are stup1d", RiskClass.INSULT)
    detection = outcome.detections[0]
    # re:st[u4]pid (0.50) + "stupid" littéral (0.45) sur deobfuscated → base 0.50 + bonus 0.05
    assert detection.score == 0.55
    assert "re:st[u4]pid" in detection.detail


@pytest.mark.unit
async def test_multiple_patterns_bonus(repo: LexiconRepository) -> None:
    outcome = await _evaluate(repo, "idiot stupid", RiskClass.INSULT)
    assert len(outcome.detections) == 1
    # idiot (0.45) + stupid (0.45) + re:st[u4]pid (0.50) → base 0.50 + 2×0.05
    assert outcome.detections[0].score == 0.60
    assert "idiot" in outcome.detections[0].detail


@pytest.mark.unit
async def test_max_score_cap(repo: LexiconRepository) -> None:
    outcome = await _evaluate(repo, "merde ici", RiskClass.INSULT)
    assert outcome.detections[0].score == 0.85  # 0.90 plafonné par LEXICON_MAX_SCORE


@pytest.mark.unit
async def test_max_score_override(repo: LexiconRepository) -> None:
    flt = LexiconFilter(repo, max_score=0.5)
    item = make_item(text="merde ici", user_ref="u-1", content_id="c-1")
    outcome = await flt.evaluate(item, _target(RiskClass.INSULT))
    assert outcome.detections[0].score == 0.5


@pytest.mark.unit
async def test_bonus_cap(tmp_path) -> None:
    entries = "\n".join(f"mot{i}|0.40" for i in range(5))
    (tmp_path / "insult.txt").write_text(entries + "\n", encoding="utf-8")
    flt = LexiconFilter(LexiconRepository(tmp_path))
    item = make_item(text="mot0 mot1 mot2 mot3 mot4", user_ref="u-1", content_id="c-1")
    outcome = await flt.evaluate(item, _target(RiskClass.INSULT))
    # base 0.40 + bonus plafonné 0.15
    assert outcome.detections[0].score == 0.55


@pytest.mark.unit
async def test_no_emission_when_class_not_targeted(repo: LexiconRepository) -> None:
    outcome = await _evaluate(repo, "stupid free money", RiskClass.SCAM)
    assert outcome.status == FilterStatus.COMPLETED
    assert all(d.risk_class == RiskClass.SCAM for d in outcome.detections)


@pytest.mark.unit
async def test_none_targeted_no_detections(repo: LexiconRepository) -> None:
    outcome = await _evaluate(repo, "you are an idiot", RiskClass.TOXICITY)
    assert outcome.detections == []


@pytest.mark.unit
def test_seed_files_load_within_expected_range() -> None:
    """Les seeds fournis (FR+EN) doivent charger : 20-50 entrées valides par classe."""
    repo = LexiconRepository()
    repo.load()
    for risk_class in LexiconFilter.HANDLED_CLASSES:
        count = len(repo.patterns_for(risk_class))
        assert 20 <= count <= 50, f"{risk_class}: {count} entrées hors bornes [20,50]"


@pytest.mark.unit
def test_seed_files_no_missing() -> None:
    repo = LexiconRepository()
    repo.load()
    for risk_class in LexiconFilter.HANDLED_CLASSES:
        assert repo.patterns_for(risk_class), f"lexicon manquant pour {risk_class}"


@pytest.mark.unit
def test_whitespace_pattern_handled(tmp_path) -> None:
    (tmp_path / "scam.txt").write_text("free money|0.65\n bad weight |0.75  \n", encoding="utf-8")
    repo = LexiconRepository(tmp_path)
    patterns = repo.patterns_for(RiskClass.SCAM)
    assert {p.pattern: p.score for p in patterns} == {"free money": 0.65, "bad weight": 0.75}


@pytest.mark.unit
async def test_whitespace_text_skipped(repo: LexiconRepository) -> None:
    outcome = await _evaluate(repo, "   ", RiskClass.INSULT)
    assert outcome.status == FilterStatus.SKIPPED
    assert outcome.detections == []


@pytest.mark.unit
async def test_none_text_skipped(repo: LexiconRepository) -> None:
    outcome = await _evaluate(repo, None, RiskClass.INSULT)
    assert outcome.status == FilterStatus.SKIPPED
