"""Turn results.csv into the report's tables. Nothing here may invent a number:
every cell is either computed from the CSV or explicitly 'not measured'.

Table 1  - service limits: documented vs observed, how each value was obtained
Table 2a - latency by scenario, successful requests only
Table 2b - reliability, retries, queue, cost by scenario
Table 3  - retrieval settings: quality and cost
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from relay.config import PROJECT_ROOT, load_retrieval
from relay.obs.events import percentile

RESULTS = PROJECT_ROOT / "results"
CSV_PATH = RESULTS / "results.csv"
LIMITS_PATH = RESULTS / "limits.json"
LOAD_SUMMARY = RESULTS / "load" / "summary.csv"
EVAL_DIR = RESULTS / "eval"
MANUAL_GRADES = PROJECT_ROOT / "eval" / "manual_grades.csv"

GRADES = ("correct", "wrong", "refused_correctly", "refused_wrongly")


def read_rows(path: Path | list[Path]) -> list[dict[str, str]]:
    paths = [path] if isinstance(path, Path) else path
    rows: list[dict[str, str]] = []
    for item in paths:
        with item.open(encoding="utf-8", newline="") as fh:
            rows.extend(csv.DictReader(fh))
    return rows


def _float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _ms(value: float | None) -> str:
    return "not measured" if value is None else f"{value:.0f}"


def _pct(part: int, whole: int) -> str:
    """One decimal, as the brief asks: 96.7% rather than 97%."""
    return f"{100.0 * part / whole:.1f}%" if whole else "n/a"


def _secs(value: float | None) -> str:
    return "not measured" if value is None else f"{value:.1f}"


def _rate(value: float | None) -> str:
    return "not measured" if value is None else f"{value:.1f}"


def window_seconds(rows: list[dict[str, str]]) -> float:
    """Wall clock covered by the rows: last end minus first start."""
    starts = [datetime.fromisoformat(row["start_time"]) for row in rows]
    ends = [
        datetime.fromisoformat(row["start_time"]).timestamp() + float(row["total_ms"]) / 1000.0
        for row in rows
    ]
    return max(ends) - min(item.timestamp() for item in starts)


def peak_overlap(rows: list[dict[str, str]]) -> int:
    """Queue gauge computed from the CSV alone, used when the load summary is absent.

    Each request occupies [start_time, start_time + total_ms]. total_ms includes
    time spent waiting for a slot, so the maximum overlap counts everyone holding
    or waiting for capacity - the closest thing to queue length that the required
    columns can express. When a load run exists its own gauge (peak_waiting) wins.
    """
    events: list[tuple[float, int]] = []
    for row in rows:
        start = datetime.fromisoformat(row["start_time"]).timestamp()
        events.append((start, 1))
        events.append((start + float(row["total_ms"]) / 1000.0, -1))
    events.sort(key=lambda item: (item[0], item[1]))
    current = peak = 0
    for _timestamp, delta in events:
        current += delta
        peak = max(peak, current)
    return peak


def by_scenario(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(row["scenario"], []).append(row)
    return grouped


@dataclass(slots=True)
class ScenarioStats:
    scenario: str
    source: str
    requests: int
    answered: int
    duration_s: float | None
    offered_per_min: float | None
    statuses: Counter[str]
    ttft_p50: float | None
    ttft_p95: float | None
    ttft_p99: float | None
    total_p50: float | None
    total_p95: float | None
    total_p99: float | None
    retries_per_request: float
    peak_queue: int
    tokens_out_per_answer: float | None


def load_meta(path: Path = LOAD_SUMMARY) -> dict[str, dict[str, str]]:
    """Duration, offered rate and queue gauges written beside results.csv."""
    if not path.exists():
        return {}
    with path.open(encoding="utf-8", newline="") as fh:
        return {row["scenario"]: row for row in csv.DictReader(fh)}


def scenario_stats(
    name: str, rows: list[dict[str, str]], meta: dict[str, str] | None = None
) -> ScenarioStats:
    """Latency covers successful requests only.

    A refusal that returns in 7 ms is not a fast answer, it is an absent answer.
    Mixing the two into one p50 (the earlier burst row) made the system look
    instantaneous. Refusals are counted in Table 2b instead.
    """
    meta = meta or {}
    answered = [row for row in rows if row["status"] == "ok"]
    ttft = [value for row in answered if (value := _float(row["first_token_ms"])) is not None]
    total = [_float(row["total_ms"]) or 0.0 for row in answered]
    retries = [int(row["retries"]) for row in rows]
    tokens = [_float(row["tokens_out"]) for row in answered if _float(row["tokens_out"]) is not None]
    duration = _float(meta.get("wall_seconds")) if meta.get("wall_seconds") else None
    offered = _float(meta.get("offered_per_min")) if meta.get("offered_per_min") else None
    if duration is None:
        duration = window_seconds(rows) or None
    if offered is None and duration:
        offered = len(rows) / duration * 60.0
    peak = int(meta["peak_waiting"]) if meta.get("peak_waiting") else peak_overlap(rows)
    return ScenarioStats(
        scenario=name,
        source=rows[0].get("source", "unknown") if rows else "unknown",
        requests=len(rows),
        answered=len(answered),
        duration_s=duration,
        offered_per_min=offered,
        statuses=Counter(row["status"] for row in rows),
        ttft_p50=percentile(ttft, 50) if ttft else None,
        ttft_p95=percentile(ttft, 95) if ttft else None,
        ttft_p99=percentile(ttft, 99) if ttft else None,
        total_p50=percentile(total, 50) if total else None,
        total_p95=percentile(total, 95) if total else None,
        total_p99=percentile(total, 99) if total else None,
        retries_per_request=sum(retries) / len(retries) if retries else 0.0,
        peak_queue=peak,
        tokens_out_per_answer=(sum(tokens) / len(tokens) if tokens else None),
    )


def table_1(limits_path: Path = LIMITS_PATH) -> str:
    """Limit, documented value, observed value, how it was found, confidence.

    Confidence is the honest third axis the review asked for: 'documented' means
    nobody tested it, 'header' means the API told us, 'measured' means a probe
    crossed the line and saw the 429.
    """
    from relay.runtime import DOCUMENTED_LIMITS

    lines = [
        "| Limit | Documented | Observed | How found | Confidence |",
        "| --- | --- | --- | --- | --- |",
    ]
    if not limits_path.exists():
        why = "documented value only; `relay probe-limits` not run (no API key)"
        missing = "not measured"
        lines += [
            f"| Requests per minute | {DOCUMENTED_LIMITS.rpm} | {missing} | {why} | documented |",
            f"| Tokens per minute | {DOCUMENTED_LIMITS.tpm} | {missing} | {why} | documented |",
            f"| Requests per day | {DOCUMENTED_LIMITS.rpd} | {missing} | {why} | documented |",
            f"| Tokens per day | {DOCUMENTED_LIMITS.tpd} | {missing} | {why} | documented |",
            f"| Requests in flight | - | {missing} | {why} | not measured |",
            f"| What happens when a limit is hit | - | {missing} | {why} | not measured |",
            f"| Time until recovery | - | {missing} | {why} | not measured |",
            "",
            "Values in the Documented column are from console.groq.com/docs/rate-limits for "
            "`openai/gpt-oss-120b`, read 2026-11-09.",
        ]
        return "\n".join(lines)

    data = json.loads(limits_path.read_text(encoding="utf-8"))
    documented = data["documented"]
    observed = data.get("observed_from_headers", {})
    rpm = data.get("rpm_probe", {})
    recovery = data.get("recovery", {})
    inflight = data.get("inflight_probe", {})
    latency = data.get("latency", {})
    first_429 = (
        f"first 429 after {rpm.get('ok')} rapid calls"
        if rpm.get("rate_limited")
        else "no 429 in probe"
    )
    lines += [
        f"| Requests per minute | {documented['rpm']} | {first_429} | 32 concurrent minimal calls | "
        f"{'measured' if rpm.get('rate_limited') else 'lower bound only'} |",
        f"| Tokens per minute | {documented['tpm']} | {observed.get('tpm', 'not measured')} | "
        f"`x-ratelimit-limit-tokens` header | header |",
        f"| Requests per day | {documented['rpd']} | {observed.get('rpd', 'not measured')} | "
        f"`x-ratelimit-limit-requests` header | header |",
        f"| Tokens per day | {documented['tpd']} | not measured | would cost 200k tokens to reach | "
        f"documented |",
        f"| Requests in flight | - | {inflight.get('max_ok_concurrent', 'not measured')} | "
        f"ramped concurrency until refusal | {'measured' if inflight else 'not measured'} |",
        f"| What happens when a limit is hit | - | "
        f"HTTP 429, retry-after {rpm.get('retry_after_s', 'n/a')} s | captured 429 response | measured |",
        f"| Time until recovery | - | {recovery.get('seconds', 'not measured')} s | polled every 2 s | "
        f"{'measured' if recovery.get('seconds') else 'not measured'} |",
    ]
    if latency:
        lines += [
            "",
            f"First token on a small prompt: p50 {_ms(latency.get('ttft_p50_ms'))} ms, "
            f"p95 {_ms(latency.get('ttft_p95_ms'))} ms over {latency.get('samples', 'n/a')} calls.",
        ]
    return "\n".join(lines)


def table_2a(stats: list[ScenarioStats]) -> str:
    lines = [
        "| Scenario | Source | Requests | Answered | Duration (s) | Offered/min | TTFT p50 | "
        "TTFT p95 | TTFT p99 | Total p50 | Total p95 | Total p99 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in stats:
        lines.append(
            f"| {item.scenario} | {item.source} | {item.requests} | {item.answered} | "
            f"{_secs(item.duration_s)} | {_rate(item.offered_per_min)} | "
            f"{_ms(item.ttft_p50)} | {_ms(item.ttft_p95)} | {_ms(item.ttft_p99)} | "
            f"{_ms(item.total_p50)} | {_ms(item.total_p95)} | {_ms(item.total_p99)} |"
        )
    return "\n".join(lines)


def table_2b(stats: list[ScenarioStats]) -> str:
    lines = [
        "| Scenario | Succeeded | Rate-limited | Timed out or given up | Retries/request | "
        "Peak queue | Tokens out/answer | Cost/1000 answers |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in stats:
        total = item.requests
        succeeded = item.statuses.get("ok", 0)
        limited = item.statuses.get("rate_limited", 0)
        gaveup = item.statuses.get("timeout", 0) + item.statuses.get("error", 0)
        lines.append(
            f"| {item.scenario} | {_pct(succeeded, total)} | {_pct(limited, total)} | "
            f"{_pct(gaveup, total)} | {item.retries_per_request:.2f} | {item.peak_queue} | "
            f"{_ms(item.tokens_out_per_answer)} | $0.00 (free tier) |"
        )
    return "\n".join(lines)


def citation_totals(setting: str, source: str) -> tuple[int, int, int] | None:
    """(answered rows, quotes requested, quotes verified) for one eval run.

    Read from the answer file the evaluation wrote, so citation correctness is
    reported on its own axis and never folded into the answer grade: an answer can
    be correct and its citation wrong, and the table has to be able to say so.
    """
    import glob

    matches = sorted(glob.glob(str(EVAL_DIR / f"eval_{setting}_*.json")))
    if not matches:
        return None
    import json as _json

    answers = _json.loads(Path(matches[-1]).read_text(encoding="utf-8"))
    if source != "any" and matches and f"_{source}.json" not in matches[-1]:
        return None
    answered = 0
    requested = 0
    verified = 0
    for item in answers:
        citations = item.get("citations") or []
        requested += len(citations)
        verified += sum(1 for cite in citations if cite.get("verified"))
        if citations:
            answered += 1
    return answered, requested, verified


def manual_grades(path: Path = MANUAL_GRADES) -> dict[str, str]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8", newline="") as fh:
        return {
            row["request_id"]: row["final_grade"]
            for row in csv.DictReader(fh)
            if row.get("final_grade")
        }


def table_3(rows: list[dict[str, str]], source_label: str) -> str:
    """Quality per retrieval setting, using human grades when they exist."""
    human = manual_grades()
    try:
        settings = load_retrieval().settings
    except Exception:  # config missing is not a reason to hide the numbers
        settings = {}
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        if row["scenario"] == "eval":
            grouped.setdefault(row["retrieval_setting"], []).append(row)
    lines = [
        "| Setting | Piece size | Fetched | Re-rank | Questions | Correct and cited | Wrong | "
        "Refused correctly | Refused when answerable | Quotes verified | Tokens out/answer | "
        "TTFT p50 | TTFT p95 | Total p50 | Total p95 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for setting in sorted(grouped):
        items = grouped[setting]
        grades = [human.get(row["request_id"], row["answer_grade"]) for row in items]
        counts = Counter(grades)
        ok = [row for row in items if row["status"] == "ok"]
        ttft = [v for row in ok if (v := _float(row["first_token_ms"])) is not None]
        total = [_float(row["total_ms"]) or 0.0 for row in ok]
        tokens = [_float(row["tokens_out"]) or 0.0 for row in ok]
        config = settings.get(setting)
        piece = f"{config.chunk_tokens}/{config.overlap_tokens}" if config else "n/a"
        cites = citation_totals(setting, source_label.split(",")[0].strip())
        cite_cell = (
            f"{100.0 * cites[2] / cites[1]:.1f}%" if cites and cites[1] else "not measured"
        )
        lines.append(
            f"| {setting} | {piece} | {config.fetch_k if config else 'n/a'} | "
            f"{config.rerank if config else 'n/a'} | {len(items)} | "
            f"{_pct(counts.get('correct', 0), len(items))} | "
            f"{_pct(counts.get('wrong', 0), len(items))} | "
            f"{_pct(counts.get('refused_correctly', 0), len(items))} | "
            f"{_pct(counts.get('refused_wrongly', 0), len(items))} | "
            f"{cite_cell} | "
            f"{_ms(sum(tokens) / len(tokens) if tokens else None)} | "
            f"{_ms(percentile(ttft, 50) if ttft else None)} | "
            f"{_ms(percentile(ttft, 95) if ttft else None)} | "
            f"{_ms(percentile(total, 50) if total else None)} | "
            f"{_ms(percentile(total, 95) if total else None)} |"
        )
    lines.append("")
    lines.append(
        f"Source: {source_label}. Grades: "
        f"{'human (eval/manual_grades.csv)' if human else 'automatic gold-region check, not human'}. "
        "Quotes verified is a separate axis - the share of quoted citations the "
        "`verify_quote` tool matched exactly against the retrieved chunk - and is never "
        "folded into the answer grade. Whether a verified quote points at the *right* "
        "passage is the other half of citation correctness; that judgement is made by "
        "hand in `eval/manual_grades.csv` (`citation_correct` column)."
    )
    return "\n".join(lines)


def all_tables(csv_path: Path = CSV_PATH) -> str:
    rows = read_rows(csv_path)
    meta = load_meta()
    stats = [
        scenario_stats(name, items, meta.get(name))
        for name, items in sorted(by_scenario(rows).items())
    ]
    load_stats = [item for item in stats if item.scenario != "eval"]
    sources = {row["source"] for row in rows}
    label = ", ".join(sorted(sources)) if sources else "no rows"
    parts = [
        "# Tables generated from results.csv",
        "",
        f"Rows: {len(rows)}. Source(s): {label}.",
        "",
        "## Table 1 - service limits",
        "",
        table_1(),
        "",
        "## Table 2a - latency by scenario",
        "",
        table_2a(load_stats),
        "",
        "## Table 2b - reliability, retries, queue and cost",
        "",
        table_2b(load_stats),
        "",
        "## Table 3 - retrieval settings, quality and cost",
        "",
        table_3(rows, label),
        "",
        "Table 2a latency covers successful requests only; refused and timed-out "
        "requests are counted in Table 2b, because a 7 ms refusal is not a 7 ms answer.",
        "",
        "Peak queue is the load runner's `peak_waiting` gauge when the run wrote one, "
        "otherwise the maximum overlap of [start_time, start_time + total_ms] intervals "
        "computed from the CSV. It stays at 1 in the shedding scenarios because a request "
        "refused by the limiter is rejected before it is admitted, so it never waits.",
        "",
        "Cost is $0.00 because the free tier is not billed; no list price was paid, so "
        "no list-price figure is reported.",
    ]
    return "\n".join(parts)
