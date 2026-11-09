"""Tool call: verify_quote.

This is the anti-hallucination gate, and it is deliberately *not* another model
call. A quote is accepted only if its alphanumeric-normalised form is a substring
of the cited passage. That makes "the model made up a quotation" mechanically
detectable, cheap (no tokens), and auditable after the fact.

Page and section are taken from our chunk metadata rather than from the model, so
a citation can point at a real passage but can never invent a page number.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from relay.models import Chunk, Citation

TOOL_NAME = "verify_quote"
MIN_QUOTE_CHARS = 24  # short quotes match almost anything; refuse to "verify" them
NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def normalize_for_match(text: str) -> str:
    return NON_ALNUM_RE.sub("", text.lower())


@dataclass(frozen=True, slots=True)
class QuoteCheck:
    chunk_id: str
    ok: bool
    reason: str


def verify_quote(quote: str, passage: str) -> tuple[bool, str]:
    normalized_quote = normalize_for_match(quote)
    if len(normalized_quote) < MIN_QUOTE_CHARS:
        return False, f"quote shorter than {MIN_QUOTE_CHARS} characters"
    if normalized_quote not in normalize_for_match(passage):
        return False, "quote does not appear verbatim in the cited passage"
    return True, "verified"


def verify_citations(
    raw: list[dict[str, str]], chunks_by_id: dict[str, Chunk]
) -> tuple[list[Citation], list[str]]:
    """Build verified citations; return (citations, errors)."""
    citations: list[Citation] = []
    errors: list[str] = []
    seen: set[tuple[str, str]] = set()

    for index, item in enumerate(raw, start=1):
        chunk_id = str(item.get("chunk_id", "")).strip()
        quote = str(item.get("quote", "")).strip()
        chunk = chunks_by_id.get(chunk_id)
        if chunk is None:
            errors.append(f"citation {index}: chunk_id {chunk_id!r} is not one of the passages")
            continue
        if not quote:
            errors.append(f"citation {index}: missing quote")
            continue
        key = (chunk_id, normalize_for_match(quote))
        if key in seen:
            continue
        seen.add(key)
        ok, reason = verify_quote(quote, chunk.text)
        if not ok:
            errors.append(f"citation {index} ({chunk_id}): {reason}")
            continue
        citations.append(
            Citation(
                chunk_id=chunk_id,
                paper_key=chunk.paper_key,
                page=chunk.page_start,
                section=chunk.section,
                quote=quote,
                verified=True,
            )
        )
    return citations, errors


def render_passages(chunks: list[Chunk]) -> str:
    blocks = []
    for chunk in chunks:
        blocks.append(
            f"[{chunk.chunk_id}] ({chunk.paper_key}, p.{chunk.page_start}, "
            f"section {chunk.section})\n{chunk.text}"
        )
    return "\n\n".join(blocks)
