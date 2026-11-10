"""Deterministic fault injection for the retry/deadline/breaker path.

The load runs only ever produced 429s, so nothing here is inferred from them: each
test scripts the provider's replies, which makes "retry succeeded", "retry failed",
"timeout", and "retrying made it worse" reproducible in milliseconds and independent
of the network or the stand-in's clock.

These are synthetic provider behaviours. They say nothing about how often Groq
actually fails; that number can only come from the real probe.
"""

from __future__ import annotations

import asyncio
import time

import pytest

from relay.llm.base import RATE_LIMITED_DAY, RATE_LIMITED_MINUTE, SERVER_ERROR, TIMEOUT, ChatResult
from relay.obs.events import Trace
from relay.pipeline.engine import PipelineConfig, Relay
from relay.scheduling.limiter import LimiterLimits, RollingLimiter
from relay.scheduling.queue import AdmissionQueue

GENEROUS = LimiterLimits(rpm=1_000, tpm=10_000_000, rpd=100_000, tpd=1_000_000_000)


class ScriptedProvider:
    """Returns scripted results in order; the last one repeats."""

    def __init__(self, results: list[ChatResult], *, delay_ms: float = 0.0) -> None:
        self.results = results
        self.calls = 0
        self.delay_ms = delay_ms

    async def chat(self, request):  # noqa: ANN001 - mirrors GroqProvider.chat
        self.calls += 1
        if self.delay_ms:
            await asyncio.sleep(self.delay_ms / 1000.0)
        return self.results[min(self.calls - 1, len(self.results) - 1)]


def ok_result(text: str = "{}") -> ChatResult:
    return ChatResult(status="ok", text=text, ttft_ms=10.0, tokens_in=40, tokens_out=12)


def fail_result(kind: str = SERVER_ERROR, *, retry_after_s: float | None = None) -> ChatResult:
    return ChatResult(
        status="rate_limited" if kind == RATE_LIMITED_MINUTE else "error",
        error_kind=kind,
        error=f"synthetic {kind}",
        http_status=429 if kind == RATE_LIMITED_MINUTE else 500,
        retry_after_s=retry_after_s,
    )


def build(provider: ScriptedProvider, **config) -> Relay:
    return Relay(
        provider=provider,
        index=None,  # not used by _call
        limiter=RollingLimiter(GENEROUS, state_path=None),
        queue=AdmissionQueue(max_inflight=4, max_waiting=4),
        setting_name="A",
        fetch_k=4,
        top_k=4,
        model="scripted",
        source="test",
        config=PipelineConfig(**config),
    )


def call(relay: Relay):
    trace = Trace(scenario="test", source="test", retrieval_setting="A", question="q")
    started = time.perf_counter()
    result = asyncio.run(relay._call([{"role": "user", "content": "hi"}], 32, trace, "draft"))
    return result, trace, (time.perf_counter() - started) * 1000


def test_retry_after_server_error_succeeds() -> None:
    provider = ScriptedProvider([fail_result(), ok_result()])
    relay = build(provider)
    result, trace, _ = call(relay)
    assert result.ok
    assert provider.calls == 2
    assert trace.retries == 1
    assert trace.backoff_ms > 0
    assert trace.working_ms > 0


def test_server_error_exhausts_attempts_and_fails() -> None:
    provider = ScriptedProvider([fail_result()])
    relay = build(provider, max_attempts=3)
    result, trace, _ = call(relay)
    assert not result.ok and result.error_kind == SERVER_ERROR
    assert provider.calls == 3
    assert trace.retries == 2


def test_timeout_is_classified_and_retried() -> None:
    provider = ScriptedProvider(
        [ChatResult(status="timeout", error_kind=TIMEOUT, error="read timeout"), ok_result()]
    )
    relay = build(provider)
    result, trace, _ = call(relay)
    assert result.ok
    assert provider.calls == 2
    assert trace.retries == 1


def test_permanent_error_is_not_retried() -> None:
    provider = ScriptedProvider([fail_result("bad_request")])
    relay = build(provider)
    result, _trace, _ = call(relay)
    assert not result.ok
    assert provider.calls == 1, "a 400 must not be retried"


