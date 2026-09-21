"""Tests unitaires du `LinkFilter` (main.md §5.2, signaux S1–S7, allowlist) — Tâche 04."""

from __future__ import annotations

import pytest

from app.filters.link_filter import LinkFilter
from app.filters.registry import FILTER_REGISTRY
from app.schemas.enums import FilterStatus, RiskClass
from app.schemas.result import FilterContext
from tests.fixtures.payloads import make_item


def _ctx() -> FilterContext:
    return FilterContext(
        batch_id="batch-1",
        community_ref="community-A",
        attempt=0,
        target_classes={RiskClass.MALICIOUS_LINK, RiskClass.PHISHING},
    )


async def _outcome(flt: LinkFilter, text: str) -> object:
    item = make_item(text=text, user_ref="u-1", content_id="c-1")
    return await flt.evaluate(item, _ctx())


def _detections_by_class(outcome):
    return {d.risk_class: d for d in outcome.detections}


@pytest.mark.unit
def test_registered_in_registry() -> None:
    assert FILTER_REGISTRY["LinkFilter"] is LinkFilter
    assert LinkFilter.HANDLED_CLASSES == {RiskClass.MALICIOUS_LINK, RiskClass.PHISHING}


@pytest.mark.unit
async def test_s5_at_in_authority_phishing() -> None:
    outcome = await _outcome(LinkFilter(), "http://paypal.com@evil.io/secure")
    dets = _detections_by_class(outcome)
    assert outcome.status == FilterStatus.COMPLETED
    assert RiskClass.PHISHING in dets
    assert dets[RiskClass.PHISHING].score == 0.60
    assert "S5" in dets[RiskClass.PHISHING].detail


@pytest.mark.unit
async def test_s1_ip_host_malicious() -> None:
    outcome = await _outcome(LinkFilter(), "http://192.168.0.1/update")
    dets = _detections_by_class(outcome)
    assert RiskClass.MALICIOUS_LINK in dets
    assert dets[RiskClass.MALICIOUS_LINK].score == 0.50
    assert "S1" in dets[RiskClass.MALICIOUS_LINK].detail


@pytest.mark.unit
async def test_s6_brand_subdomain_phishing() -> None:
    outcome = await _outcome(LinkFilter(), "https://paypal.security-login.com/finish")
    dets = _detections_by_class(outcome)
    assert RiskClass.PHISHING in dets
    assert dets[RiskClass.PHISHING].score == 0.50
    assert "S6" in dets[RiskClass.PHISHING].detail


@pytest.mark.unit
async def test_s6_official_brand_not_phishing() -> None:
    outcome = await _outcome(LinkFilter(), "https://paypal.com/login/secure")
    assert outcome.detections == []


@pytest.mark.unit
async def test_s4_suspicious_tld_malicious() -> None:
    outcome = await _outcome(LinkFilter(), "https://example.xyz/hold")
    dets = _detections_by_class(outcome)
    assert RiskClass.MALICIOUS_LINK in dets
    assert dets[RiskClass.MALICIOUS_LINK].score == 0.30
    assert "S4" in dets[RiskClass.MALICIOUS_LINK].detail


@pytest.mark.unit
async def test_s7_deep_subdomain_malicious() -> None:
    outcome = await _outcome(LinkFilter(), "https://a.b.c.d.example.com/x")
    dets = _detections_by_class(outcome)
    assert RiskClass.MALICIOUS_LINK in dets
    assert dets[RiskClass.MALICIOUS_LINK].score == 0.20
    assert "S7" in dets[RiskClass.MALICIOUS_LINK].detail


@pytest.mark.unit
async def test_s2_punycode_phishing() -> None:
    outcome = await _outcome(LinkFilter(), "https://xn--rsch-7qa969ezblg.xn--p1ai/")
    dets = _detections_by_class(outcome)
    assert RiskClass.PHISHING in dets
    assert "S2" in dets[RiskClass.PHISHING].detail


@pytest.mark.unit
async def test_s3_shortener_malicious() -> None:
    outcome = await _outcome(LinkFilter(), "https://bit.ly/abcdef")
    dets = _detections_by_class(outcome)
    assert RiskClass.MALICIOUS_LINK in dets
    assert dets[RiskClass.MALICIOUS_LINK].score == 0.30
    assert "S3" in dets[RiskClass.MALICIOUS_LINK].detail


@pytest.mark.unit
async def test_signals_combine_and_cap_per_class() -> None:
    outcome = await _outcome(LinkFilter(), "http://paypal.com@192.168.0.1/x")
    dets = _detections_by_class(outcome)
    assert dets[RiskClass.MALICIOUS_LINK].score == 0.50  # S1
    assert dets[RiskClass.PHISHING].score == 0.60  # S5


@pytest.mark.unit
async def test_signals_capped_at_one() -> None:
    # S5 (0.60) + S6 (0.50) = 1.10 → plafonné à 1.00
    outcome = await _outcome(LinkFilter(), "http://paypal.com@evil.io/login")
    dets = _detections_by_class(outcome)
    assert dets[RiskClass.PHISHING].score == 1.00


@pytest.mark.unit
async def test_allowlist_domain_ignored() -> None:
    flt = LinkFilter(allowlist=["example.com"])
    outcome = await _outcome(flt, "https://example.com/login check this")
    assert outcome.detections == []


@pytest.mark.unit
async def test_allowlist_ignores_subdomains() -> None:
    flt = LinkFilter(allowlist=["example.com"])
    outcome = await _outcome(flt, "https://shop.example.com/item")
    assert outcome.detections == []


@pytest.mark.unit
async def test_no_url_skipped() -> None:
    flt = LinkFilter()
    item = make_item(text="hello world, nothing to see here", user_ref="u-1", content_id="c-1")
    assert flt.is_applicable(item) is False
    outcome = await flt.evaluate(item, _ctx())
    assert outcome.status == FilterStatus.SKIPPED
    assert outcome.detections == []


@pytest.mark.unit
async def test_bare_domain_detected() -> None:
    outcome = await _outcome(LinkFilter(), "go to evil-shop.xyz right now")
    dets = _detections_by_class(outcome)
    assert RiskClass.MALICIOUS_LINK in dets
    assert "S4" in dets[RiskClass.MALICIOUS_LINK].detail
