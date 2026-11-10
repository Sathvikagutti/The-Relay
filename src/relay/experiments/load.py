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

import httpx

from relay.config import PROJECT_ROOT, Settings
from relay.experiments.run_eval import load_questions
from relay.grading import auto_grade
from relay.obs.csvio import row_from_trace, write_results
from relay.pipeline.engine import PipelineConfig
from relay.runtime import DOCUMENTED_LIMITS, LimiterLimits, build_runtime

LOAD_DIR = PROJECT_ROOT / "results" / "load"

# The stand-in enforces these per request so that the server, not just the client
# limiter, can be the thing that says no. The fault rates are stated explicitly, at
# zero, on every scenario that does not want them: the server keeps these in a
# process-global PARAMS, so an earlier `faulty` run would otherwise leave 15% server
# errors switched on for every scenario that ran after it.
SERVER_DOCUMENTED = {
    "rpm": "30",
    "tpm": "8000",
    "rpd": "1000",
    "tpd": "200000",
    "fail": "0",
    "timeout": "0",
    "partial": "0",
}


@dataclass(slots=True)
class Scenario:
    name: str
    count: int
    rate_per_min: float
    # Concurrent calls the client keeps open. This is the queue's in-flight limit:
    # anything above it waits in the bounded admission queue instead of being
    # dropped. An earlier version also wrapped each request in a semaphore of the
    # same size, which meant nothing ever waited and `peak_waiting` always read 1.
    concurrency: int
    limits: LimiterLimits
    server: dict[str, str] = field(default_factory=lambda: dict(SERVER_DOCUMENTED))
    force_day_exhausted: bool = False
    top_k: int = 2  # lean context: these runs measure the scheduler, not retrieval quality
    # Charge the limiter before the first request so the degradation ladder is
    # exercised by traffic rather than by a unit test alone.
    prefill_tokens: int = 0


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
    "burst": Scenario("burst", count=30, rate_per_min=600, concurrency=4, limits=DOCUMENTED_LIMITS),
    # More work than one minute can ever absorb, held for a minute.
    "overload": Scenario("overload", count=45, rate_per_min=60, concurrency=4, limits=DOCUMENTED_LIMITS),
    # The scenario most people forget: limits change under you.
    "limit_halved": Scenario("limit_halved", count=22, rate_per_min=25, concurrency=4, limits=_halved()),
    # Sustained overload: twice the documented request rate, held for four minutes.
    # The earlier 45-second run could not show whether the system degrades or recovers.
    "sustained": Scenario(
        "sustained", count=240, rate_per_min=60, concurrency=4, limits=DOCUMENTED_LIMITS
    ),
    # Faults other than 429: server errors, timeouts and truncated streams.
    # Synthetic and labelled as such; the real fault rate can only come from the probe.
    "faulty": Scenario(
        "faulty",
        count=40,
        rate_per_min=30,
        concurrency=4,
        limits=DOCUMENTED_LIMITS,
        server={
            **SERVER_DOCUMENTED,
            "fail": "0.15",
            "timeout": "0.05",
            "partial": "0.10",
        },
    ),
    # Graceful degradation: the minute budget starts 65% spent, so the ladder has to
    # drop the analysis call and then trim context instead of failing outright.
    "degraded": Scenario(
        "degraded",
        count=30,
        rate_per_min=12,
        concurrency=4,
        limits=DOCUMENTED_LIMITS,
        prefill_tokens=5_200,
    ),
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
    source: str = "stand-in"
    offered_per_min: float = 0.0


async def reset_standin(base_url: str) -> None:
    """Ask the stand-in for a clean minute/day window before each scenario.

    Without this the scenarios are not independent: the simulator's buckets are
    process-global, so `limit_halved` would inherit the empty minute left by the
    240-request `sustained` run and refuse all 22 requests at 4 ms - a property of the
    harness, not of the scheduler.
    """
    root = base_url.rstrip("/").removesuffix("/v1")
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(f"{root}/reset")
        response.raise_for_status()


async def run_scenario(scenario: Scenario, *, source: str) -> ScenarioResult:
    if source == "stand-in":
        await reset_standin(Settings().standin_base_url)
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
        truncate_trace=True,
        max_inflight=scenario.concurrency,
        max_waiting=MAX_WAITING,
        budget_state=False,
        top_k_override=scenario.top_k,
    )
    relay = runtime.relay
    relay.extra_query = dict(scenario.server)
    if scenario.force_day_exhausted:
        runtime.limiter.force_exhaust_day()
    if scenario.prefill_tokens:
        reservation = await runtime.limiter.acquire(scenario.prefill_tokens, deadline_s=5.0)
        await runtime.limiter.reconcile(reservation, scenario.prefill_tokens)

    questions = load_questions()
    interval = 60.0 / scenario.rate_per_min
    rows: list[dict[str, object]] = []

    async def one(index: int) -> None:
        question = questions[index % len(questions)]
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
        source=source,
        offered_per_min=scenario.rate_per_min,
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
    """Queue gauges are not columns in results.csv, so keep them beside it.

    Rows for scenarios not in this run are kept: running three scenarios must not
    erase the summary of the five that ran earlier.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    merged: dict[str, ScenarioResult | dict[str, str]] = {}
    if path.exists():
        with path.open(encoding="utf-8", newline="") as old:
            merged.update({row["scenario"]: row for row in csv.DictReader(old)})
    merged.update({item.scenario: item for item in results})
    results = sorted(merged.values(), key=lambda item: str(getattr(item, "scenario", "")))  # type: ignore[arg-type]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        # duration and offered rate are not columns of results.csv (its schema is fixed
        # by the brief), so they live beside it and Table 2a joins on scenario name.
        writer.writerow(
            [
                "scenario",
                "wall_seconds",
                "peak_waiting",
                "peak_inflight",
                "requests",
                "source",
                "offered_per_min",
            ]
        )
        for item in results:
            if isinstance(item, dict):  # a row kept from an earlier run
                writer.writerow(
                    [
                        item.get("scenario"),
                        item.get("wall_seconds"),
                        item.get("peak_waiting"),
                        item.get("peak_inflight"),
                        item.get("requests"),
                        item.get("source"),
                        item.get("offered_per_min"),
                    ]
                )
                continue
            writer.writerow(
                [
                    item.scenario,
                    round(item.wall_seconds, 2),
                    item.peak_waiting,
                    item.peak_inflight,
                    len(item.rows),
                    item.source,
                    round(item.offered_per_min, 1),
                ]
            )


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")