def test_daily_cap_is_not_retried() -> None:
    provider = ScriptedProvider([fail_result(RATE_LIMITED_DAY)])
    relay = build(provider)
    result, _trace, _ = call(relay)
    assert not result.ok and result.error_kind == RATE_LIMITED_DAY
    assert provider.calls == 1, "tomorrow's budget is not reachable by retrying"


def test_rate_limit_longer_than_deadline_fails_fast() -> None:
    """Waiting 60 s inside a 30 s deadline is not patience, it is a delayed failure."""
    provider = ScriptedProvider([fail_result(RATE_LIMITED_MINUTE, retry_after_s=60.0)])
    relay = build(provider)
    result, trace, elapsed_ms = call(relay)
    assert not result.ok and result.status == "rate_limited"
    assert elapsed_ms < 500, f"returned after {elapsed_ms:.0f} ms instead of refusing"
    assert trace.retries == 1, "the retry decision was made, then abandoned on the deadline"


def test_rate_limits_do_not_open_the_breaker() -> None:
    provider = ScriptedProvider([fail_result(RATE_LIMITED_MINUTE)])
    relay = build(provider, max_attempts=7)
    call(relay)
    assert relay.breaker.state == "closed", "a busy provider is not a broken provider"


def test_server_errors_open_the_breaker() -> None:
    provider = ScriptedProvider([fail_result()])
    relay = build(provider, max_attempts=6)
    call(relay)
    assert relay.breaker.state == "open"
    # The next request must not even attempt a call.
    before = provider.calls
    call(relay)
    assert provider.calls == before
    assert relay.breaker.state == "open"


def test_retrying_makes_it_worse_same_failure_later() -> None:
    """One experiment where retrying is strictly worse, measured rather than asserted.

    Same permanent-ish 500, same latency per attempt: the retried version takes
    longer and still fails. This is why the retry budget stops at three attempts.
    """
    slow = 40.0
    single = ScriptedProvider([fail_result()], delay_ms=slow)
    single_result, _trace, single_ms = call(build(single, max_attempts=1))

    retried = ScriptedProvider([fail_result()], delay_ms=slow)
    retried_result, retried_trace, retried_ms = call(build(retried, max_attempts=3))

    assert not single_result.ok and not retried_result.ok
    assert retried.calls == 3 > single.calls == 1
    assert retried_ms > single_ms + 2 * slow
    assert retried_trace.backoff_ms > 0
    # Same outcome, more than three times the wall clock.
    assert retried_ms > 2.5 * single_ms


def test_degradation_ladder_trims_work_as_the_minute_fills() -> None:
    """The ladder is code until something exercises it, so exercise it directly."""
    provider = ScriptedProvider([ok_result()])
    relay = build(provider)
    assert relay._auto_degrade() == 0

    async def fill(tokens: int) -> None:
        reservation = await relay.limiter.acquire(tokens, deadline_s=5.0)
        await relay.limiter.reconcile(reservation, tokens)

    asyncio.run(fill(int(0.6 * relay.limiter.limits.tpm)))
    assert relay._auto_degrade() == 1, "above 55% the analyse step is skipped"

    asyncio.run(fill(int(0.25 * relay.limiter.limits.tpm)))
    assert relay._auto_degrade() == 2, "above 80% context and repair are trimmed"


@pytest.mark.parametrize("kind", [SERVER_ERROR, TIMEOUT, RATE_LIMITED_MINUTE])
def test_every_fault_kind_maps_to_a_status_the_csv_can_hold(kind: str) -> None:
    provider = ScriptedProvider([fail_result(kind)])
    relay = build(provider, max_attempts=1)
    result, trace, _ = call(relay)
    answer = relay._failure(result, trace)
    assert trace.status in {"ok", "rate_limited", "timeout", "error"}
    assert answer.refused, "a failed call must never come back as an answer"
    assert answer.reason, "the refusal has to say why it refused"
