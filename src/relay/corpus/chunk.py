"""Configurable chunking.

Chunk size is expressed in *estimated tokens* because the binding provider limit
is tokens-per-minute. The estimator is a characters/4 heuristic until Stage 2
calibrates it against Groq's reported `prompt_tokens`; that calibration factor is
stored in the index metadata so a chunk "350 tokens" claim is auditable.

Chunks never cross a paper or a section boundary: a citation that spans two
sections cannot be honestly labelled with one section.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from relay.corpus.extract import TextBlock
from relay.models import Chunk

CHARS_PER_TOKEN = 4.0  # calibrated in Stage 2 against real usage numbers
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def estimate_tokens(text: str) -> int:
    return max(1, round(len(text) / CHARS_PER_TOKEN))


@dataclass(frozen=True, slots=True)
class ChunkingSpec:
    chunk_tokens: int = 350
    overlap_tokens: int = 60

    def __post_init__(self) -> None:
        if self.chunk_tokens < 50:
            raise ValueError("chunk_tokens too small to hold a useful passage")
        if not 0 <= self.overlap_tokens < self.chunk_tokens:
            raise ValueError("overlap_tokens must be >= 0 and < chunk_tokens")

    @property
    def name(self) -> str:
        return f"t{self.chunk_tokens}_o{self.overlap_tokens}"


def _pack_section(
    lines: list[tuple[int, str]], spec: ChunkingSpec
) -> list[tuple[int, int, str]]:
    """Greedy line packing with a trailing overlap carried into the next chunk."""
    packed: list[tuple[int, int, str]] = []
    current: list[tuple[int, str]] = []

    def tokens_of(items: list[tuple[int, str]]) -> int:
        return estimate_tokens(" ".join(text for _, text in items))

    def emit() -> None:
        if not current:
            return
        text = " ".join(line for _, line in current)
        packed.append((current[0][0], current[-1][0], text))

    for item in lines:
        if current and tokens_of(current + [item]) > spec.chunk_tokens:
            emit()
            # Carry the tail of the finished chunk so a fact split across the
            # boundary is still retrievable from one piece.
            tail: list[tuple[int, str]] = []
            while current and tokens_of(tail + [current[-1]]) <= spec.overlap_tokens:
                tail.insert(0, current[-1])
                current.pop()
            current = tail
            if current and tokens_of(current + [item]) > spec.chunk_tokens:
                current = []
        current.append(item)
    emit()
    return packed


def chunk_paper(
    blocks: list[TextBlock],
    *,
    paper_key: str,
    title: str,
    arxiv_id: str,
    version: int,
    spec: ChunkingSpec,
) -> list[Chunk]:
    sections: dict[tuple[str, str], list[tuple[int, str]]] = {}
    order: list[tuple[str, str]] = []
    for block in blocks:
        key = (block.section_number, block.section_title)
        if key not in sections:
            sections[key] = []
            order.append(key)
        sections[key].extend((block.page, line) for line in block.lines)

    chunks: list[Chunk] = []
    seq = 0
    for section_number, section_title in order:
        for page_start, page_end, text in _pack_section(sections[(section_number, section_title)], spec):
            seq += 1
            chunks.append(
                Chunk(
                    chunk_id=f"{paper_key}:{seq:04d}",
                    paper_key=paper_key,
                    title=title,
                    arxiv_id=arxiv_id,
                    version=version,
                    section_number=section_number,
                    section_title=section_title,
                    page_start=page_start,
                    page_end=page_end,
                    text=text,
                    est_tokens=estimate_tokens(text),
                    seq=seq,
                )
            )
    return chunks
