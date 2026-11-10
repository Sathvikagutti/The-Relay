"""Build the human grading material from an evaluation run.

Two artefacts, deliberately separate:

  * `eval/manual_grades.csv` - one row per graded answer with blank judgement
    columns. This is the file a person fills in; `relay tables` prefers its
    `final_grade` whenever it is present.
  * `eval/review_sheet.md` - the same rows in reading order, with the question,
    the answer, the quotations actually verified, and the reference answer from
    `eval/questions.yaml` side by side, so grading does not need the terminal.

No model grades another model here: the blank columns are for a human.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from relay.config import PROJECT_ROOT
from relay.grading import load_questions

EVAL_DIR = PROJECT_ROOT / "results" / "eval"
GRADES_CSV = PROJECT_ROOT / "eval" / "manual_grades.csv"
SHEET_MD = PROJECT_ROOT / "eval" / "review_sheet.md"

FIELDS = [
    "request_id",
    "setting",
    "question_id",
    "category",
    "answerable",
    "auto_grade",
    "final_grade",
    "evidence_support",
    "citation_correct",
    "abstention_correct",
    "notes",
]

# Allowed values, written into the sheet header so the columns are not free text.
LEGEND = (
    "final_grade: correct | wrong | refused_correctly | refused_wrongly | leave blank to keep the automatic grade. "
    "evidence_support: supported | partly | unsupported. citation_correct: yes | no | n/a. "
    "abstention_correct: yes | no | n/a."
)


def _answers(setting: str, source: str) -> list[dict]:
    path = EVAL_DIR / f"eval_{setting}_{source}.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def build(source: str = "stand-in", settings: tuple[str, ...] = ("A", "B", "C")) -> tuple[int, int]:
    questions = {q.id: q for q in load_questions()}
    rows: list[dict[str, str]] = []
    sections: list[str] = [
        "# Manual grading sheet",
        "",
        f"Source: {source}. {LEGEND}",
        "",
        "Grade against the papers, not against the reference answer alone: the reference is",
        "a pointer to the right region, and a correct answer may be worded differently.",
        "",
    ]
    for setting in settings:
        for item in _answers(setting, source):
            qid = item.get("question_id", "")
            question = questions.get(qid)
            rows.append(
                {
                    "request_id": item.get("request_id", ""),
                    "setting": setting,
                    "question_id": qid,
                    "category": item.get("category", ""),
                    "answerable": "yes" if question and question.answerable else "no",
                    "auto_grade": item.get("answer_grade", ""),
                    "final_grade": "",
                    "evidence_support": "",
                    "citation_correct": "",
                    "abstention_correct": "",
                    "notes": "",
                }
            )
            sections += [
                f"## {setting} / {qid} - {item.get('category', '')} "
                f"({'answerable' if question and question.answerable else 'not answerable'})",
                "",
                f"**Asked:** {question.question if question else item.get('question', '')}",
                "",
                f"**Answer:** {item.get('answer', '')}",
                "",
                "**Citations:**",
                "",
            ]
            citations = item.get("citations") or []
            if citations:
                for cite in citations:
                    mark = "verified" if cite.get("verified") else "UNVERIFIED"
                    sections.append(f"- {cite.get('label', '')} ({mark}): \"{cite.get('quote', '')}\"")
            else:
                sections.append("- none")
            sections += [
                "",
                f"**Reference:** {question.reference if question else ''}",
                "",
                f"**Automatic grade:** `{item.get('answer_grade', '')}`  |  "
                f"first token {item.get('first_token_ms')} ms, total {item.get('total_ms')} ms, "
                f"{item.get('tokens_out')} tokens out",
                "",
                "Fill in: final_grade ___ evidence_support ___ citation_correct ___ "
                "abstention_correct ___ notes ___",
                "",
            ]

    GRADES_CSV.parent.mkdir(parents=True, exist_ok=True)
    with GRADES_CSV.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    SHEET_MD.write_text("\n".join(sections), encoding="utf-8")
    return len(rows), len(sections)
