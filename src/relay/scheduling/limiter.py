"""Rolling-window budgets for requests and tokens.

Design choice: we reserve *estimated* tokens before the call and reconcile with
the provider's reported usage afterwards. Reserving requests only would let a
handful of large prompts blow through tokens-per-minute while the request count
still looks healthy; on the free tier that is the failure mode that actually
happens (8K TPM is ~3 answers/minute).

Day counters persist to disk because the free-tier cap is per organisation per
day, and a restarted process must not think it has fresh quota.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections import deque
from dataclasses import dataclass
from datetime import date
from pathlib import Path

MINUTE = "minute"
DAY = "day"


class LimitExceeded(Exception):
    def __init__(self, kind: str, retry_after_s: float, detail: str = "") -> None:
        super().__init__(f"{kind} limit: retry in {retry_after_s:.1f}s {detail}".strip())
        self.kind = kind
        self.retry_after_s = retry_after_s
        self.detail = detail


@dataclass(frozen=True, slots=True)
class LimiterLimits:
    rpm: int | None = None
    tpm: int | None = None
    rpd: int | None = None
    tpd: int | None = None

    def halve_minute(self) -> LimiterLimits:
        """Scenario 'per-minute limit halved' - used by the load harness."""
        return LimiterLimits(
            rpm=None if self.rpm is None else max(1, self.rpm // 2),
            tpm=None if self.tpm is None else max(1, self.tpm // 2),
            rpd=self.rpd,
            tpd=self.tpd,
        )

    def to_dict(self) -> dict[str, int | None]:
        return {"rpm": self.rpm, "tpm": self.tpm, "rpd": self.rpd, "tpd": self.tpd}


@dataclass(slots=True)
class _Entry:
    at: float
    tokens: int


class RollingLimiter:
    def __init__(
        self,
        limits: LimiterLimits,
        *,
        window_s: float = 60.0,
        state_path: Path | None = None,
    ) -> None:
        self.limits = limits
        self.window_s = window_s
        self.state_path = state_path
        self._entries: dict[str, _Entry] = {}
        self._lock = asyncio.Lock()
        self._day = date.today()
        self._day_requests = 0
        self._day_tokens = 0
        self._load_state()

    # ---- persistence -----------------------------------------------------
    def _load_state(self) -> None:
        if not self.state_path or not self.state_path.exists():
            return
        try:
            raw = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        if raw.get("day") != self._day.isoformat():
            return  # a new day means fresh quota
        self._day_requests = int(raw.get("requests", 0))
        self._day_tokens = int(raw.get("tokens", 0))

    def _save_state(self) -> None:
        if not self.state_path:
            return
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(
            json.dumps(
                {
                    "day": self._day.isoformat(),
                    "requests": self._day_requests,
                    "tokens": self._day_tokens,
                }
            ),
            encoding="utf-8",
        )

    def _roll_day(self) -> None:
        today = date.today()
        if today != self._day:
            self._day = today
            self._day_requests = 0
            self._day_tokens = 0
            self._save_state()

    # ---- accounting ------------------------------------------------------
    def _prune(self, now: float) -> None:
        cutoff = now - self.window_s
        for rid in [rid for rid, entry in self._entries.items() if entry.at <= cutoff]:
            del self._entries[rid]

    def minute_usage(self) -> tuple[int, int]:
        return len(self._entries), sum(entry.tokens for entry in self._entries.values())

    def snapshot(self) -> dict[str, object]:
        requests, tokens = self.minute_usage()
        return {
            "limits": self.limits.to_dict(),
            "minute": {"requests": requests, "tokens": tokens},
            "day": {"requests": self._day_requests, "tokens": self._day_tokens},
        }

    async def acquire(self, est_tokens: int, *, deadline_s: float = 30.0) -> str:
        """Reserve budget for one call, waiting inside the deadline if possible."""
        waited = 0.0
        async with self._lock:
            while True:
                self._roll_day()
                now = time.monotonic()
                self._prune(now)
                if self.limits.tpd is not None and self._day_tokens >= self.limits.tpd:
                    raise LimitExceeded(DAY, 3600.0, "token budget for today is spent")
                if self.limits.rpd is not None and self._day_requests >= self.limits.rpd:
                    raise LimitExceeded(DAY, 3600.0, "request budget for today is spent")

                minute_requests, minute_tokens = self.minute_usage()
                over_requests = (
                    self.limits.rpm is not None and minute_requests >= self.limits.rpm
                )
                over_tokens = (
                    self.limits.tpm is not None and minute_tokens + est_tokens > self.limits.tpm
                )
                if not over_requests and not over_tokens:
                    break

                oldest = min(entry.at for entry in self._entries.values())
                wait_s = max(0.05, (oldest + self.window_s) - now)
                if waited + wait_s > deadline_s:
                    raise LimitExceeded(
                        MINUTE, wait_s, "waiting would exceed the request deadline"
                    )
                await asyncio.sleep(min(wait_s, deadline_s - waited))
                waited += wait_s

            rid = f"res-{now:.6f}"
            self._entries[rid] = _Entry(at=now, tokens=est_tokens)
            self._day_requests += 1
            self._day_tokens += est_tokens
            self._save_state()
            return rid

    async def reconcile(self, reservation: str, actual_tokens: int) -> None:
        """Replace an estimate with the provider's reported usage."""
        async with self._lock:
            entry = self._entries.get(reservation)
            if entry is None:
                return
            delta = actual_tokens - entry.tokens
            entry.tokens = actual_tokens
            self._day_tokens += delta
            self._save_state()

    def release(self, reservation: str) -> None:
        """Give back a reservation whose call never reached the provider."""
        entry = self._entries.pop(reservation, None)
        if entry is None:
            return
        self._day_tokens = max(0, self._day_tokens - entry.tokens)
        self._day_requests = max(0, self._day_requests - 1)
        self._save_state()

    def force_exhaust_day(self) -> None:
        """Scenario 'daily budget exhausted' without burning real quota."""
        self._day_tokens = self.limits.tpd or 0
        self._day_requests = self.limits.rpd or 0
        self._save_state()
