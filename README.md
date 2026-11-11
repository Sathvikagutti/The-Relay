# The Relay

A small, honest RAG assistant over three pinned arXiv papers, built to be measured:

* **Attention Is All You Need** (1706.03762v7)
* **Moshi: a speech-text foundation model for real-time dialogue** (2410.00037v1)
* **Dynamic Chunking for End-to-End Hierarchical Sequence Modeling** (2507.07955v2)

Every answer cites a paper, a page and a section, and the quote is verified against the
chunk before the answer is revealed. If the papers do not answer the question, the system
says so instead of guessing. The load tests are run against a stand-in service whose
latency is calibrated from real measurements of Groq's free tier, because crossing a
free-tier limit thousands of times is not possible in a four-day exercise.

## Quickstart

```bash
python -m venv .venv
.venv/Scripts/activate            # Windows; source .venv/bin/activate elsewhere
pip install -r requirements.txt
cp .env.example .env              # then put your GROQ_API_KEY in .env

relay fetch-corpus --check        # downloads and verifies the three pinned PDFs
relay index                       # extracts, chunks (350/60) and builds the BM25 index
relay ask "How does Moshi handle streaming speech?"
```

`relay ask` works against the stand-in service with no key at all:

```bash
python -m uvicorn services.standin.app:app --host 127.0.0.1 --port 8788 &
relay ask "How does the decoder attend to the encoder output?" --source stand-in
```

## Commands

| Command | What it does |
| --- | --- |
| `relay fetch-corpus --check` | Fetch the pinned PDFs and verify sha256 + page counts against `manifest.json` |
| `relay index` | Extract text, repair pypdf artefacts, chunk by section, build the BM25 index |
| `relay ask "..."` | One question through the full pipeline; prints answer, citations and timings |
| `relay probe-limits` | ~45 real requests to measure RPM/TPM, 429 shape, recovery and TTFT |
| `relay calibrate` | Fit the stand-in's latency parameters from those measurements |
| `relay eval --settings A B C` | Run the 20-question set; writes graded rows per setting |
| `relay load` | Eight load scenarios: steady, burst, overload, sustained (4 min), faulty, degraded, limit halved, daily exhausted |
| `relay combine` | Merge every row file into `results/results.csv` |
| `relay review-sheet` | Write `eval/manual_grades.csv` (60 rows, blank judgement columns) and `eval/review_sheet.md` |
| `relay tables` | Regenerate the report tables from that CSV |

## The pipeline

```
question
  -> analyze   (cheap call: answerable? which passages?)
  -> retrieve  (BM25 over heading + body, k=4)
  -> draft     (writes only from the selected passages, returns JSON citations)
  -> verify    (tool call: quote must appear verbatim in the cited chunk)
  -> repair    (at most twice, then refuse)
  -> answer    (paper, page, section, verified quote)
```

Failure handling is part of the design, not an afterthought: a token-budget admission
queue, a deadline-aware limiter, full-jitter retries that honour `retry-after`, and a
circuit breaker that ignores 429s because a busy provider is not a broken one.

## Layout

```
src/relay/
  corpus/       fetch, extract (pypdf repair), chunk (section-bounded, overlapping)
  retrieval/    BM25 index, context selection
  pipeline/     steps, tools (verify_quote), engine (queue, limiter, retries, breaker)
  llm/          provider interface + Groq streaming (TTFT, 429 classification)
  scheduling/   rolling limiter, retry policy, circuit breaker, admission queue
  obs/          trace events, CSV writer/reader, table generation
  experiments/  probe, calibrate, eval, load
services/standin/  OpenAI-compatible SSE server with the documented free-tier counters
eval/              20 questions in 5 buckets, gold regions, manual grade sheet
results/           results.csv, raw traces, per-scenario rows, load summary
                   (limits.json appears only after `relay probe-limits` runs)
report/            2-page report and its tables
docs/              plan, decisions, grading, checklist, audit, analysis, interview notes,
                   conversation record
```

## Results

Everything numeric lives in `results/results.csv` (one row per request, exact columns
required by the brief) and `report/TABLES.md` (regenerated with `relay tables`, never
typed by hand). `results/limits.json` is written by `relay probe-limits`, which needs
`GROQ_API_KEY`; it has been run, so Table 1 reports measured values where the probe could
establish them and says `not measured` for tokens/day and in-flight, which it could not.

## What this does not do

No vector database, no UI, no fine-tuning, no LLM-as-judge, no multi-provider failover.
Those are deliberate omissions, argued in `docs/DECISIONS.md`; the corpus is 349 chunks,
where BM25 is a reasonable choice and an embedding index would add a build step and a new
failure mode.

## Known limitations

* Multi-paper synthesis (bucket C) is the weakest area: retrieval can return passages from
  one paper only, and nothing forces a cross-paper answer to cite more than one paper.
* Automatic grading checks citation location, not answer correctness. Table 3 therefore
  uses reviewed grades where they exist and says so when they do not.
* The stand-in cannot reproduce cold starts or prefill scaling; the differences are listed
  in its calibration metadata, `services/standin/params.json`, which `relay calibrate`
  writes. That file is committed and the stand-in reports `calibrated: true`.
