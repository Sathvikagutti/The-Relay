"""Run the 20-question evaluation set for one retrieval setting.

Answers are graded twice:
  * `answer_grade` in the CSV is the mechanical grade (gold region + verified quotes);
  * `eval/manual_grades.csv` carries the same answers for human verification against
    the PDFs, which is what the report's quality numbers use.

Sequential by default. The point of this run is comparable per-question cost and
latency, not throughput; overlapping requests would let one question's queueing
delay distort another's numbers.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from relay.config import PROJECT_ROOT
from relay.grading import auto_grade, load_questions
from relay.obs.csvio import row_from_trace
from relay.pipeline.engine import PipelineConfig
from relay.runtime import DOCUMENTED_LIMITS, build_runtime
from relay.scheduling.limiter import LimiterLimits

RELAXED = LimiterLimits(rpm=600, tpm=2_000_000, rpd=100_000, tpd=50_000_000)


@dataclass(frozen=True, slots=True)
class EvalResult:
    rows: list[dict[str, object]]
    answers: list[dict[str, object]]


async def run_eval(
    *,
    setting: str,
    source: str,
    limit_profile: str = "relaxed",
    questions_path: Path | None = None,
    trace_name: str | None = None,
) -> EvalResult:
    limits = RELAXED if limit_profile == "relaxed" else DOCUMENTED_LIMITS
    runtime = build_runtime(
        source=source,
        setting_name=setting,
        limits=limits,
        config=PipelineConfig(deadline_ms=120_000 if source == "real" else 30_000),
        trace_name=trace_name or f"eval_{setting}_{source}",
        budget_state=False,
    )
    questions = load_questions(questions_path)
    rows: list[dict[str, object]] = []
    answers: list[dict[str, object]] = []
    try:
        for question in questions:
            trace, answer = await runtime.relay.run(
                question.question,
                scenario="eval",
                grader=lambda ans, q=question: auto_grade(ans, q),
            )
            grade = trace.answer_grade
            rows.append(row_from_trace(trace.to_dict()))
            answers.append(
                {
                    "question_id": question.id,
                    "category": question.category,
                    "request_id": trace.request_id,
                    "answer_grade": grade,
                    "status": trace.status,
                    "answer": answer.text,
                    "reference": question.reference,
                    "citations": [
                        {
                            "label": citation.label,
                            "quote": citation.quote,
                            "verified": citation.verified,
                        }
                        for citation in answer.citations
                    ],
                    "tokens_in": trace.tokens_in,
                    "tokens_out": trace.tokens_out,
                    "retries": trace.retries,
                    "first_token_ms": trace.ttft_ms,
                    "total_ms": trace.total_ms,
                }
            )
    finally:
        await runtime.aclose()

    out_dir = PROJECT_ROOT / "results" / "eval"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"eval_{setting}_{source}.json").write_text(
        json.dumps(answers, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return EvalResult(rows=rows, answers=answers)
