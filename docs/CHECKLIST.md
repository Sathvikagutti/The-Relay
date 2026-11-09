# The Relay — Requirement Checklist

Source of truth: `The_Relay_Assignment_Brief.pdf` (4 pages) + the master prompt.
Status: `[ ]` not started · `[~]` in progress · `[x]` done & verified · `[!]` blocked

Every `[x]` must be backed by a command whose output we have actually seen.
Nothing in this project is marked done because it "looks right".

---

## A. Ground rules & process

| ID | Requirement | Artifact | Verified by |
|----|-------------|----------|-------------|
| A1 | Python implementation | `src/relay/**` | `python -m relay --help` |
| A2 | Own free Groq account + key, key never in submission | `.env` (gitignored), `.env.example` | `git grep -i gsk_` returns nothing; `.gitignore` check |
| A3 | No extra accounts / no limit circumvention | one key, one org | `results/limits.json` shows a single org/limit set |
| A4 | Submit within 4 days | stage plan in `docs/PLAN.md` | checklist dates |
| A5 | Max 2 pages of writing | `report/report.pdf` | page count = 2, measured |
| A6 | Real conversation history included, not cleaned up | `docs/conversation-log.md` + exported chat | file exists, prompts verbatim |
| A7 | Don't invent limits/results/costs/grades/feedback | every cell traceable to `results/` | `python -m relay verify-tables` |

## B. The pipeline

| ID | Requirement | Artifact | Verified by |
|----|-------------|----------|-------------|
| B1 | ≥ 4 steps | `src/relay/pipeline/orchestrate.py` | pipeline trace shows ≥4 spans |
| B2 | ≥ 1 tool call | `pipeline/tools.py` (`verify_quote`) | trace shows tool span + result |
| B3 | ≥ 1 branch or loop | repair loop + degradation ladder | trace of a forced-invalid citation |
| B4 | One step retrieves passages | `retrieval/*` | trace shows retrieval span with chunk ids |
| B5 | Answers only from the 3 papers | prompt + validator | eval: out-of-library question refuses |
| B6 | Every answer cites paper + page/section | `models.Citation` | validator rejects citation without page |
| B7 | Refuses when papers don't say | refusal path | eval `unanswerable` bucket |
| B8 | Never sends an unsupported answer to stay fast | cite-validate before reveal | retry-exp test shows refuse, not guess |
| B9 | Components testable independently | `tests/**` | `pytest -q` |

## C. Library & retrieval

| ID | Requirement | Artifact | Verified by |
|----|-------------|----------|-------------|
| C1 | Attention Is All You Need **v7** (1706.03762) | `data/papers/1706.03762v7.pdf` | manifest: version + sha256 |
| C2 | Moshi **v1** (2410.00037) | `data/papers/2410.00037v1.pdf` | manifest |
| C3 | Dynamic Chunking **v2** (2507.07955) | `data/papers/2507.07955v2.pdf` | manifest |
| C4 | Text extraction preserves page numbers | `corpus/extract.py` | spot-check 10 chunks vs PDF pages |
| C5 | Section headings preserved | `corpus/extract.py` | chunk metadata has `section` |
| C6 | Configurable chunk size | `config/retrieval.yaml` | 3 settings produce different chunk counts |
| C7 | Configurable top-k | `config/retrieval.yaml` | same |
| C8 | Optional re-ranking | `retrieval/rerank.py` | `rerank: none|cross_encoder` |
| C9 | ≥ 3 retrieval configurations compared | Table 3 | 3 settings × 20 questions |
| C10 | Best config chosen from measurements | `docs/DECISIONS.md` | numbers, not vibes |

## D. Real Groq service

| ID | Requirement | Artifact | Verified by |
|----|-------------|----------|-------------|
| D1 | Documented limits collected from docs/console | `results/limits.json` → `documented` | URL + read date recorded |
| D2 | Observed limits from actual responses | `results/limits.json` → `observed` | response headers captured |
| D3 | What it returns at a limit (status + body + headers) | `results/raw/limit_probe.jsonl` | captured 429 evidence |
| D4 | Documented vs observed vs assumed vs not-measured, labelled | Table 1 | confidence column filled |
| D5 | Latency distribution measured | `results/raw/real_latency.jsonl` | percentiles computed from CSV |
| D6 | TTFT measured separately from total | `obs/events.py` | first-token span exists |
| D7 | Token usage recorded per request | results.csv `tokens_in/out` | sums match Groq `usage` |
| D8 | Modest request count (TPD is the real cap) | request budget in `docs/PLAN.md` | `results.csv` real-row count |

## E. Stand-in service

