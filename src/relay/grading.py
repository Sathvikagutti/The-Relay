"""Gold-answer loading and mechanical grading.

Two distinct jobs, kept apart on purpose:

  * `citation_hits_gold` is mechanical: does a citation come from the region of the
    paper where the answer lives? It is cheap, reproducible, and it is what the
    load-test rows use (there is no human in the loop for 500 requests).

  * Human grading for the 20-question evaluation is done from
    `eval/manual_grades.csv`, which ships the model answer, its quotations and the
    reference answer side by side. The assignment explicitly forbids treating an
    LLM's opinion as ground truth, so no model judges another model here.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from relay.config import PROJECT_ROOT
from relay.models import Answer, Citation

GRADES = ("correct", "wrong", "refused_correctly", "refused_wrongly")
STATUSES = ("ok", "rate_limited", "timeout", "error")


@dataclass(frozen=True, slots=True)
class GoldRegion:
    paper: str
    page_min: int
    page_max: int
    section: str = ""


@dataclass(frozen=True, slots=True)
class Question:
    id: str
    category: str
    question: str
    answerable: bool
    gold: tuple[GoldRegion, ...]
    reference: str


def default_questions_path() -> Path:
    return PROJECT_ROOT / "eval" / "questions.yaml"


def load_questions(path: Path | None = None) -> list[Question]:
    raw = yaml.safe_load((path or default_questions_path()).read_text(encoding="utf-8"))
    questions: list[Question] = []
    for item in raw:
        gold = tuple(
            GoldRegion(
                paper=str(region["paper"]),
                page_min=int(region["pages"][0]),
                page_max=int(region["pages"][1]),
                section=str(region.get("section", "")),
            )
            for region in item.get("gold") or []
        )
        questions.append(
            Question(
                id=str(item["id"]),
                category=str(item["category"]),
                question=str(item["question"]),
                answerable=bool(item["answerable"]),
                gold=gold,
                reference=str(item.get("reference", "")),
            )
        )
    return questions


def citation_hits_gold(citation: Citation, regions: tuple[GoldRegion, ...]) -> bool:
    for region in regions:
        if citation.paper_key != region.paper:
            continue
        if region.page_min <= citation.page <= region.page_max:
            if not region.section or citation.section.startswith(region.section):
                return True
    return False


def auto_grade(answer: Answer, question: Question) -> str:
    """Mechanical grade in the four values the CSV allows."""
    if answer.refused or answer.status != "ok":
        return "refused_correctly" if not question.answerable else "refused_wrongly"
    if not question.answerable:
        return "wrong"  # answered a question the papers do not answer
    if any(citation_hits_gold(citation, question.gold) for citation in answer.citations):
        return "correct"
    return "wrong"
