"""Prompt construction and response parsing.

Both model calls return strict JSON. JSON costs a few tokens but removes an
entire class of parser bugs, and it makes "answerable: false" an explicit branch
instead of an implicit refusal hidden in prose.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from relay.models import Chunk
from relay.pipeline.tools import render_passages

ANALYSIS_SYSTEM = """You plan searches for an assistant that answers ONLY from three papers:
"Attention Is All You Need" (transformer architecture), "Moshi" (speech-text dialogue model),
and "Dynamic Chunking for End-to-End Hierarchical Sequence Modeling" (H-Net, byte-level chunking).
Return strict JSON only:
{"queries": ["1-3 short keyword queries"], "needs_multi": true|false, "answerable": true|false}
Set answerable=false only when the question is outside these papers' subject matter.
Use the papers' own terminology (e.g. "scaled dot-product attention", "inner monologue", "ratio loss")."""

DRAFT_SYSTEM = """You answer using ONLY the numbered passages provided. Return strict JSON only:
{"answerable": true|false, "answer": "<=110 words", "citations": [{"chunk_id": "...", "quote": "..."}]}
Rules:
- Every factual sentence needs a citation. The quote must be copied verbatim, 1-2 sentences, from that passage.
- Use only chunk_id values that appear in the passages.
- If the passages do not contain the answer, return {"answerable": false, "answer": "The papers do not state this.", "citations": []}
- Never rely on outside knowledge, and never guess a number that is not in a passage."""

REPAIR_TEMPLATE = """Your previous citations failed verification:
{errors}

Return the corrected JSON. Copy each quote character-for-character from the passage text.
If you cannot support a claim with a verbatim quote, remove the claim.
Previous answer:
{previous}"""


@dataclass(frozen=True, slots=True)
class Analysis:
    queries: tuple[str, ...]
    needs_multi: bool
    answerable: bool
    degraded: bool = False


@dataclass(frozen=True, slots=True)
class Draft:
    answerable: bool
    answer: str
    citations: list[dict[str, str]] = field(default_factory=list)


def extract_json(text: str) -> dict[str, object] | None:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def build_analysis_messages(question: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": ANALYSIS_SYSTEM},
        {"role": "user", "content": f"Question: {question}"},
    ]


def build_draft_messages(question: str, chunks: list[Chunk]) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": DRAFT_SYSTEM},
        {
            "role": "user",
            "content": f"Passages:\n\n{render_passages(chunks)}\n\nQuestion: {question}",
        },
    ]


def build_repair_messages(
    question: str, chunks: list[Chunk], errors: list[str], previous: str
) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": DRAFT_SYSTEM},
        {
            "role": "user",
            "content": (
                f"Passages:\n\n{render_passages(chunks)}\n\nQuestion: {question}\n\n"
                + REPAIR_TEMPLATE.format(
                    errors="\n".join(f"- {error}" for error in errors), previous=previous
                )
            ),
        },
    ]


def parse_analysis(text: str) -> Analysis:
    payload = extract_json(text)
    if payload is None:
        return Analysis(queries=(), needs_multi=False, answerable=True, degraded=True)
    queries = payload.get("queries") or []
    clean = tuple(str(query).strip() for query in queries if str(query).strip())[:3]
    return Analysis(
        queries=clean,
        needs_multi=bool(payload.get("needs_multi", False)),
        answerable=bool(payload.get("answerable", True)),
    )


def parse_draft(text: str) -> Draft | None:
    payload = extract_json(text)
    if payload is None:
        return None
    citations = payload.get("citations") or []
    clean = [
        {"chunk_id": str(item.get("chunk_id", "")), "quote": str(item.get("quote", ""))}
        for item in citations
        if isinstance(item, dict)
    ]
    return Draft(
        answerable=bool(payload.get("answerable", bool(clean))),
        answer=str(payload.get("answer", "")).strip(),
        citations=clean,
    )
