"""Retry policy.

What is retryable, and why:
  * timeout / read stall  - yes, one retry: the call may have been a slow success.
  * 5xx / connection      - yes, with jittered exponential backoff.
  * 429 on a per-minute window - yes, but only if `retry-after` fits the deadline;
    a token-window rejection frees in seconds.
  * 429 on a per-day window    - no. It cannot succeed before tomorrow; retrying
    delays the refusal the user needs to see and burns nothing but their patience.
  * 4xx other than 429, 401/403 - never; the request itself is wrong.

Backoff is full jitter (`uniform(0, cap)`) rather than equal jitter: when many
requests are released from the same rate-limit event, full jitter is what stops
them from re-colliding on the provider's window boundary.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from relay.llm.base import RATE_LIMITED_DAY, RATE_LIMITED_MINUTE, SERVER_ERROR, TIMEOUT

RETRYABLE = frozenset({RATE_LIMITED_MINUTE, SERVER_ERROR, TIMEOUT})
NEVER_RETRY = frozenset({RATE_LIMITED_DAY, "bad_request", "auth_error"})


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_attempts: int = 3
    base_ms: float = 400.0
    cap_ms: float = 8000.0
    deadline_ms: float = 30000.0
    retry_budget_ratio: float = 0.25  # retries allowed per successful request

    def delay_ms(self, attempt: int, rng: random.Random) -> float:
        """Full-jitter exponential backoff for attempt 1..n."""
        ceiling = min(self.cap_ms, self.base_ms * (2 ** (attempt - 1)))
        return rng.uniform(0.0, ceiling)


class RetryBudget:
    """Caps total retries relative to successes so one outage cannot cascade."""

    def __init__(self, policy: RetryPolicy, *, floor: int = 8) -> None:
        self.policy = policy
        self.floor = floor
        self.successes = 0
        self.spent = 0

    @property
    def allowance(self) -> int:
        return max(self.floor, int(self.successes * self.policy.retry_budget_ratio))

    def spend(self) -> bool:
        if self.spent >= self.allowance:
            return False
        self.spent += 1
        return True

    def record_success(self) -> None:
        self.successes += 1
