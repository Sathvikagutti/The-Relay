"""Shared data types.

`Chunk` is the unit of retrieval and the unit of citation. Every field needed to
reproduce a citation without opening the PDF is carried on the chunk itself.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Chunk:
    chunk_id: str
    paper_key: str
    title: str
    arxiv_id: str
    version: int
    section_number: str
    section_title: str
    page_start: int
    page_end: int
    text: str
    est_tokens: int
    seq: int

    @property
    def section(self) -> str:
        return f"{self.section_number} {self.section_title}".strip()

    @property
    def label(self) -> str:
        pages = (
            f"p.{self.page_start}"
            if self.page_start == self.page_end
            else f"pp.{self.page_start}-{self.page_end}"
        )
        return f"{self.paper_key} {pages} §{self.section}"

    def to_dict(self) -> dict[str, object]:
        return {
            "chunk_id": self.chunk_id,
            "paper_key": self.paper_key,
            "title": self.title,
            "arxiv_id": self.arxiv_id,
            "version": self.version,
            "section_number": self.section_number,
            "section_title": self.section_title,
            "page_start": self.page_start,
            "page_end": self.page_end,
            "text": self.text,
            "est_tokens": self.est_tokens,
            "seq": self.seq,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> Chunk:
        return cls(
            chunk_id=str(raw["chunk_id"]),
            paper_key=str(raw["paper_key"]),
            title=str(raw["title"]),
            arxiv_id=str(raw["arxiv_id"]),
            version=int(raw["version"]),
            section_number=str(raw["section_number"]),
            section_title=str(raw["section_title"]),
            page_start=int(raw["page_start"]),
            page_end=int(raw["page_end"]),
            text=str(raw["text"]),
            est_tokens=int(raw["est_tokens"]),
            seq=int(raw["seq"]),
        )


@dataclass(frozen=True, slots=True)
class Citation:
    """A citation we constructed ourselves: paper/page/section come from chunk
    metadata, never from the model. Only the quote is the model's claim, and the
    quote is checked against the source text before the answer is revealed."""

    chunk_id: str
    paper_key: str
    page: int
    section: str
    quote: str
    verified: bool = False

    @property
    def label(self) -> str:
        return f"{self.paper_key} p.{self.page} §{self.section}"

    def to_dict(self) -> dict[str, object]:
        return {
            "chunk_id": self.chunk_id,
            "paper_key": self.paper_key,
            "page": self.page,
            "section": self.section,
            "quote": self.quote,
            "verified": self.verified,
        }


@dataclass(frozen=True, slots=True)
class Answer:
    status: str  # ok | refused
    text: str
    citations: tuple[Citation, ...] = ()
    reason: str = ""

    @property
    def refused(self) -> bool:
        return self.status == "refused"


@dataclass(frozen=True, slots=True)
class ScoredChunk:
    chunk: Chunk
    score: float

    def __str__(self) -> str:
        return f"{self.score:7.2f}  {self.chunk.label}"
