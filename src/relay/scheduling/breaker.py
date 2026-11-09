"""Circuit breaker.

Why this and not per-call timeouts alone: when the provider is hard-down, every
request paying a 30 s deadline makes the queue look like a capacity problem when
it is really an outage. The breaker converts "wait 30 s then fail" into "fail in
1 ms with a retry hint", which is the only honest thing to tell a waiting person.

Half-open probes one request at a time so recovery is detected without a thundering
herd.
"""

from __future__ import annotations

import time


class CircuitOpen(Exception):
    def __init__(self, retry_after_s: float) -> None:
        super().__init__(f"circuit open, retry in {retry_after_s:.1f}s")
        self.retry_after_s = retry_after_s


class CircuitBreaker:
    def __init__(
        self,
        *,
        failure_threshold: int = 5,
        cooldown_s: float = 20.0,
        clock=time.monotonic,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.cooldown_s = cooldown_s
        self._clock = clock
        self._consecutive_failures = 0
        self._opened_at: float | None = None
        self._half_open = False

    @property
    def state(self) -> str:
        if self._opened_at is None:
            return "closed"
        if self._half_open:
            return "half_open"
        return "open"

    def before_call(self) -> None:
        if self._opened_at is None:
            return
        elapsed = self._clock() - self._opened_at
        if elapsed >= self.cooldown_s:
            self._half_open = True
            return
        raise CircuitOpen(self.cooldown_s - elapsed)

    def record_failure(self) -> None:
        self._consecutive_failures += 1
        if self._half_open or self._consecutive_failures >= self.failure_threshold:
            self._opened_at = self._clock()
            self._half_open = False

    def record_success(self) -> None:
        self._consecutive_failures = 0
        self._opened_at = None
        self._half_open = False
