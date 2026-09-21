"""Tests du `TextNormalizer` (main.md §5.0) — Tâche 02."""

from __future__ import annotations

import pytest

from app.core.text_normalizer import deobfuscate, extract_urls, normalize, normalize_url, tokens_of


@pytest.mark.unit
def test_html_entities_decoded_and_tags_removed() -> None:
    result = normalize("<p>Tom &amp; Jerry &lt;3</p>")
    assert result.raw == "Tom & Jerry <3"


@pytest.mark.unit
def test_nfkc_normalization() -> None:
    result = normalize("\uff34\uff2f\uff25\uff38")  # ＴＯＥＸ fullwidth
    assert result.lower == "toex"
    result = normalize("caf\u00e9")  # é précomposé reste é
    assert result.lower == "café"


@pytest.mark.unit
def test_zero_width_and_control_chars_removed() -> None:
    result = normalize("ab\u200bc\u200dz\u200ew\u200f\ufeff")
    assert result.lower == "abczw"


@pytest.mark.unit
def test_whitespace_collapsed() -> None:
    result = normalize("  hello \t  world \n  again  ")
    assert result.raw == "hello world again"


@pytest.mark.unit
def test_casefold() -> None:
    result = normalize("HELLO Wörld")
    assert result.lower == "hello wörld"


@pytest.mark.unit
def test_deobfuscated_dots_removed() -> None:
    assert deobfuscate("f.u.c.k") == "fuck"


@pytest.mark.unit
def test_deobfuscated_isolated_letters_spaces() -> None:
    assert deobfuscate("f u c k") == "fuck"


@pytest.mark.unit
def test_deobfuscated_leet_mapping() -> None:
    assert deobfuscate("v1agra") == "viagra"
    assert deobfuscate("p@55w0rd") == "password"
    assert deobfuscate("s3cur1ty-7eam") == "securityteam"


@pytest.mark.unit
def test_deobfuscated_normal_words_not_joined_by_spaces() -> None:
    assert deobfuscate("hello world") == "hello world"


@pytest.mark.unit
def test_urls_extracted_with_scheme_and_bare() -> None:
    result = normalize("visit https://Example.COM/Path#frag and evil.io/xyz please")
    assert "https://example.com/Path" in result.urls
    assert "http://evil.io/xyz" in result.urls


@pytest.mark.unit
def test_normalize_url_handles_bare_and_fragment() -> None:
    assert normalize_url("Evil.ORG/a?b=1#frag") == "http://evil.org/a?b=1"
    assert normalize_url("ftp://x.com/f") == "ftp://x.com/f"  # schéma non-http inchangé
    assert normalize_url("https://x.com") == "https://x.com"


@pytest.mark.unit
def test_urls_deduplicated() -> None:
    urls = extract_urls("go https://a.com and https://a.com again")
    assert urls == ["https://a.com"]  # port normalisé absent


@pytest.mark.unit
def test_tokens_split_on_non_alphanumeric() -> None:
    result = normalize("Hello,World_123!")
    assert result.tokens == ["hello", "world", "123"]


@pytest.mark.unit
def test_tokens_of() -> None:
    assert tokens_of("a b--c__d") == ["a", "b", "c", "d"]
