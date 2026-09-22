"""Tests unitaires de la `RetryPolicy` (main.md §6)."""

from __future__ import annotations

from app.providers.base import RetryPolicy


class TestRetryPolicy:
    def test_defaults(self) -> None:
        rp = RetryPolicy()
        assert rp.base_delay_ms == 500
        assert rp.multiplier == 2.0
        assert rp.max_delay_ms == 8000
        assert rp.max_retries == 3

    def test_delay_sequence(self) -> None:
        rp = RetryPolicy(base_delay_ms=100, multiplier=2.0, max_delay_ms=1000, max_retries=3)
        assert rp.delay_for(0) == 100
        assert rp.delay_for(1) == 200
        assert rp.delay_for(2) == 400
        assert rp.delay_for(3) == 800

    def test_delay_capped(self) -> None:
        rp = RetryPolicy(base_delay_ms=100, multiplier=10.0, max_delay_ms=500, max_retries=10)
        assert rp.delay_for(0) == 100
        assert rp.delay_for(1) == 500  # capped
        assert rp.delay_for(2) == 500  # capped

    def test_negative_attempt_clamped(self) -> None:
        rp = RetryPolicy(base_delay_ms=100)
        assert rp.delay_for(-1) == 100

    def test_retryable_statuses(self) -> None:
        rp = RetryPolicy()
        assert rp.is_retryable(429)
        assert rp.is_retryable(500)
        assert rp.is_retryable(503)
        assert not rp.is_retryable(400)
        assert not rp.is_retryable(401)
        assert not rp.is_retryable(402)
        assert not rp.is_retryable(404)
        assert not rp.is_retryable(200)
