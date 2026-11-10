"""Command line entry point.

Every experiment in this project is a subcommand, so results can be reproduced
from a command line rather than from notebook state.
"""

from __future__ import annotations

import argparse
import asyncio
import statistics
import sys
from pathlib import Path

from relay.config import load_config, load_retrieval, resolve
from relay.corpus.chunk import ChunkingSpec
from relay.corpus.fetch import MANIFEST_NAME, fetch_all, render_table
from relay.models import Chunk
from relay.retrieval.index import (
    build_index,
    chunk_path,
    describe_hit,
    index_dir,
    load_index,
)
from relay.runtime import build_runtime


def _enable_utf8_stdout() -> None:
    """Paper text contains math symbols that cp1252 cannot encode."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def cmd_fetch_corpus(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    records = fetch_all(cfg, force=args.force, check_only=args.check)
    print("The Relay - corpus")
    print(render_table(records))
    manifest_path = index_dir(cfg) / MANIFEST_NAME
    print(f"\nmanifest: {manifest_path}")
    if not all(record.verified for record in records):
        print(
            "WARNING: at least one PDF's arXiv version marker could not be read; "
            "confirm the version by eye before citing it.",
            file=sys.stderr,
        )
        return 1
    print("all three papers verified at the pinned versions")
    return 0


def _unique_specs(names: list[str] | None) -> list[tuple[str, ChunkingSpec]]:
    retrieval = load_retrieval()
    selected = names or sorted(retrieval.settings)
    seen: dict[str, tuple[str, ChunkingSpec]] = {}
    for name in selected:
        key, setting = retrieval.setting(name)
        spec = ChunkingSpec(setting.chunk_tokens, setting.overlap_tokens)
        seen.setdefault(spec.name, (key, spec))
    return list(seen.values())


def cmd_index(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    for name, spec in _unique_specs(args.settings):
        index, meta = build_index(cfg, spec)
        chunks = index.chunks
        tokens = [chunk.est_tokens for chunk in chunks]
        per_paper: dict[str, int] = {}
        for chunk in chunks:
            per_paper[chunk.paper_key] = per_paper.get(chunk.paper_key, 0) + 1
        print(f"setting {name}  {spec.name}: {meta.n_chunks} chunks")
        print(
            f"  est tokens/chunk  mean {statistics.fmean(tokens):6.1f}  "
            f"p50 {statistics.median(tokens):5.1f}  max {max(tokens):5d}"
        )
        print("  per paper: " + "  ".join(f"{k}={v}" for k, v in sorted(per_paper.items())))
        print(f"  written to {chunk_path(cfg, spec)}")
        if args.print_sections:
            seen: list[str] = []
            for chunk in chunks:
                label = f"§{chunk.section_number} {chunk.section_title}".strip()
                if not seen or seen[-1] != label:
                    seen.append(label)
            print("  detected sections:")
            for label in seen:
                print(f"    {label}")
        print()
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    retrieval = load_retrieval()
    name, setting = retrieval.setting(args.setting)
    if setting.rerank != "none" and not args.no_rerank:
        print(
            f"setting {name} uses rerank={setting.rerank}; "
            "the reranker lands in Stage 7. Re-run with --no-ranker for BM25-only order.",
            file=sys.stderr,
        )
        return 2
    spec = ChunkingSpec(setting.chunk_tokens, setting.overlap_tokens)
    index = load_index(cfg, spec)
    top_k = args.top_k or setting.top_k
    hits = index.search(args.query, top_k=top_k)
    print(f'query: "{args.query}"')
    print(f"setting {name} ({spec.name}, fetch_k={setting.fetch_k}, top_k={top_k})")
    if not hits:
        print("no passage scored above zero - this query has no lexical anchor in the corpus")
        return 1
    for rank, hit in enumerate(hits, start=1):
        print(f"\n[{rank}] {describe_hit(hit)}")
    return 0


def cmd_ask(args: argparse.Namespace) -> int:
    runtime = build_runtime(
        source=args.source,
        setting_name=args.setting,
        trace_name=args.trace or f"ask_{args.source}",
    )
    try:
        trace, answer = asyncio.run(
            runtime.relay.run(
                args.question, scenario=args.scenario, degrade=args.degrade
            )
        )
    finally:
        asyncio.run(runtime.aclose())

    print(f"status={trace.status} total={trace.total_ms:.0f}ms "
          f"ttft={'-' if trace.ttft_ms is None else f'{trace.ttft_ms:.0f}ms'} "
          f"retries={trace.retries} degrade={trace.notes.get('degrade_level', 0)} "
          f"tokens={trace.tokens_in}/{trace.tokens_out}")
    print()
    print(answer.text.strip())
    if answer.citations:
        print("\ncitations:")
        for citation in answer.citations:
            quote = " ".join(citation.quote.split())
            print(f"  - {citation.label}: \"{quote[:110]}\"")
    elif answer.reason:
        print(f"\n(refused: {answer.reason})")
    print(f"\ntrace: {runtime.trace_path}")
    return 0 if trace.status == "ok" else 1


def cmd_eval(args: argparse.Namespace) -> int:
    from relay.experiments.run_eval import run_eval
    from relay.obs.csvio import write_results
    from relay.obs.events import percentile

    all_rows: list[dict[str, object]] = []
    for setting in args.settings:
        result = asyncio.run(
            run_eval(setting=setting, source=args.source, limit_profile=args.limits)
        )
        all_rows.extend(result.rows)
        path = (
            resolve(Path("results/eval"))
            / f"rows_{setting}_{args.source}.csv"
        )
        write_results(result.rows, path)
        grades: dict[str, int] = {}
        for row in result.rows:
            grades[str(row["answer_grade"])] = grades.get(str(row["answer_grade"]), 0) + 1
        ttft = [float(r["first_token_ms"]) for r in result.rows if r["first_token_ms"] != ""]
        total = [float(r["total_ms"]) for r in result.rows]
        tokens_out = [int(r["tokens_out"]) for r in result.rows]
        print(
            f"setting {setting} ({args.source}): {len(result.rows)} questions  "
            f"grades={grades}  ttft_p50={(percentile(ttft, 50) or 0.0):.0f}ms  "
            f"total_p50={percentile(total, 50):.0f}ms  "
            f"tokens_out/answer={statistics.fmean(tokens_out):.0f}"
        )
        print(f"  rows -> {path}")
    return 0


def cmd_calibrate(args: argparse.Namespace) -> int:
    from relay.experiments.calibrate import main

    return main()


def cmd_probe_limits(args: argparse.Namespace) -> int:
    from relay.experiments import probe_limits

    return asyncio.run(probe_limits.main())


def cmd_load(args: argparse.Namespace) -> int:
    from relay.experiments.load import LOAD_DIR, append_summary, run_all

    results = asyncio.run(run_all(args.scenarios, source=args.source))
    append_summary(results, LOAD_DIR / "summary.csv")
    print(f"rows written under {LOAD_DIR}")
    return 0


def cmd_review(args: argparse.Namespace) -> int:
    from relay.experiments.review import build

    rows, _lines = build(source=args.source, settings=tuple(args.settings))
    print(f"{rows} grading rows -> eval/manual_grades.csv and eval/review_sheet.md")
    return 0 if rows else 1


def cmd_combine(args: argparse.Namespace) -> int:
    from relay.obs.csvio import write_results
    from relay.obs.metrics import read_rows

    paths = sorted(resolve(Path("results/load")).glob("*.csv"))
    paths = [p for p in paths if p.name != "summary.csv"]
    paths += sorted(resolve(Path("results/eval")).glob("rows_*.csv"))
    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for path in paths:
        for row in read_rows(path):
            if row["request_id"] in seen:
                continue
            seen.add(row["request_id"])
            rows.append(row)
    rows.sort(key=lambda row: (row["start_time"], row["request_id"]))
    target = resolve(Path("results/results.csv"))
    write_results(rows, target)  # type: ignore[arg-type]
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["scenario"]] = counts.get(row["scenario"], 0) + 1
    print(f"{len(rows)} rows -> {target}")
    print(f"by scenario: {counts}")
    return 0


def cmd_tables(args: argparse.Namespace) -> int:
    from relay.obs.metrics import CSV_PATH, all_tables

    text = all_tables(CSV_PATH)
    print(text)
    if args.write:
        target = resolve(Path("report/TABLES.md"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text + "\n", encoding="utf-8")
        print(f"\nwritten: {target}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="relay", description="The Relay pipeline")
    sub = parser.add_subparsers(dest="command", required=True)

    fetch = sub.add_parser(
        "fetch-corpus", help="download the pinned papers and verify versions"
    )
    fetch.add_argument("--force", action="store_true", help="re-download existing files")
    fetch.add_argument(
        "--check", action="store_true", help="verify local files only, no network"
    )
    fetch.add_argument("--config", default=None, help="path to a config YAML")
    fetch.set_defaults(func=cmd_fetch_corpus)

    idx = sub.add_parser("index", help="extract, chunk and build BM25 indexes")
    idx.add_argument(
        "--settings", nargs="*", default=None, help="retrieval settings (default: all)"
    )
    idx.add_argument("--print-sections", action="store_true", help="audit section map")
    idx.add_argument("--config", default=None)
    idx.set_defaults(func=cmd_index)

    search = sub.add_parser("search", help="query the index and show ranked passages")
    search.add_argument("query")
    search.add_argument("--setting", default=None)
    search.add_argument("--top-k", type=int, default=None)
    search.add_argument("--no-ranker", action="store_true", help="ignore rerank config")
    search.add_argument("--config", default=None)
    search.set_defaults(func=cmd_search)

    ask = sub.add_parser("ask", help="run the full pipeline for one question")
    ask.add_argument("question")
    ask.add_argument("--source", choices=["stand-in", "real"], default="stand-in")
    ask.add_argument("--setting", default=None, help="retrieval setting A/B/C")
    ask.add_argument("--scenario", default="adhoc", help="scenario label for results.csv")
    ask.add_argument("--degrade", type=int, default=None, help="force degradation level")
    ask.add_argument("--trace", default=None, help="trace file stem under results/raw")
    ask.set_defaults(func=cmd_ask)

    ev = sub.add_parser("eval", help="run the 20-question evaluation set")
    ev.add_argument("--settings", nargs="*", default=["A"])
    ev.add_argument("--source", choices=["stand-in", "real"], default="stand-in")
    ev.add_argument("--limits", choices=["relaxed", "documented"], default="relaxed")
    ev.set_defaults(func=cmd_eval)

    pl = sub.add_parser("probe-limits", help="measure real service limits (~45 requests)")
    pl.set_defaults(func=cmd_probe_limits)

    cal = sub.add_parser("calibrate", help="fit stand-in params from real measurements")
    cal.set_defaults(func=cmd_calibrate)

    ld = sub.add_parser("load", help="run load scenarios")
    ld.add_argument(
        "--scenarios",
        nargs="*",
        default=[
            "steady",
            "burst",
            "overload",
            "sustained",
            "faulty",
            "degraded",
            "limit_halved",
            "daily_exhausted",
        ],
    )
    ld.add_argument("--source", choices=["stand-in", "real"], default="stand-in")
    ld.set_defaults(func=cmd_load)

    cb = sub.add_parser("combine", help="merge row files into results/results.csv")
    cb.set_defaults(func=cmd_combine)

    rs = sub.add_parser("review-sheet", help="build eval/manual_grades.csv + review_sheet.md")
    rs.add_argument("--source", choices=["stand-in", "real"], default="stand-in")
    rs.add_argument("--settings", nargs="*", default=["A", "B", "C"])
    rs.set_defaults(func=cmd_review)

    tb = sub.add_parser("tables", help="regenerate report tables from results.csv")
    tb.add_argument("--write", action="store_true", help="write report/TABLES.md")
    tb.set_defaults(func=cmd_tables)
    return parser


def main(argv: list[str] | None = None) -> int:
    _enable_utf8_stdout()
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
