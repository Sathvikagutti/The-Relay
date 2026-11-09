"""results.csv: the raw file every table number must be recomputable from.

The column list and the allowed values are fixed by the assignment, so they are
enforced in one place and validated before anything is written.
"""

from __future__ import annotations

import csv
from pathlib import Path

from relay.grading import GRADES, STATUSES

COLUMNS = [
    "request_id",
    "scenario",
    "source",
    "start_time",
    "first_token_ms",
    "total_ms",
    "status",
    "retries",
    "tokens_in",
    "tokens_out",
    "retrieval_setting",
    "answer_grade",
]


def row_from_trace(trace: dict[str, object]) -> dict[str, object]:
    return {
        "request_id": trace["request_id"],
        "scenario": trace["scenario"],
        "source": trace["source"],
        "start_time": trace["start_time"],
        "first_token_ms": "" if trace.get("first_token_ms") is None else trace["first_token_ms"],
        "total_ms": trace["total_ms"],
        "status": trace["status"],
        "retries": trace.get("retries", 0),
        "tokens_in": trace.get("tokens_in", 0),
        "tokens_out": trace.get("tokens_out", 0),
        "retrieval_setting": trace.get("retrieval_setting", ""),
        "answer_grade": trace.get("answer_grade", ""),
    }


def validate_rows(rows: list[dict[str, object]]) -> list[str]:
    problems: list[str] = []
    for index, row in enumerate(rows, start=2):  # row 1 is the header
        missing = [column for column in COLUMNS if column not in row]
        if missing:
            problems.append(f"row {index}: missing columns {missing}")
            continue
        if row["status"] not in STATUSES:
            problems.append(f"row {index}: status {row['status']!r} not allowed")
        if row["answer_grade"] not in GRADES:
            problems.append(f"row {index}: answer_grade {row['answer_grade']!r} not allowed")
        if str(row["retrieval_setting"]) == "":
            problems.append(f"row {index}: retrieval_setting is empty")
        for numeric in ("total_ms", "tokens_in", "tokens_out", "retries"):
            try:
                float(str(row[numeric]))
            except ValueError:
                problems.append(f"row {index}: {numeric} is not numeric")
    return problems


def write_results(rows: list[dict[str, object]], path: Path) -> None:
    problems = validate_rows(rows)
    if problems:
        raise ValueError("refusing to write an invalid results file:\n" + "\n".join(problems))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row[column] for column in COLUMNS})


def read_results(path: Path) -> list[dict[str, object]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))
