"""Fetch the three pinned papers and record provenance we can audit later.

Why this is its own step: the assignment grades citations against *exact*
arXiv versions. If we silently read v6 of "Attention Is All You Need" (or the
NeurIPS camera-ready), page numbers and some results differ, and every citation
in the report becomes contestable. So the version marker printed in the PDF
margin is checked against the pin, and the sha256 is stored.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import httpx
from pypdf import PdfReader

from relay.config import PaperSpec, RelayConfig, resolve

MANIFEST_NAME = "manifest.json"
USER_AGENT = "the-relay-assignment/0.1 (corpus fetch; educational use)"
# arXiv stamps "arXiv:1706.03762v7 [cs.CL]" in the left margin of page 1.
ARXIV_MARKER_RE = re.compile(
    r"arXiv:\s*(?P<arxiv_id>\d{4}\.\d{4,5})v(?P<version>\d+)", re.IGNORECASE
)


class CorpusError(RuntimeError):
    """A downloaded file cannot be trusted to be the pinned paper version."""


@dataclass(frozen=True)
class PaperRecord:
    key: str
    arxiv_id: str
    version: int
    title: str
    url: str
    path: str
    sha256: str
    size_bytes: int
    pages: int
    page_one_marker: str | None
    verified: bool
    fetched_at: str

    @property
    def size_mb(self) -> float:
        return self.size_bytes / (1024 * 1024)


def parse_version_marker(text: str) -> tuple[str, int] | None:
    """Extract (arxiv_id, version) from page-one text, tolerant of spacing."""
    normalized = " ".join(text.split())
    match = ARXIV_MARKER_RE.search(normalized)
    if not match:
        return None
    return match.group("arxiv_id"), int(match.group("version"))


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def download(spec: PaperSpec, dest: Path, client: httpx.Client, *, force: bool) -> None:
    if dest.exists() and not force:
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    partial = dest.with_suffix(".pdf.part")
    with client.stream("GET", spec.url) as response:
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if "pdf" not in content_type.lower():
            raise CorpusError(f"{spec.url} returned {content_type!r}, expected a PDF")
        with partial.open("wb") as fh:
            for block in response.iter_bytes(1 << 16):
                fh.write(block)
    with partial.open("rb") as fh:
        if not fh.read(5).startswith(b"%PDF"):
            partial.unlink(missing_ok=True)
            raise CorpusError(f"{spec.url} did not return a PDF body")
    partial.replace(dest)


def inspect(spec: PaperSpec, path: Path, *, fetched_at: str) -> PaperRecord:
    if not path.exists():
        raise CorpusError(f"missing {path}; run `python -m relay fetch-corpus`")
    reader = PdfReader(str(path))
    first_page = reader.pages[0].extract_text() or ""
    marker = parse_version_marker(first_page)
    verified = marker == (spec.arxiv_id, spec.version)
    if marker is not None and not verified:
        raise CorpusError(
            f"{path.name} is arXiv:{marker[0]}v{marker[1]}, "
            f"but the assignment requires v{spec.version}"
        )
    return PaperRecord(
        key=spec.key,
        arxiv_id=spec.arxiv_id,
        version=spec.version,
        title=spec.title,
        url=spec.url,
        path=str(path),
        sha256=sha256_of(path),
        size_bytes=path.stat().st_size,
        pages=len(reader.pages),
        page_one_marker=None if marker is None else f"arXiv:{marker[0]}v{marker[1]}",
        verified=verified,
        fetched_at=fetched_at,
    )


def fetch_all(
    cfg: RelayConfig, *, force: bool = False, check_only: bool = False
) -> list[PaperRecord]:
    corpus_dir = resolve(cfg.corpus.dir)
    index_dir = resolve(cfg.corpus.index_dir)
    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    records: list[PaperRecord] = []

    client = httpx.Client(
        timeout=httpx.Timeout(90.0, connect=20.0),
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
    )
    try:
        for spec in cfg.corpus.papers:
            dest = corpus_dir / spec.filename
            if not check_only:
                download(spec, dest, client, force=force)
            records.append(inspect(spec, dest, fetched_at=fetched_at))
    finally:
        client.close()

    index_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "generated_at": fetched_at,
        "source": "https://arxiv.org",
        "papers": [asdict(record) for record in records],
    }
    (index_dir / MANIFEST_NAME).write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return records


def render_table(records: list[PaperRecord]) -> str:
    header = (
        f"{'key':<18}{'arxiv id':<13}{'ver':<4}{'pages':<7}"
        f"{'size':>9} {'version check':<14}{'sha256':<12}"
    )
    lines = [header, "-" * len(header)]
    for record in records:
        check = f"v{record.version} ok" if record.verified else "unverified"
        lines.append(
            f"{record.key:<18}{record.arxiv_id:<13}{record.version:<4}"
            f"{record.pages:<7}{record.size_mb:>5.1f} MB "
            f"{check:<14}{record.sha256[:12]}"
        )
    return "\n".join(lines)