| ID | Requirement | Artifact | Verified by |
|----|-------------|----------|-------------|
| E1 | Normal + variable latency | `services/standin/sim.py` | latency histogram of N=200 |
| E2 | Slow responses & timeouts | `sim.py` profile `stall` | client deadline fires |
| E3 | Failures (5xx) | `sim.py` | retry path exercised |
| E4 | Rate-limit errors (RPM, RPD) | `sim.py` | 429 + `retry-after` |
| E5 | Requests-per-minute limit | `sim.py` | window counter test |
| E6 | Requests-per-day limit | `sim.py` | daily exhaustion scenario |
| E7 | Latency increases under load | `sim.py` queue model | p95 rises with concurrency |
| E8 | Concurrent requests | uvicorn async | 50 in-flight handled |
| E9 | Streaming, partial responses | SSE chunks, mid-stream cut | partial-response test |
| E10 | Recovery after a limit | window reset | recovery time recorded |
| E11 | Calibrated from real measurements | `services/standin/calibrate.py` | fitted params + source numbers |
| E12 | Deterministic/reproducible | seeded RNG per (scenario, idx) | same seed → same CSV stats |
| E13 | Differences from real + weakest assumption named | report §2 | explicit paragraph |

## F. Load testing (≥3 shapes; brief's Table 2a wants 5)

| ID | Requirement | Artifact | Verified by |
|----|-------------|----------|-------------|
| F1 | Steady | `scenarios.yaml` | results.csv block |
| F2 | Sudden burst | idem | idem |
| F3 | Sustained overload | idem | idem |
| F4 | Per-minute limit halved | idem | idem |
| F5 | Daily budget exhausted | idem | idem |
| F6 | Per scenario: sent, duration, offered rate | Table 2a | recomputed from CSV |
| F7 | Per scenario: TTFT + total p50/p95/p99 | Table 2a | idem |
| F8 | Succeeded %, rate-limited %, timed-out % | Table 2b | idem |
| F9 | Retries/request, peak queue, tokens/answer | Table 2b | from event log |
| F10 | Cost per 1,000 answers | Table 2b | price source recorded (free tier → $0 cash, list-price equivalent labelled) |
| F11 | Real vs stand-in clearly separated | `source` column | every row tagged |
| F12 | Behaviour explained per scenario | report §3 | prose matches numbers |

## G. Reliability & rate-limit handling

| ID | Requirement | Artifact | Verified by |
|----|-------------|----------|-------------|
| G1 | Bounded queue + concurrency cap | `scheduling/queue.py` | peak queue length measured |
| G2 | Token budget + request budget enforced | `scheduling/limiter.py` | unit test with fake clock |
| G3 | Backpressure (reject with retry-after when full) | orchestrator | test: queue full → 429 |
| G4 | Exponential backoff + full jitter | `scheduling/retry.py` | delay sequence printed |
| G5 | Per-request deadline | orchestrator | test: deadline → timeout grade |
| G6 | Circuit breaker | `scheduling/breaker.py` | open/half-open test |
| G7 | Graceful degradation ladder | `pipeline/degrade.py` | scenario 5 trace |
| G8 | User cancellation | `asyncio.CancelledError` path | test |
| G9 | Techniques chosen for measured reasons, trade-offs stated | report §5 | prose |
| G10 | Never degrade into an unsupported answer | validator gate | degrade ladder has no citation-dropping step |

## H. Retry experiments

| ID | Requirement | Artifact | Verified by |
|----|-------------|----------|-------------|
| H1 | Retryable vs non-retryable classes defined | `retry.py` | table in report §6 |
| H2 | Max attempts, backoff, jitter, budget, deadline | `retry.py` | config + test |
| H3 | ≥ 1 experiment where retrying made it **worse** | `experiments/retry_experiment.py` | paired comparison numbers |

## I. Answer quality

| ID | Requirement | Artifact | Verified by |
|----|-------------|----------|-------------|
| I1 | ≥ 15 questions written by us | `eval/questions.yaml` | count |
| I2 | Buckets: clear / multi-passage / citation-sensitive / unanswerable / hallucination-bait | idem | 5 buckets non-empty |
| I3 | Explicit grading method | `docs/GRADING.md` | rubric with definitions |
| I4 | Manual verification against papers | `eval/manual_grades.csv` | human-signed rows |
| I5 | Not "correct because another LLM said so" | mechanical quote-match + human sign-off | no LLM-judge in the grading path |
| I6 | correct / wrong / correctly-cited / incorrect-citation / correct-refusal / incorrect-refusal / tokens | Table 3 + report §3 | recomputed |

## J. `results.csv`

