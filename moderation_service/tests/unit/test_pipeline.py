"""Tests du `PipelineBuilder` (main.md §4.2) — Tâche 02."""

from __future__ import annotations

import pytest

from app.core.pipeline import PipelineBuilder
from app.schemas.enums import RiskClass
from tests.fixtures.filters import (
    AlwaysDetectFilter,
    BatchDetectFilter,
    FailOnceThenSucceedFilter,
    PermanentFailFilter,
    SkipFilter,
    SlowFilter,
)

# Registre isolé : les fixtures uniquement (le registre global contient aussi
# les filtres réels SpamFilter/LinkFilter/LexiconFilter).
FIXTURES = [
    AlwaysDetectFilter,  # TOXICITY
    PermanentFailFilter,  # SEXUAL
    FailOnceThenSucceedFilter,  # INSULT
    SkipFilter,  # ADVERTISING
    SlowFilter,  # VIOLENCE
    BatchDetectFilter,  # SCAM
]


@pytest.mark.unit
def test_build_selects_only_matching_filters() -> None:
    builder = PipelineBuilder(registry=FIXTURES)
    pipeline, targets = builder.build([RiskClass.TOXICITY, RiskClass.SEXUAL])
    names = {cls.NAME for cls in pipeline}
    assert names == {"AlwaysDetectFilter", "PermanentFailFilter"}
    assert targets["AlwaysDetectFilter"] == {RiskClass.TOXICITY}
    assert targets["PermanentFailFilter"] == {RiskClass.SEXUAL}


@pytest.mark.unit
def test_build_excludes_filters_with_empty_intersection() -> None:
    builder = PipelineBuilder(registry=FIXTURES)
    # Aucune classe ne croise ADVERTISING (SkipFilter) ni SCAM (BatchDetectFilter)
    pipeline, _ = builder.build([RiskClass.TOXICITY, RiskClass.INSULT])
    names = {cls.NAME for cls in pipeline}
    assert "SkipFilter" not in names
    assert "BatchDetectFilter" not in names
    assert names == {"AlwaysDetectFilter", "FailOnceThenSucceedFilter"}


@pytest.mark.unit
def test_build_disabled_filters_absent() -> None:
    builder = PipelineBuilder(registry=FIXTURES)
    pipeline, _ = builder.build(
        [RiskClass.TOXICITY, RiskClass.SEXUAL],
        disabled={"PermanentFailFilter"},
    )
    names = {cls.NAME for cls in pipeline}
    assert names == {"AlwaysDetectFilter"}
    assert "PermanentFailFilter" not in names


@pytest.mark.unit
def test_build_computes_target_intersection() -> None:
    builder = PipelineBuilder(registry=FIXTURES)
    # FailOnceThenSucceedFilter gère INSULT ; actif avec d'autres classes
    pipeline, targets = builder.build([RiskClass.INSULT, RiskClass.TOXICITY, RiskClass.ADVERTISING])
    assert {c.NAME for c in pipeline} == {
        "AlwaysDetectFilter",
        "FailOnceThenSucceedFilter",
        "SkipFilter",
    }
    assert "BatchDetectFilter" not in {c.NAME for c in pipeline}  # SCAM non actif
    assert targets["FailOnceThenSucceedFilter"] == {RiskClass.INSULT}
    assert targets["SkipFilter"] == {RiskClass.ADVERTISING}


@pytest.mark.unit
def test_build_contexts() -> None:
    builder = PipelineBuilder(registry=FIXTURES)
    pipeline, targets = builder.build([RiskClass.TOXICITY])
    assert pipeline
    contexts = builder.build_contexts("b-1", "c-A", attempt=2, targets=targets)
    ctx = contexts["AlwaysDetectFilter"]
    assert ctx.batch_id == "b-1"
    assert ctx.community_ref == "c-A"
    assert ctx.attempt == 2
    assert ctx.target_classes == {RiskClass.TOXICITY}


@pytest.mark.unit
def test_build_accepts_set_input() -> None:
    builder = PipelineBuilder(registry=[AlwaysDetectFilter])
    pipeline, targets = builder.build({RiskClass.TOXICITY})
    assert pipeline == [AlwaysDetectFilter]
    assert targets["AlwaysDetectFilter"] == {RiskClass.TOXICITY}
