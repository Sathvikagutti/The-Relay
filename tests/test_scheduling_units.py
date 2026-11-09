"""Unit tests for the pieces whose failure modes are invisible in a happy-path run:
the queue's shedding boundary, the breaker's half-open recovery, backoff ceilings,
and the quote verifier that stops fabricated citations."""

from __future__ import annotations

import asyncio
import random

import pytest

from relay.pipeline.tools import MIN_QUOTE_CHARS, verify_quote
from relay.scheduling.breaker import CircuitBreaker, CircuitOpen
from relay.scheduling.queue import AdmissionQueue, QueueFull
from relay.scheduling.retry import RetryPolicy


def test_queue_rejects_when_waiting_is_full() -> None:
    async def scenario() -> None:
        queue = AdmissionQueue(max_inflight=1, max_waiting=1)
        release = asyncio.Event()

        async def holder() -> None:
            async with queue.slot():
                await release.wait()

        first = asyncio.create_task(holder())
        await asyncio.sleep(0.01)

        async def waiter() -> None:
            async with queue.slot():
                pass

        second = asyncio.create_task(waiter())  # fills the one waiting slot
        await asyncio.sleep(0.01)
        assert queue.waiting == 1
        with pytest.raises(QueueFull):
            async with queue.slot():
                pass
        release.set()
        await asyncio.gather(first, second)

    asyncio.run(scenario())


def test_queue_tracks_peaks_without_exceeding_concurrency() -> None:
    async def scenario() -> None:
        queue = AdmissionQueue(max_inflight=2, max_waiting=8)

        async def worker() -> None:
            async with queue.slot():
                await asyncio.sleep(0.01)

        await asyncio.gather(*(worker() for _ in range(6)))
        assert queue.peak_inflight == 2
        assert queue.peak_waiting >= 1

    asyncio.run(scenario())


def test_breaker_opens_then_half_opens_after_cooldown() -> None:
    now = [0.0]
    breaker = CircuitBreaker(failure_threshold=3, cooldown_s=10.0, clock=lambda: now[0])
    for _ in range(3):
        breaker.record_failure()
    assert breaker.state == "open"
    with pytest.raises(CircuitOpen):
        breaker.before_call()
    now[0] = 10.5
    breaker.before_call()  # half-open probe is allowed
    assert breaker.state == "half_open"
    breaker.record_success()
    assert breaker.state == "closed"


def test_breaker_success_resets_failure_count() -> None:
    breaker = CircuitBreaker(failure_threshold=2)
    breaker.record_failure()
    breaker.record_success()
    breaker.record_failure()
    assert breaker.state == "closed"


def test_backoff_ceiling_grows_and_caps() -> None:
    policy = RetryPolicy(base_ms=100.0, cap_ms=500.0)
    rng = random.Random(0)
    for attempt in range(1, 8):
        delay = policy.delay_ms(attempt, rng)
        ceiling = min(policy.cap_ms, policy.base_ms * 2 ** (attempt - 1))
        assert 0.0 <= delay <= ceiling


def test_quote_verifier_accepts_pdf_split_words() -> None:
    passage = "we propose the T ransformer, based solely on attention mechanisms"
    quote = "we propose the Transformer, based solely"
    ok, reason = verify_quote(quote, passage)
    assert ok, reason


def test_quote_verifier_rejects_short_and_fabricated_quotes() -> None:
    passage = "The encoder is composed of a stack of six identical layers."
    short_ok, short_reason = verify_quote("six layers", passage)
    assert not short_ok and str(MIN_QUOTE_CHARS) in short_reason
    made_up = "The encoder contains twelve recurrent convolutional layers"
    ok, reason = verify_quote(made_up, passage)
    assert not ok and "verbatim" in reason
