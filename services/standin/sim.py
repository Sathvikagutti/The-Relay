"""Simulation model for the stand-in service.

Calibration source: `services/standin/params.json`, written by `calibrate.py` from
real Groq measurements. Until that file exists, the defaults below are explicitly
uncalibrated and the service reports `calibrated: false` on /health so a report can
never mistake assumed numbers for measured ones.

Determinism: every request derives its RNG from (seed, prompt content, occurrence
count of that content). Replaying the same request sequence reproduces the same
latency and fault decisions.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import re
import time
from collections import deque
from dataclasses import asdict, dataclass
from pathlib import Path

PARAMS_PATH = Path(__file__).with_name("params.json")

CHUNK_RE = re.compile(r"^\[(?P<id>[a-z_]+:\d{4})\]\s*\((?P<meta>[^\n]*)\)\n(?P<body>.*?)(?=\n\n\[|\Z)", re.S | re.M)


@dataclass(slots=True)
class SimParams:
    """Latency and fault parameters. Percentiles, not means, because the tail is
    what users feel and what the report quotes."""

    ttft_p50_ms: float = 190.0
    ttft_p95_ms: float = 780.0
    per_token_ms: float = 4.0
    queue_dilation: float = 0.08  # fractional slowdown per queued request
    failure_rate: float = 0.0
    timeout_rate: float = 0.0
    timeout_s: float = 35.0
    partial_rate: float = 0.0
    concurrency: int = 4
    calibrated: bool = False
    calibrated_from: str = "uncalibrated defaults"
    sample_size: int = 0

    @classmethod
    def load(cls) -> SimParams:
        if not PARAMS_PATH.exists():
            return cls()
        raw = json.loads(PARAMS_PATH.read_text(encoding="utf-8"))
        return cls(**{key: raw[key] for key in raw if key in cls.__annotations__})

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class Limits:
    rpm: int = 30
    tpm: int = 8_000
    rpd: int = 1_000
    tpd: int = 200_000


@dataclass(slots=True)
class LatencySample:
    ttft_ms: float
    total_ms: float
    tokens_out: int


class Simulator:
    def __init__(
        self,
        *,
        params: SimParams,
        limits: Limits,
        window_s: float = 60.0,
        clock=time.monotonic,
    ) -> None:
        self.params = params
        self.limits = limits
        self.window_s = window_s
        self._clock = clock
        self._minute: deque[tuple[float, int]] = deque()
        self._day_started = time.time()
        self._day_requests = 0
        self._day_tokens = 0
        self._occurrences: dict[str, int] = {}
        self.inflight = 0
        self.peak_queue = 0
        self.force_day_exhausted = False

    # ---- limits ----------------------------------------------------------
    def _prune(self, now: float) -> None:
        cutoff = now - self.window_s
        while self._minute and self._minute[0][0] <= cutoff:
            self._minute.popleft()

    def _minute_wait(self, est_tokens: int, now: float) -> float | None:
        """Seconds until the minute window would accept this request."""
        self._prune(now)
        requests = len(self._minute)
        tokens = sum(entry[1] for entry in self._minute)
        if requests < self.limits.rpm and tokens + est_tokens <= self.limits.tpm:
            return None
        oldest = self._minute[0][0] if self._minute else now
        return max(0.05, (oldest + self.window_s) - now)

    def check_limits(self, est_tokens: int) -> tuple[str, float] | None:
        now = self._clock()
        if self.force_day_exhausted or self._day_tokens + est_tokens > self.limits.tpd:
            return ("tokens per day (TPD)", 3600.0)
        if self._day_requests + 1 > self.limits.rpd:
            return ("requests per day (RPD)", 3600.0)
        wait = self._minute_wait(est_tokens, now)
        if wait is not None:
            kind = (
                "requests per minute (RPM)"
                if len(self._minute) >= self.limits.rpm
                else "tokens per minute (TPM)"
            )
            return (kind, wait)
        return None

    def record(self, est_tokens: int, actual_tokens: int) -> None:
        now = self._clock()
        self._minute.append((now, max(1, est_tokens)))
        self._day_requests += 1
        self._day_tokens += max(1, actual_tokens)

    def headers(self) -> dict[str, str]:
        self._prune(self._clock())
        tokens = sum(entry[1] for entry in self._minute)
        return {
            "x-ratelimit-limit-requests": str(self.limits.rpd),
            "x-ratelimit-remaining-requests": str(max(0, self.limits.rpd - self._day_requests)),
            "x-ratelimit-limit-tokens": str(self.limits.tpm),
            "x-ratelimit-remaining-tokens": str(max(0, self.limits.tpm - tokens)),
        }

    # ---- latency ---------------------------------------------------------
    def _rng(self, prompt: str, seed: int) -> random.Random:
        key = f"{seed}:{prompt[:400]}"
        occurrence = self._occurrences.get(key, 0)
        self._occurrences[key] = occurrence + 1
        digest = hashlib.blake2b(f"{key}:{occurrence}".encode(), digest_size=8).digest()
        return random.Random(int.from_bytes(digest, "big"))

    def sample_latency(self, prompt: str, max_tokens: int, seed: int) -> LatencySample:
        rng = self._rng(prompt, seed)
        sigma = max(0.05, (math.log(self.params.ttft_p95_ms) - math.log(self.params.ttft_p50_ms)) / 1.645)
        ttft = rng.lognormvariate(math.log(self.params.ttft_p50_ms), sigma)
        dilution = 1.0 + self.params.queue_dilation * max(0, self.inflight - self.params.concurrency)
        tokens_out = max(8, min(max_tokens, 40 + rng.randrange(0, 60)))
        total = ttft * dilution + tokens_out * self.params.per_token_ms * dilution
        return LatencySample(ttft_ms=ttft * dilution, total_ms=total, tokens_out=tokens_out)

    def fault(self, prompt: str, seed: int) -> str | None:
        rng = self._rng(f"fault:{prompt}", seed)
        roll = rng.random()
        if roll < self.params.failure_rate:
            return "server_error"
        roll -= self.params.failure_rate
        if roll < self.params.timeout_rate:
            return "timeout"
        roll -= self.params.timeout_rate
        if roll < self.params.partial_rate:
            return "partial"
        return None

    # ---- payload shaping -------------------------------------------------
    @staticmethod
    def is_analysis_prompt(messages: list[dict[str, str]]) -> bool:
        return any("You plan searches" in message.get("content", "") for message in messages)

    @staticmethod
    def prompts(messages: list[dict[str, str]]) -> tuple[str, str]:
        system = " ".join(m.get("content", "") for m in messages if m.get("role") == "system")
        user = " ".join(m.get("content", "") for m in messages if m.get("role") == "user")
        return system, user

    def analysis_response(self, user_content: str) -> str:
        question = user_content.split("Question:")[-1].strip()
        answerable = bool(question)
        payload = {
            "queries": [question[:180]] if question else [],
            "needs_multi": len(question.split()) > 12,
            "answerable": answerable,
        }
        return json.dumps(payload)

    def draft_response(self, user_content: str) -> tuple[str, str]:
        """Return (answer_text, json_payload) using the first cited passage."""
        passages = [
            (match.group("id"), match.group("body").strip())
            for match in CHUNK_RE.finditer(user_content)
        ]
        if not passages:
            return (
                "The papers do not state this.",
                json.dumps({"answerable": False, "answer": "The papers do not state this.", "citations": []}),
            )
        chunk_id, body = passages[0]
        quote = " ".join(body.split())
        if len(quote) > 180:
            cut = quote[:180]
            quote = cut[: cut.rfind(" ")] if " " in cut else cut
        if len(quote) < 30:
            quote = " ".join(body.split())[:120]
        payload = {
            "answerable": True,
            "answer": f"According to the passage: {quote[:140]}",
            "citations": [{"chunk_id": chunk_id, "quote": quote}],
        }
        return payload["answer"], json.dumps(payload)
