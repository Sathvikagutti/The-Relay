"""Five load scenarios, each run against a fresh limiter so they cannot leak into
one another. The point is not "does the server stay up" but "who gets dropped, how
long do the survivors wait, and how often do we hit a hard ceiling".

Every row lands in results/load/<scenario>.csv with exactly the results.csv columns,
so the tables in the report are computed from data rather than typed by hand.
"""

from __future__ import annotations

import asyncio
import csv
import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from relay.config import PROJECT_ROOT
from relay.experiments.run_eval import load_questions
from relay.grading import auto_grade
from relay.obs.csvio import row_from_trace, write_results
from relay.pipeline.engine import PipelineConfig
from relay.runtime import DOCUMENTED_LIMITS, LimiterLimits, build_runtime

LOAD_DIR = PROJECT_ROOT / "results" / "load"

# The stand-in enforces these per request so that the server, not just the client
# limiter, can be the thing that says no.
SERVER_DOCUMENTED = {"rpm": "30", "tpm": "8000", "rpd": "1000", "tpd": "200000"}


@dataclass(slots=True)
class Scenario:
    name: str
    count: int
    rate_per_min: float
    concurrency: int
    limits: LimiterLimits
    server: dict[str, str] = field(default_factory=lambda: dict(SERVER_DOCUMENTED))
    force_day_exhausted: bool = False
    top_k: int = 2  # lean context: these runs measure the scheduler, not retrieval quality


def _halved() -> LimiterLimits:
    return LimiterLimits(
        rpm=DOCUMENTED_LIMITS.rpm // 2,
        rpd=DOCUMENTED_LIMITS.rpd,
        tpm=DOCUMENTED_LIMITS.tpm // 2,
        tpd=DOCUMENTED_LIMITS.tpd,
    )


SCENARIOS: dict[str, Scenario] = {
    # Offered below the token ceiling: should be almost all ok, queue near zero.
    "steady": Scenario("steady", count=14, rate_per_min=4, concurrency=2, limits=DOCUMENTED_LIMITS),
    # 30 requests inside a couple of seconds: RPM and TPM both crossed instantly.
    "burst": Scenario("burst", count=30, rate_per_min=600, concurrency=30, limits=DOCUMENTED_LIMITS),
    # More work than one minute can ever absorb, held for a minute.
    "overload": Scenario("overload", count=45, rate_per_min=60, concurrency=8, limits=DOCUMENTED_LIMITS),
    # The scenario most people forget: limits change under you.
    "limit_halved": Scenario("limit_halved", count=22, rate_per_min=25, concurrency=4, limits=_halved()),
    # Day budget gone: no amount of waiting inside the request helps.
    "daily_exhausted": Scenario(
        "daily_exhausted",
        count=12,
        rate_per_min=60,
        concurrency=4,
        limits=DOCUMENTED_LIMITS,
        server={**SERVER_DOCUMENTED, "exhaust_day": "1"},
        force_day_exhausted=True,
    ),
}

PIPELINE = PipelineConfig(
    deadline_ms=30_000,
    context_token_budget=900,
    max_tokens_answer=220,
)
MAX_WAITING = 64


@dataclass(slots=True)
class ScenarioResult:
    scenario: str
    rows: list[dict[str, object]]
    wall_seconds: float
    peak_waiting: int
    peak_inflight: int


async def run_scenario(scenario: Scenario, *, source: str) -> ScenarioResult:
    runtime = build_runtime(
        source=source,
        setting_name="A",
        limits=scenario.limits,
        config=PipelineConfig(
            deadline_ms=PIPELINE.deadline_ms,
            context_token_budget=PIPELINE.context_token_budget,
            max_tokens_answer=PIPELINE.max_tokens_answer,
        ),
        trace_name=f"load_{scenario.name}_{source}",
        max_inflight=scenario.concurrency,
        max_waiting=MAX_WAITING,
        budget_state=False,
        top_k_override=scenario.top_k,
    )
    relay = runtime.relay
    relay.extra_query = dict(scenario.server)
    if scenario.force_day_exhausted:
        runtime.limiter.force_exhaust_day()

    questions = load_questions()
    interval = 60.0 / scenario.rate_per_min
    semaphore = asyncio.Semaphore(scenario.concurrency)
    rows: list[dict[str, object]] = []

    async def one(index: int) -> None:
        question = questions[index % len(questions)]
        async with semaphore:
            trace, _answer = await relay.run(
                question.question,
                scenario=scenario.name,
                grader=lambda ans, q=question: auto_grade(ans, q),
            )
        rows.append(row_from_trace(trace.to_dict()))

    started = time.perf_counter()
    tasks: list[asyncio.Task[None]] = []
    for index in range(scenario.count):
        target = started + index * interval
        delay = target - time.perf_counter()
        if delay > 0:
            await asyncio.sleep(delay)
        tasks.append(asyncio.create_task(one(index)))
    await asyncio.gather(*tasks)
    wall = time.perf_counter() - started

    rows.sort(key=lambda row: str(row["start_time"]))
    return ScenarioResult(
        scenario=scenario.name,
        rows=rows,
        wall_seconds=wall,
        peak_waiting=runtime.queue.peak_waiting,
        peak_inflight=runtime.queue.peak_inflight,
    )


async def run_all(
    names: list[str], *, source: str, out_dir: Path = LOAD_DIR
) -> list[ScenarioResult]:
    out_dir.mkdir(parents=True, exist_ok=True)
    results: list[ScenarioResult] = []
    for name in names:
        scenario = SCENARIOS[name]
        print(f"[load] {name}: {scenario.count} requests at {scenario.rate_per_min:g}/min ...", flush=True)
        result = await run_scenario(scenario, source=source)
        write_results(result.rows, out_dir / f"{name}.csv")
        statuses: dict[str, int] = {}
        for row in result.rows:
            statuses[str(row["status"])] = statuses.get(str(row["status"]), 0) + 1
        totals = [float(row["total_ms"]) for row in result.rows]
        print(
            f"  wall={result.wall_seconds:.1f}s  statuses={statuses}  "
            f"total_p50={statistics.median(totals):.0f}ms  "
            f"peak_waiting={result.peak_waiting}  peak_inflight={result.peak_inflight}",
            flush=True,
        )
        results.append(result)
    return results


def append_summary(results: list[ScenarioResult], path: Path) -> None:
    """Queue gauges are not columns in results.csv, so keep them beside it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["scenario", "wall_seconds", "peak_waiting", "peak_inflight", "requests"])
        for item in results:
            writer.writerow(
                [
                    item.scenario,
                    round(item.wall_seconds, 2),
                    item.peak_waiting,
                    item.peak_inflight,
                    len(item.rows),
                ]
            )


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")
