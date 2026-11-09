"""Context selection: precision per token.

The free tier gives 8k tokens/minute, so a prompt that stuffs ten passages buys
recall with minutes of the user's time. Selection therefore merges results from
several sub-queries, keeps the best distinct passages, and stops at a token
budget rather than at a fixed count.
"""

from __future__ import annotations

from relay.models import Chunk, ScoredChunk


def merge_hits(hit_lists: list[list[ScoredChunk]]) -> list[ScoredChunk]:
    """Merge ranked lists, keeping each chunk's best score across sub-queries."""
    best: dict[str, ScoredChunk] = {}
    for hits in hit_lists:
        for hit in hits:
            current = best.get(hit.chunk.chunk_id)
            if current is None or hit.score > current.score:
                best[hit.chunk.chunk_id] = hit
    return sorted(best.values(), key=lambda hit: (-hit.score, hit.chunk.chunk_id))


def dedupe_by_section(hits: list[ScoredChunk], *, limit_per_section: int = 1) -> list[ScoredChunk]:
    """Cap how many pieces one section contributes.

    Without this, a long section with one repeated term fills the whole budget
    and the answer misses the second paper that also discussed the topic.
    """
    counts: dict[tuple[str, str], int] = {}
    kept: list[ScoredChunk] = []
    for hit in hits:
        key = (hit.chunk.paper_key, hit.chunk.section_number)
        if counts.get(key, 0) >= limit_per_section:
            continue
        counts[key] = counts.get(key, 0) + 1
        kept.append(hit)
    return kept


def select_context(
    hits: list[ScoredChunk],
    *,
    token_budget: int,
    top_k: int,
    limit_per_section: int = 1,
) -> list[Chunk]:
    selected: list[Chunk] = []
    spent = 0
    for hit in dedupe_by_section(hits, limit_per_section=limit_per_section):
        if len(selected) >= top_k:
            break
        if selected and spent + hit.chunk.est_tokens > token_budget:
            continue
        selected.append(hit.chunk)
        spent += hit.chunk.est_tokens
    return selected
