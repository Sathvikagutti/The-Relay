"""Page- and section-preserving text extraction.

The citation contract is "paper, page, section", so section boundaries are part
of the data model rather than something a later step guesses at. pypdf gives us
(page number, text); a heading detector turns that into (page, section) blocks.

Heading detection is deliberately conservative: a false heading corrupts every
chunk label below it, whereas a missed sub-sub-heading only makes one chunk's
section label coarser. We validate precision by printing the detected map.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

# "3.2.1 Scaled Dot-Product Attention", "A.1 Static Chunking", "5 Training"
HEADING_RE = re.compile(
    r"^(?P<number>\d{1,2}(?:\.\d{1,2}){0,2}|[A-Z](?:\.\d{1,2}){0,2})\.?\s+"
    r"(?P<title>[A-Z][^=$\n]{1,80})$"
)
# A heading's title normally contains a capitalised word ("Static", "Training").
TITLE_WORD_RE = re.compile(r"[A-Z][a-z]{2,}")
# pypdf splits some small-caps words into "T ext" / "W atermarking". Repairing
# this only in short heading lines is low-risk; the same artifact in body text is
# handled in the tokenizer instead (see retrieval/index.py).
SPLIT_CAPS_RE = re.compile(r"\b([TWVR]) (?=[a-z]{2,}\b)([a-z]+)")
UNNUMBERED_HEADINGS = {"abstract", "references", "appendix", "acknowledgments", "acknowledgements"}
RUNNING_TEXT_PREFIXES = ("arxiv:", "provided proper attribution")


@dataclass(frozen=True, slots=True)
class TextBlock:
    """Contiguous text from one page inside one section."""

    section_number: str
    section_title: str
    page: int
    lines: tuple[str, ...]

    @property
    def text(self) -> str:
        return "\n".join(self.lines)


def normalize_line(line: str) -> str:
    return " ".join(line.split())


def repair_split_caps(text: str) -> str:
    """Rejoin small-caps words that pypdf split after the first letter."""
    return SPLIT_CAPS_RE.sub(r"\1\2", text)


def is_heading(line: str, paper_title: str) -> tuple[str, str] | None:
    """Return (section_number, section_title) if the line is a heading."""
    text = repair_split_caps(normalize_line(line))
    if not text or len(text) > 85:
        return None
    if text.casefold() == normalize_line(paper_title).casefold():
        return None
    if text.casefold() in UNNUMBERED_HEADINGS:
        return "", text.rstrip(":")

    match = HEADING_RE.match(text)
    if not match:
        return None
    title = match.group("title").strip()
    if title.endswith((".", "?", ";", ",")):
        return None
    words = title.split()
    if len(words) > 9:
        return None
    if not TITLE_WORD_RE.search(title):
        return None
    return match.group("number"), title


def _is_page_furniture(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    if stripped.isdigit():
        return True
    return stripped.casefold().startswith(RUNNING_TEXT_PREFIXES)


def extract_blocks(pdf_path: Path, *, paper_key: str, title: str) -> list[TextBlock]:
    """Split a paper into per-page blocks tagged with the section they belong to."""
    reader = PdfReader(str(pdf_path))
    blocks: list[TextBlock] = []
    section_number = ""
    section_title = "Front matter"
    buffer: list[str] = []
    buffer_page = 0

    def flush(page: int) -> None:
        if buffer:
            blocks.append(
                TextBlock(
                    section_number=section_number,
                    section_title=section_title,
                    page=page,
                    lines=tuple(buffer),
                )
            )
            buffer.clear()

    for page_index, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        for raw_line in page_text.splitlines():
            line = normalize_line(raw_line)
            if _is_page_furniture(line):
                continue
            heading = is_heading(line, title)
            if heading is not None:
                flush(buffer_page or page_index)
                section_number, section_title = heading
                buffer_page = page_index
                continue
            if buffer and buffer_page != page_index:
                flush(buffer_page)
            buffer_page = page_index
            buffer.append(line)
        flush(buffer_page)
        buffer_page = 0

    return [block for block in blocks if block.lines]


def section_map(blocks: list[TextBlock]) -> list[str]:
    """Human-readable audit of the detected sections (used by the index CLI)."""
    seen: list[str] = []
    for block in blocks:
        label = f"p.{block.page:<3} §{block.section_number} {block.section_title}".rstrip()
        if not seen or seen[-1].split("§", 1)[1] != label.split("§", 1)[1]:
            seen.append(label)
    return seen
