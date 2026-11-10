"""Per-request evidence.

Every number in the report has to survive being recomputed from `results.csv`,
so the pipeline records raw spans (queued, admitted, call start, first token,
end, retries) and derives the CSV from those spans rather than the other way
round. `results/raw/*.jsonl` keeps the full trace; `results.csv` keeps the 12
columns the assignment requires.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def new_request_id() -> str:
    return uuid.uuid4().hex[:12]


@dataclass(slots=True)
class Trace:
    """Timing arithmetic for one request.

    The split the report needs is waiting / working / retrying:
      waiting  = time spent queued or blocked on a rate limiter
      working  = time in successful provider calls
      retrying = time in failed or abandoned attempts, including backoff sleeps
    """

    request_id: str = field(default_factory=new_request_id)
    scenario: str = "adhoc"
    source: str = "stand-in"
    retrieval_setting: str = "A"
    question: str = ""
    start_time: str = field(default_factory=utc_now_iso)
    start_perf: float = field(default_factory=time.perf_counter)
    queued_ms: float = 0.0
    # Time blocked inside the token limiter, waiting for budget to free up. It is
    # neither queueing nor work, and leaving it out once hid 49 s of a 50 s request.
    limit_wait_ms: float = 0.0
    working_ms: float = 0.0
    retrying_ms: float = 0.0
    backoff_ms: float = 0.0
    ttft_ms: float | None = None
    total_ms: float = 0.0
    status: str = "ok"
    retries: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    answer_grade: str = ""
    calls: list[dict[str, object]] = field(default_factory=list)
    notes: dict[str, object] = field(default_factory=dict)

    def finish(self) -> None:
        self.total_ms = (time.perf_counter() - self.start_perf) * 1000

    def to_dict(self) -> dict[str, object]:
        return {
            "request_id": self.request_id,
            "scenario": self.scenario,
            "source": self.source,
            "retrieval_setting": self.retrieval_setting,
            "question": self.question,
            "start_time": self.start_time,
            "queued_ms": round(self.queued_ms, 1),
            "limit_wait_ms": round(self.limit_wait_ms, 1),
            "waiting_ms": round(self.queued_ms + self.limit_wait_ms, 1),
            "working_ms": round(self.working_ms, 1),
            "retrying_ms": round(self.retrying_ms, 1),
            "backoff_ms": round(self.backoff_ms, 1),
            "first_token_ms": None if self.ttft_ms is None else round(self.ttft_ms, 1),
            "total_ms": round(self.total_ms, 1),
            "status": self.status,
            "retries": self.retries,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "answer_grade": self.answer_grade,
            "calls": self.calls,
            "notes": self.notes,
        }


class JsonlWriter:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: dict[str, object]) -> None:
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def percentile(values: list[float], q: float) -> float | None:
    """Linear-interpolated percentile; returns None for an empty sample."""
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    position = (len(ordered) - 1) * (q / 100.0)
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    fraction = position - low
    return float(ordered[low] + (ordered[high] - ordered[low]) * fraction)


def pid_is_alive(pid: int) -> bool:
    if os.name == "nt":
        import subprocess

        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}"], capture_output=True, text=True
        )
        return str(pid) in result.stdout
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True
