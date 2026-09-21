"""Tests des heuristiques du SpamFilter (main.md §5.1, H1–H5) — Tâche 03."""

from __future__ import annotations

import pytest

from app.filters._spam_heuristics import (
    compute_heuristics,
    emoji_count,
    has_char_repetition,
    has_link_flood,
    has_token_repeat,
    uppercase_ratio,
)
from app.filters.spam_filter import dup_score, flood_score, heuristic_score


@pytest.mark.unit
def test_uppercase_ratio() -> None:
    assert uppercase_ratio("HELLO WORLD") == 1.0
    assert uppercase_ratio("hello world") == 0.0
    assert uppercase_ratio("HeLLo") == 0.6
    assert uppercase_ratio("123 !!!") is None  # aucune lettre


@pytest.mark.unit
def test_char_repetition() -> None:
    assert has_char_repetition("AAAAAAA") is True
    assert has_char_repetition("aaaaaaa") is True
    assert has_char_repetition("aaaaaa") is False  # 6 fois → en dessous du seuil
    assert has_char_repetition("aabbccdd") is False
    assert has_char_repetition("1234567") is False
    assert has_char_repetition("1111111") is True  # 7 × '1' consécutives


@pytest.mark.unit
def test_link_flood() -> None:
    urls = ["https://a.com", "https://b.com", "https://c.com", "https://d.com"]
    assert has_link_flood(urls) is True
    assert has_link_flood(urls[:3]) is False


@pytest.mark.unit
def test_token_repeat() -> None:
    tokens = ["buy", "now", "buy", "now", "buy", "now", "buy", "now"]  # 8 tokens, 50% 'buy'
    assert has_token_repeat(tokens) is True
    tokens2 = ["a", "b", "c", "d", "e", "f", "g", "h"]  # 8 tokens, 12.5%
    assert has_token_repeat(tokens2) is False
    short = ["x", "x"]  # < 8 tokens
    assert has_token_repeat(short) is False
    tokens3 = ["a"] * 7 + ["b"]  # 8 tokens, 87.5% 'a'
    assert has_token_repeat(tokens3) is True


@pytest.mark.unit
def test_emoji_count() -> None:
    assert emoji_count("😀😀😀😀😀😀😀😀😀😀😀😀😀😀😀😀") == 16  # U+1F600
    assert emoji_count("☺☺☺☺☺☺☺☺☺☺☺☺☺☺☺☺") == 16  # U+263A (2600-27BF)
    assert emoji_count("no emojis here") == 0


@pytest.mark.unit
def test_short_text_no_heuristics() -> None:
    assert compute_heuristics(raw="short", urls=[], tokens=[]) == []


@pytest.mark.unit
def test_h1_all_caps() -> None:
    raw = "THIS IS A VERY LONG SHOUTING MESSAGE IN CAPITALS"
    assert compute_heuristics(raw=raw, urls=[], tokens=raw.lower().split()) == ["H1"]


@pytest.mark.unit
def test_h2_repetition() -> None:
    raw = "free money AAAAAAAAAA here for you my friend today"
    assert "H2" in compute_heuristics(raw=raw, urls=[], tokens=raw.lower().split())


@pytest.mark.unit
def test_h3_link_flood() -> None:
    raw = "links " + " ".join(f"https://s{i}.com/x" for i in range(4))
    heuristic_codes = compute_heuristics(raw=raw, urls=raw.split(), tokens=[])
    assert "H3" in heuristic_codes


@pytest.mark.unit
def test_h4_token_repeat() -> None:
    raw = "spam spam spam spam spam spam spam spam more words here"
    tokens = raw.lower().split()
    assert "H4" in compute_heuristics(raw=raw, urls=[], tokens=tokens)


@pytest.mark.unit
def test_h5_emoji_flood() -> None:
    raw = "😀" * 15 + " plus some filler words to reach the minimum length ok"
    assert "H5" in compute_heuristics(raw=raw, urls=[], tokens=[])


@pytest.mark.unit
def test_scores_tables() -> None:
    assert dup_score(1) == 0.0
    assert dup_score(2) == 0.40
    assert dup_score(3) == 0.60
    assert dup_score(4) == 0.60
    assert dup_score(5) == 0.80
    assert dup_score(9) == 0.80
    assert dup_score(10) == 0.95

    assert flood_score(5, threshold=10) == 0.0
    assert flood_score(15, threshold=10) == 0.60
    assert flood_score(30, threshold=10) == 0.80
    assert flood_score(41, threshold=10) == 0.95

    assert heuristic_score(0) == 0.0
    assert heuristic_score(1) == 0.30
    assert heuristic_score(2) == 0.50
    assert heuristic_score(3) == 0.70
    assert heuristic_score(5) == 0.70
