# The Relay — Design & Implementation Plan

## 1. The constraint that shapes everything

Groq's free plan publishes (docs, read 2026-11): **30 RPM, 1,000 RPD, 8,000 TPM, 200,000 TPD** for
`openai/gpt-oss-120b`-class models. These are *documented*, not yet *observed* on our account.

At ~2,600 tokens per answer, **8,000 TPM is about 3 answers per minute**, and 200,000 TPD is about
75 answers per day. So for this workload **tokens-per-minute is the binding limit, not requests**.
That single fact produces the whole architecture:

> The pipeline knows the token cost of each model call *before* it sends it, and admission control
> budgets tokens, not requests. Everything else — a two-call pipeline, validating citations before
> revealing text, fail-fast on a token-window 429, and a degradation ladder — follows from it.

Secondary consequence: retrieval must be *small and precise*. Context budget target ≈ 1.4k tokens
(4 chunks), not "stuff the top 10". This is why retrieval quality per token is a first-class metric.

## 2. Architecture

```
CLI / HTTP request
  │
  ├─ RequestGate ........... validate, assign request_id + deadline + cancel token
  │
  ├─ AdmissionController ... rolling-window budgets (RPM, TPM, RPD, TPD, in-flight)
  │      ├─ admit ─────────► pipeline
  │      ├─ queue (bounded, deadline-aware, FCFS + priority for eval runs)
  │      └─ reject ────────► 429 + retry_after_ms, or degraded mode
  │
  ├─ 1 analyze_query ....... branch: trivial → heuristic; ambiguous → 1 LLM JSON call
  │                          → {answerable, sub_queries[], needs_multi_passage}
  ├─ 2 retrieve ............ BM25 over section-aware chunks (top-N configurable)
  ├─ 3 select_context ...... optional cross-encoder rerank → dedupe by section →
  │                          neighbour expansion → token budget → 4 chunks
  ├─ 4 draft_answer ........ 1 streaming LLM call → JSON {answer, citations[{paper,page,section,quote}]}
  ├─ 5 verify_quote [TOOL] . normalized substring match of each quote against the cited page
  │      └─ loop ≤2 repairs on failure, then refuse  ← the branch/loop
  ├─ 6 compose_reply ....... buffered reveal: citation footer, or refusal, or degraded notice
  │
  └─ Observability ......... span JSONL per request (queued/admitted/call/first_token/end/retry)
                             → results.csv → tables → report
```

Step count: 6 (≥4 required). Tool: `verify_quote` (≥1). Loop: citation repair (≥1).
Branch: analysis routing + degrade ladder.

### Component purposes

| Component | Why it exists |
|---|---|
| `RequestGate` | one place for deadline/cancellation so nothing runs past the user's patience |
| `AdmissionController` | the only writer of provider quota; keeps us under TPM/RPD before spending |
| `analyze_query` | cheap routing; decides whether we can answer at all, and how many chunks we need |
| `retrieve` | recall: get candidate passages with page+section metadata |
| `select_context` | precision per token: our scarcest resource is prompt tokens |
| `draft_answer` | grounded generation with machine-checkable citations |
| `verify_quote` | objective (non-LLM) check that the cited text exists — the anti-hallucination gate |
| `compose_reply` | decides what the human actually sees, including refusals and degraded answers |
| `standin` | lets us run 10⁴-request experiments the free tier cannot absorb |
| `obs` | every table number must be derivable from raw rows |

## 3. Folder structure

```
the-relay/
├─ README.md  requirements.txt  .env.example  .gitignore
├─ config/        default.yaml  retrieval.yaml  scenarios.yaml
├─ data/papers/   1706.03762v7.pdf  2410.00037v1.pdf  2507.07955v2.pdf
│  data/index/    chunks.jsonl  bm25.pkl  manifest.json
├─ src/relay/
│  ├─ config.py  models.py  cli.py
│  ├─ corpus/     fetch.py  extract.py  chunk.py
│  ├─ retrieval/  index.py  rerank.py  select.py
│  ├─ llm/        base.py  groq.py  transport.py  tokens.py
│  ├─ pipeline/   steps.py  tools.py  orchestrate.py  degrade.py
│  ├─ scheduling/ limiter.py  queue.py  retry.py  breaker.py
│  └─ obs/        events.py  metrics.py  csvio.py
├─ services/standin/  app.py  sim.py  calibrate.py
├─ experiments/       probe_limits.py  load.py  retry_exp.py  breakdown.py  eval.py
├─ eval/              questions.yaml  manual_grades.csv
├─ results/           raw/*.jsonl  results.csv  limits.json
├─ report/            report.md  report.html  tables/
├─ docs/              CHECKLIST.md  PLAN.md  DECISIONS.md  GRADING.md
│                     conversation-log.md  INTERVIEW.md  SUBMISSION.md
└─ tests/
```

