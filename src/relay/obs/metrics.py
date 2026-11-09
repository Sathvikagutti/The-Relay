"""Turn results.csv into the report's tables. Nothing here may invent a number:
every cell is either computed from the CSV or explicitly 'not measured'.

Table 1  - service limits: documented vs observed (results/limits.json)
Table 2a - latency by scenario
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

from relay.config import PROJECT_ROOT
from relay.obs.events import percentile

RESULTS = PROJECT_ROOT / "results"
CSV_PATH = RESULTS / "results.csv"
LIMITS_PATH = RESULTS / "limits.json"
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
    return f"{100.0 * part / whole:.0f}%" if whole else "n/a"


def window_seconds(rows: list[dict[str, str]]) -> float:
    """Wall clock covered by the rows: last end minus first start."""
    starts = [datetime.fromisoformat(row["start_time"]) for row in rows]
    ends = [
        datetime.fromisoformat(row["start_time"]).timestamp() + float(row["total_ms"]) / 1000.0
        for row in rows
    ]
    return max(ends) - min(item.timestamp() for item in starts)


def peak_overlap(rows: list[dict[str, str]]) -> int:
    """Queue gauge computed from the CSV alone.

    Each request occupies [start_time, start_time + total_ms]. total_ms includes
    time spent waiting for a slot, so the maximum overlap counts everyone holding
    or waiting for capacity - the closest thing to queue length that the required
    columns can express. Stated as a definition, not as a measured gauge.
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
    requests: int
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


def scenario_stats(name: str, rows: list[dict[str, str]]) -> ScenarioStats:
    ttft = [value for row in rows if (value := _float(row["first_token_ms"])) is not None]
    total = [_float(row["total_ms"]) or 0.0 for row in rows]
    retries = [int(row["retries"]) for row in rows]
    tokens = [_float(row["tokens_out"]) for row in rows if row["status"] == "ok"]
    return ScenarioStats(
        scenario=name,
        requests=len(rows),
        statuses=Counter(row["status"] for row in rows),
        ttft_p50=percentile(ttft, 50) if ttft else None,
        ttft_p95=percentile(ttft, 95) if ttft else None,
        ttft_p99=percentile(ttft, 99) if ttft else None,
        total_p50=percentile(total, 50),
        total_p95=percentile(total, 95),
        total_p99=percentile(total, 99),
        retries_per_request=sum(retries) / len(retries) if retries else 0.0,
        peak_queue=peak_overlap(rows),
        tokens_out_per_answer=(
            sum(item for item in tokens if item is not None) / len(tokens) if tokens else None
        ),
    )


def table_1(limits_path: Path = LIMITS_PATH) -> str:
    lines = [
        "| Limit | Documented | Observed | Evidence |",
        "| --- | --- | --- | --- |",
    ]
    if not limits_path.exists():
        from relay.runtime import DOCUMENTED_LIMITS

        missing = "not measured"
        reason = "`relay probe-limits` needs GROQ_API_KEY"
        return "\n".join(
            [
                "| Limit | Documented | Observed | Evidence |",
                "| --- | --- | --- | --- |",
                f"| Requests per minute | {DOCUMENTED_LIMITS.rpm} | {missing} | {reason} |",
                f"| Requests per day | {DOCUMENTED_LIMITS.rpd} | {missing} | header value only |",
                f"| Tokens per minute | {DOCUMENTED_LIMITS.tpm} | {missing} | header value only |",
                f"| Tokens per day | {DOCUMENTED_LIMITS.tpd} | {missing} | docs only |",
                f"| 429 body + retry-after | - | {missing} | {reason} |",
                f"| TTFT (small prompt) | - | {missing} | {reason} |",
            ]
        )
    data = json.loads(limits_path.read_text(encoding="utf-8"))
    documented = data["documented"]
    observed = data.get("observed_from_headers", {})
    rpm = data.get("rpm_probe", {})
    tpm = data.get("tpm_probe", {})
    recovery = data.get("recovery", {})
    lines += [
        f"| Requests per minute | {documented['rpm']} | "
        f"{'confirmed: first 429 after ' + str(rpm.get('ok')) + ' concurrent calls' if rpm.get('rate_limited') else 'not reached'} "
        f"| 32 concurrent minimal calls |",
        f"| Requests per day | {documented['rpd']} | {observed.get('rpd', 'not measured')} "
        f"| `x-ratelimit-limit-requests` header |",
        f"| Tokens per minute | {documented['tpm']} | {observed.get('tpm', 'not measured')} "
        f"| `x-ratelimit-limit-tokens` header |",
        f"| Tokens per day | {documented['tpd']} | not measured (would cost 200k tokens) | docs only |",
        f"| 429 body | - | {str(rpm.get('sample_body'))[:60] or 'not measured'} | probe JSONL |",
        f"| Retry-after | - | {rpm.get('retry_after_s') or 'not measured'} s | 429 header |",
        f"| Recovery after burst | - | {recovery.get('seconds', 'not measured')} s | poll every 2 s |",
        f"| TTFT (small prompt) | - | p50 {_ms(data.get('latency', {}).get('ttft_p50_ms'))} ms, "
        f"p95 {_ms(data.get('latency', {}).get('ttft_p95_ms'))} ms | 10 paced calls |",
    ]
    return "\n".join(lines)