| ID | Requirement | Artifact | Verified by |
|----|-------------|----------|-------------|
| J1 | One row per request | `results/results.csv` | row count == event count |
| J2 | Exact 12 columns, exact names/order | schema | `relay verify-csv` |
| J3 | `status ∈ {ok, rate_limited, timeout, error}` | schema validator | rejects others |
| J4 | `answer_grade ∈ {correct, wrong, refused_correctly, refused_wrongly}` | idem | idem |
| J5 | Every table number computable from the CSV | `obs/metrics.py` | `relay verify-tables` diff == 0 |
| J6 | No fabricated rows | provenance: `start_time` from real runs | timestamps monotonic per run |

## K. Report

| ID | Requirement | Artifact |
|----|-------------|----------|
| K1 | `1 What I built and why` + the one decision that shaped it most | `report/report.md` |
| K2 | `2 The real service and my stand-in` | idem |
| K3 | `3 Results` incl. a number we could not have guessed | idem |
| K4 | `4 Where the time goes` — waiting/working/retrying split, pre- vs post-first-token, with evidence | idem |
| K5 | `5 When a limit is hit` — per-minute vs per-day, who's delayed/dropped/degraded | idem |
| K6 | `Retrieval: quality versus cost` (inserted after 5) | idem |
| K7 | `How this library will mislead a naive retriever` (after 5) — 3 ways, each with a failing example question | idem |
| K8 | `6 Retries` | idem |
| K9 | `7 What the person sees` — 3pm budget-gone reply, verbatim | idem |
| K10 | `8 What I'm unsure about…` — least certain assumption + breakage, 2 things not built, 1 thing learned in own words | idem |
| K11 | `Your feedback on Vaani` — standout / confusing / one change | idem |
| K12 | `How I worked with the assistant` — 3 key prompts, 1 thing it got wrong + how caught, 1 overrule, what is distinctively mine | idem |
| K13 | Table 1, 2a, 2b, 3 fully filled (`not measured` where true) | `report/tables/*.md` |
| K14 | 2 pages max, ms and 1-decimal % | PDF page count |
| K15 | Headings in the exact order required | `verify-report` heading check |

## L. Vaani feedback

| ID | Requirement | Verified by |
|----|-------------|-------------|
| L1 | Site actually visited | notes with date + what was on the page |
| L2 | Honest, specific, no generic praise | quotes from the site in report |
| L3 | Standout / confusing / one improvement | 3 labelled sentences |

## M. Engineering quality

| ID | Requirement | Artifact |
|----|-------------|----------|
| M1 | Modular, clear naming, type hints | `src/relay/**` |
| M2 | Error handling + logging | `obs/events.py` |
| M3 | Config management + env vars | `config/*.yaml`, `.env.example` |
| M4 | Unit + integration tests | `tests/` |
| M5 | Data validation | csv/schema validators |
| M6 | Reproducible experiments | seeded, versioned configs |
| M7 | README with run instructions | `README.md` |
| M8 | No over-engineering | `docs/DECISIONS.md` "not built" list |
| M9 | Clean GitHub-ready tree | `.gitignore`, no secrets, no venv |

## N. Submission pack

| ID | Requirement |
|----|-------------|
| N1 | source code + `requirements.txt` + `README.md` + `.env.example` |
| N2 | `results.csv` + raw JSONL |
| N3 | 2-page report (PDF) |
| N4 | conversation history (exported + `docs/conversation-log.md`) |
| N5 | submission checklist (`docs/SUBMISSION.md`) |
| N6 | live-interview Q&A prep (`docs/INTERVIEW.md`) |
| N7 | key absent from every artifact |

---

## Progress log

| Stage | Status | Evidence actually observed |
|---|---|---|
| 0 Scaffold + pinned corpus | `[x]` | `python -m relay fetch-corpus` → 3 PDFs, `v7 ok / v1 ok / v2 ok`, sha256 + page counts in `data/index/manifest.json`; `pytest -q` → 4 passed |
| 1 Extraction, chunking, index | `[ ]` | — |
| 2 Groq transport + limit probe | `[ ]` | — |
| 3 Pipeline + verify_quote tool | `[ ]` | — |
| 4 Scheduler, limiter, retry, breaker | `[ ]` | — |
| 5 Stand-in service + calibration | `[ ]` | — |
| 6 Load scenarios | `[ ]` | — |
| 7 Real eval + grading + breakdown | `[ ]` | — |
| 8 Report + audit | `[ ]` | — |

## Requirements verified so far

- **A1** — package runs as `python -m relay` (editable install, src layout).
- **C1 / C2 / C3** — each paper's page-one arXiv marker matches the pin; sha256 recorded for later re-checks.
- **M4 (partial)** — 4 offline unit tests covering version-marker parsing and URL/filename pinning.

Corpus facts recorded at fetch time: Attention v7 = 15 pages, Moshi v1 = 66 pages,
Dynamic Chunking v2 = 39 pages (120 total).