## 4. Decisions and the measurement that decides each

| # | Decision | Alternative | Cost of being wrong | Settled by |
|---|---|---|---|---|
| D1 | Token-budget admission control, not retry-on-429 | retry hard | burn RPD, worse p95, fewer answers | retry experiment (H3) |
| D2 | Two model calls per answer (analyze + draft) | three (separate citation pass) | ~35% more tokens ⇒ ~1 fewer answer/min | setting A/B/C token counts |
| D3 | Validate citations **before** revealing the answer | stream the draft live | user waits ~+300 ms after last token | §4 latency split; quality gate |
| D4 | Buffer only the body, stream status events | no streaming at all | perceived latency | TTFT numbers |
| D5 | BM25 + local cross-encoder rerank | dense embeddings / LLM rerank | rerank costs ~100 ms CPU, saves ~700 prompt tokens | Table 3 |
| D6 | Fail fast on TPM 429, never retry RPD/TPD 429 | uniform backoff | a TPM retry re-enters the same 60 s window | §5 behaviour |
| D7 | Bounded queue (depth 32) + reject with retry-after | unbounded queue | timeouts pile up; p99 explodes | burst scenario |
| D8 | Refuse rather than answer without a verified quote | answer anyway | fatal for the brief | eval `unanswerable` bucket |

**Deliberately not built:** vector database (3 papers fit in memory), web UI/auth, fine-tuning,
LLM-as-judge grading, multi-provider failover, distributed queue/Redis.

## 5. Stages, with a gate we must pass before moving on

| Stage | Work | Gate (output we must see) |
|---|---|---|
| 0 | scaffold, config, corpus fetch + version/SHA manifest | 3 PDFs, sha256 + page counts printed |
| 1 | extraction (page+section), chunking, BM25 index, retrieval CLI | 5 hand-checked queries return the right page/section |
| 2 | Groq transport (SSE, TTFT, headers), limit probe (~25 req) | `limits.json` documented vs observed populated |
| 3 | pipeline + `verify_quote` tool + stand-in client | 20 eval questions run offline end-to-end |
| 4 | limiter, queue, retry, breaker, degradation | fake-clock unit tests pass; 429 storm behaves |
| 5 | stand-in service + calibration | stand-in p50/p95 within a stated band of real |
| 6 | load harness, 5 scenarios | 5 scenario blocks in `results.csv` |
| 7 | real eval (3 settings), grading, breakdown, retry experiment | Tables 1–3 generated **from** CSV |
| 8 | report (2 pages), README, audit, interview prep | page count = 2, `verify-tables` diff = 0 |

Days: 1 → stages 0–2 · 2 → 3–4 · 3 → 5–6 · 4 → 7–8.

## 6. Request budget (TPD is the wall)

| Day | Real requests | Est. tokens | Why |
|---|---|---|---|
| 1 | ~25 | ~8k | limit probe, latency sample |
| 2 | ~80 | ~100k | eval settings A + B (20 q each) |
| 3 | ~70 | ~90k | setting C + 10 confirmation answers |
| 4 | 0 | 0 | report only (stand-in for any re-runs) |

Load tests run entirely on the stand-in. If TPD binds mid-eval, we trim context (and report it)
rather than shrink the question set — comparability across settings matters more.

## 7. Risks

1. **2-page limit vs 5 tables.** Mitigation: report.md is generated with tables from CSV, HTML→print CSS
   tuned to exactly 2 A4 pages, verified by page count.
2. **Free-tier model turnover.** Model ids change; we resolve from `GET /v1/models` at startup and fail loud.
3. **TPD exhaustion mid-experiment.** Counters persist; the harness refuses to start a run it cannot afford.
4. **Stand-in fidelity is an assumption, not a measurement.** Only real request traces can calibrate it;
   we state exactly which parameters are assumption-backed.
5. **Grading honesty.** Mechanical quote-match is objective; final `answer_grade` is human-signed.
