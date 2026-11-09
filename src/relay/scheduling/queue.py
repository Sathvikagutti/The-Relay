"""Bounded admission queue.

Backpressure decision: the queue is bounded (32 waiting by default) and rejects
immediately with a `retry-after` hint when full. An unbounded queue does not
create capacity - it only converts a rate-limit problem into a timeout problem,
and the person waits longer to be told the same thing. Rejecting fast is the
kinder behaviour and it keeps p95 honest.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator


class QueueFull(Exception):
    def __init__(self, retry_after_s: float = 5.0) -> None:
        super().__init__("admission queue is full")
        self.retry_after_s = retry_after_s


class AdmissionQueue:
    def __init__(self, *, max_inflight: int = 4, max_waiting: int = 32) -> None:
        self.max_inflight = max_inflight
        self.max_waiting = max_waiting
        self._semaphore = asyncio.Semaphore(max_inflight)
        self._admitted = 0
        self.peak_waiting = 0
        self._inflight = 0
        self.peak_inflight = 0

    @property
    def waiting(self) -> int:
        return self._admitted - self._inflight

    @asynccontextmanager
    async def slot(self) -> AsyncIterator[None]:
        # max_waiting bounds the queue, not total admission: with 4 slots and
        # max_waiting=32, at most 36 requests are ever admitted at once.
        if self._admitted - self._inflight >= self.max_waiting:
            raise QueueFull()
        self._admitted += 1
        self.peak_waiting = max(self.peak_waiting, self._admitted - self._inflight)
        try:
            async with self._semaphore:
                self._inflight += 1
                self.peak_inflight = max(self.peak_inflight, self._inflight)
                try:
                    yield
                finally:
                    self._inflight -= 1
        finally:
            self._admitted -= 1