def table_2a(stats: list[ScenarioStats]) -> str:
    lines = [
        "| Scenario | Requests | TTFT p50 | TTFT p95 | TTFT p99 | Total p50 | Total p95 | Total p99 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in stats:
        lines.append(
            f"| {item.scenario} | {item.requests} | {_ms(item.ttft_p50)} | {_ms(item.ttft_p95)} | "
            f"{_ms(item.ttft_p99)} | {_ms(item.total_p50)} | {_ms(item.total_p95)} | {_ms(item.total_p99)} |"
        )
    return "\n".join(lines)


def table_2b(stats: list[ScenarioStats]) -> str:
    lines = [
        "| Scenario | Succeeded | Rate-limited | Timed out or given up | Retries/request | Peak queue | Tokens out/answer | Cost/1000 answers |",
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
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        if row["scenario"] == "eval":
            grouped.setdefault(row["retrieval_setting"], []).append(row)
    lines = [
        f"| Setting | Questions | Correct and cited | Wrong | Refused correctly | Refused when answerable | "
        f"Tokens out/answer | TTFT p50 | TTFT p95 | Total p50 | Total p95 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for setting in sorted(grouped):
        items = grouped[setting]
        grades = [human.get(row["request_id"], row["answer_grade"]) for row in items]
        counts = Counter(grades)
        ok = [row for row in items if row["status"] == "ok"]
        ttft = [v for row in ok if (v := _float(row["first_token_ms"])) is not None]
        total = [_float(row["total_ms"]) or 0.0 for row in ok]
        tokens = [_float(row["tokens_out"]) or 0.0 for row in ok]
        lines.append(
            f"| {setting} | {len(items)} | {_pct(counts.get('correct', 0), len(items))} | "
            f"{_pct(counts.get('wrong', 0), len(items))} | "
            f"{_pct(counts.get('refused_correctly', 0), len(items))} | "
            f"{_pct(counts.get('refused_wrongly', 0), len(items))} | "
            f"{_ms(sum(tokens) / len(tokens) if tokens else None)} | "
            f"{_ms(percentile(ttft, 50) if ttft else None)} | "
            f"{_ms(percentile(ttft, 95) if ttft else None)} | "
            f"{_ms(percentile(total, 50) if total else None)} | "
            f"{_ms(percentile(total, 95) if total else None)} |"
        )
    lines.append("")
    lines.append(f"Source: {source_label}. Grades: {'human (eval/manual_grades.csv)' if human else 'automatic gold-region check, not human'}.")
    return "\n".join(lines)


def all_tables(csv_path: Path = CSV_PATH) -> str:
    rows = read_rows(csv_path)
    stats = [scenario_stats(name, items) for name, items in sorted(by_scenario(rows).items())]
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
        "Peak queue = maximum overlap of [start_time, start_time + total_ms] intervals, computed from the CSV.",
        "Cost is $0.00 because the free tier is not billed; no list price was paid, so no list-price figure is reported.",
    ]
    return "\n".join(parts)
