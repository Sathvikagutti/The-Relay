"""Lexical retrieval over section-aware chunks.

Why BM25 as the primary retriever: the corpus is 120 pages of three papers with
very specific vocabulary (d_k, RQ-Transformer, ratio loss, Helium). Exact terms
carry most of the signal, BM25 costs 0 model tokens and ~0 ms, and the binding
constraint is tokens-per-minute. A dense retriever is left as a future branch
(see docs/DECISIONS.md, "not built"); the re-ranking experiment in Table 3 tests
whether ordering, not representation, is our problem.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from rank_bm25 import BM25Okapi

from relay.config import PROJECT_ROOT, RelayConfig, resolve
from relay.corpus.chunk import CHARS_PER_TOKEN, ChunkingSpec, chunk_paper
from relay.corpus.extract import extract_blocks
from relay.corpus.fetch import MANIFEST_NAME
from relay.models import Chunk, ScoredChunk

TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9\-]*")
STOPWORDS = frozenset(
    """a an and are as at be been by can could do does for from had has have how
    if in into is it its may might must not of on or our over than that the their
    them then there these they this those to was we were what when where which who
    why will with would you your about above after also any because both but did
    each few more most other same some such only own too very s t don now""".split()
)
BM25_K1 = 1.5
BM25_B = 0.75
# pypdf emits "T ext" / "W atermarking" for some small-caps words. Merging a
# lone t/w/r/v with the following fragment at token level makes a query for
# "text" match a document that stores "T ext", without rewriting body text.
SPLIT_CAPS_LETTERS = frozenset({"t", "w", "r", "v"})


def tokenize(text: str) -> list[str]:
    raw = TOKEN_RE.findall(text.lower())
    tokens: list[str] = []
    index = 0
    while index < len(raw):
        token = raw[index]
        if (
            token in SPLIT_CAPS_LETTERS
            and index + 1 < len(raw)
            and len(raw[index + 1]) >= 3
            and raw[index + 1].isalpha()
        ):
            tokens.append(token + raw[index + 1])
            index += 2
            continue
        # Keep single characters: in these papers "d", "k" and "h" are model
        # dimensions and head counts, and a query about d_k fails without them.
        if token not in STOPWORDS:
            tokens.append(token)
        index += 1
    return tokens


@dataclass(frozen=True, slots=True)
class IndexMeta:
    spec_name: str
    chunk_tokens: int
    overlap_tokens: int
    n_chunks: int
    n_papers: int
    built_at: str
    chars_per_token: float
    bm25_k1: float
    bm25_b: float
    tokenizer: str

    def to_dict(self) -> dict[str, object]:
        return {
            "spec_name": self.spec_name,
            "chunk_tokens": self.chunk_tokens,
            "overlap_tokens": self.overlap_tokens,
            "n_chunks": self.n_chunks,
            "n_papers": self.n_papers,
            "built_at": self.built_at,
            "chars_per_token": self.chars_per_token,
            "bm25_k1": self.bm25_k1,
            "bm25_b": self.bm25_b,
            "tokenizer": self.tokenizer,
        }


class ChunkIndex:
    """In-memory BM25 index. Rebuilt from JSONL on load: ~500 chunks, <1 s."""

    def __init__(self, chunks: tuple[Chunk, ...]) -> None:
        if not chunks:
            raise ValueError("cannot build an index with no chunks")
        self.chunks = chunks
        # Index the section heading alongside the body, but never cite it: a
        # question that names a heading ("inner monologue") must be able to match
        # the section it names. Measured effect is recorded in docs/DECISIONS.md.
        self._bm25 = BM25Okapi(
            [tokenize(f"{chunk.section_title} {chunk.text}") for chunk in chunks],
            k1=BM25_K1,
            b=BM25_B,
        )

    def search(self, query: str, top_k: int = 6) -> list[ScoredChunk]:
        tokens = tokenize(query)
        if not tokens:
            return []
        scores = self._bm25.get_scores(tokens)
        ranked = sorted(
            (
                ScoredChunk(chunk=chunk, score=float(score))
                for chunk, score in zip(self.chunks, scores, strict=True)
                if score > 0
            ),
            key=lambda hit: (-hit.score, hit.chunk.chunk_id),
        )
        return ranked[:top_k]

    def by_paper(self, paper_key: str) -> list[Chunk]:
        return [chunk for chunk in self.chunks if chunk.paper_key == paper_key]


def index_dir(cfg: RelayConfig) -> Path:
    return resolve(cfg.corpus.index_dir)


def chunk_path(cfg: RelayConfig, spec: ChunkingSpec) -> Path:
    return index_dir(cfg) / f"chunks_{spec.name}.jsonl"


def meta_path(cfg: RelayConfig, spec: ChunkingSpec) -> Path:
    return index_dir(cfg) / f"index_{spec.name}.json"


def build_chunks(cfg: RelayConfig, spec: ChunkingSpec) -> tuple[list[Chunk], int]:
    manifest_file = index_dir(cfg) / MANIFEST_NAME
    if not manifest_file.exists():
        raise FileNotFoundError(
            f"{manifest_file} missing; run `python -m relay fetch-corpus` first"
        )
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    pages_by_key = {entry["key"]: entry for entry in manifest["papers"]}

    chunks: list[Chunk] = []
    for paper in cfg.corpus.papers:
        entry = pages_by_key.get(paper.key)
        if entry is None:
            raise KeyError(f"{paper.key} missing from the corpus manifest")
        pdf_path = resolve(Path(entry["path"]))
        blocks = extract_blocks(pdf_path, paper_key=paper.key, title=paper.title)
        chunks.extend(
            chunk_paper(
                blocks,
                paper_key=paper.key,
                title=paper.title,
                arxiv_id=paper.arxiv_id,
                version=paper.version,
                spec=spec,
            )
        )
    return chunks, len(cfg.corpus.papers)


def build_index(cfg: RelayConfig, spec: ChunkingSpec) -> tuple[ChunkIndex, IndexMeta]:
    chunks, n_papers = build_chunks(cfg, spec)
    out = chunk_path(cfg, spec)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        for chunk in chunks:
            fh.write(json.dumps(chunk.to_dict(), ensure_ascii=False) + "\n")
    meta = IndexMeta(
        spec_name=spec.name,
        chunk_tokens=spec.chunk_tokens,
        overlap_tokens=spec.overlap_tokens,
        n_chunks=len(chunks),
        n_papers=n_papers,
        built_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        chars_per_token=CHARS_PER_TOKEN,
        bm25_k1=BM25_K1,
        bm25_b=BM25_B,
        tokenizer="regex-lower-stopwords",
    )
    meta_path(cfg, spec).write_text(json.dumps(meta.to_dict(), indent=2), encoding="utf-8")
    return ChunkIndex(tuple(chunks)), meta


def load_index(cfg: RelayConfig, spec: ChunkingSpec) -> ChunkIndex:
    path = chunk_path(cfg, spec)
    if not path.exists():
        index, _ = build_index(cfg, spec)
        return index
    with path.open(encoding="utf-8") as fh:
        chunks = tuple(Chunk.from_dict(json.loads(line)) for line in fh if line.strip())
    return ChunkIndex(chunks)


def describe_hit(hit: ScoredChunk, width: int = 220) -> str:
    snippet = " ".join(hit.chunk.text.split())
    if len(snippet) > width:
        snippet = snippet[: width - 1].rstrip() + "…"
    return f"{hit.score:7.2f}  {hit.chunk.label}\n         {snippet}"


def project_root() -> Path:
    return PROJECT_ROOT
