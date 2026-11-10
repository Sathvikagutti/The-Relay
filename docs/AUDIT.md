# Phase 1 audit — project against the brief and the review

Date: 2026-11-10. Method: every line below was checked against the working tree, not
against memory. Commands used are listed per row so the check can be repeated.

## 1. What was inspected

| Area | Files / command | Result |
| --- | --- | --- |
| Source | `src/relay/**` (13 modules), `services/standin/**`, `tests/**` | present |
| Tests | `.venv/Scripts/python.exe -m pytest -q` | **21 passed** in ~1.5 s |
| Results | `results/results.csv` | 183 rows, header matches the brief exactly |
| Results provenance | `source` column | **`stand-in` only — zero real Groq rows** |
| Report | `report/REPORT.md`, `report/REPORT.pdf` | 2 pages, 12 headings in required order (pypdf check) |
| Tables | `report/TABLES.md` via `relay tables --write` | Tables 1–3 generated from CSV |
| Corpus | `data/index/manifest.json` | 3 pinned papers, SHA-256 recorded, **absolute Windows paths** |
| Stand-in | `services/standin/sim.py`, `app.py` | calibrated flags exist, **no `params.json`, no `results/limits.json`** |
| Load | `src/relay/experiments/load.py` | 5 scenarios; overload = 45 requests @ 60/min |
| Key | `.env` | `GROQ_API_KEY` still the placeholder — **no real call has ever run** |

## 2. Review claims, re-verified

| Review claim | Status | Evidence |
| --- | --- | --- |
| All 183 results are stand-in | **true** (now 493 rows, still all `stand-in`) | `sorted({r["source"] …}) == ['stand-in']` |
| Real-service experiments not done | **true** | `results/limits.json` absent; `.env` placeholder |
| Stand-in uses guessed defaults | **true** | `SimParams` defaults, `calibrated=False`, no `params.json` |
| Calibration files missing | **true** | `results/limits.json`, `services/standin/params.json` do not exist |
| Stand-in always answers, 0% correct refusals | **true** | `sim.py:187` `answerable = bool(question)` |
| Overload test not sustained | **true** | `load.py:60` — 45 requests at 60/min ≈ 45 s |
| Failure/timeout/partial paths unexercised | **partly true** | `timeout_rate`, `failure_rate`, `partial_rate` exist in `SimParams`, but no scenario drives them and no test covers partials |
| Graceful degradation not demonstrated | **partly true** | limiter refuses on day cap and returns `budget_exhausted`; no test or scenario shows the user-facing behaviour |
| Queue unbounded | **false** | `queue.py:24` — `max_waiting=32`, rejects with `retry-after` |
| README references missing files | **true** | `README.md:78,87,104` → `results/limits.json`, `services/standin/params.json`; `docs/SUBMISSION.md:31`, `docs/conversation-log.md:50` → `eval/review.csv` |
| `manifest.json` has absolute paths | **true** | `"path": "C:\\Users\\sathvika\\…\\data\\papers\\…pdf"` |
| Conversation history only a summary | **true** | `docs/conversation-log.md` is a summary, not a transcript |
| Latency analysis uses medians only | **true** | report quotes p50/p95; no single-request breakdown |
| Instrumentation insufficient for per-request breakdown | **false (good news)** | traces already carry `queued_ms`, `working_ms`, `retrying_ms`, `backoff_ms`, `calls` |

## 3. Requirement checklist

`R` ids are mine; `B` = brief, `V` = review/this prompt. Status: **done**, **partial**,
**not started**, **blocked** (needs the user).

| ID | Requirement | Current implementation | Problem | Required change | Files | Verification | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R1 | Real probe: RPM/RPD/TPM/TPD, in-flight, 429 body + retry-after, recovery, TTFT | `experiments/probe_limits.py` written, never run | no key | run it, record observed vs documented | `probe_limits.py`, `results/limits.json` | probe log + limits.json counters | **blocked** |
| R2 | Calibrate stand-in from real data | `experiments/calibrate.py` written, never run | no measurements | run after R1, write `params.json` with metadata | `calibrate.py`, `services/standin/params.json` | params.json `sample_size`, `calibrated_from` | **blocked** |
| R3 | Stand-in must identify itself as uncalibrated | `/health` returns `calibrated: false` | ok, but silent in answers | keep, surface in report + CSV `source` | `services/standin/app.py` | `/health` body | **done** |
| R4 | Real service must perform honest refusals; 0% is an artefact | `answerable = bool(question)` | unconditional answering | make answerability derivable from retrieved text; add refusal probes to eval | `services/standin/sim.py` | eval refusal rate > 0 with gold-region check | **not started** |
| R5 | ≥15 questions, 5 buckets, manual verification | 20 questions (13 answerable, 7 not, 5 categories); `relay review-sheet` writes a 60-row `eval/manual_grades.csv` with `final_grade`, `evidence_support`, `citation_correct`, `abstention_correct`, `notes`, plus `eval/review_sheet.md` | the blank columns need the author's judgement | fill 60 rows; `relay tables` then prefers `final_grade` | `eval/manual_grades.csv`, `eval/review_sheet.md`, `experiments/review.py` | rows = 60, columns present; Table 3 footnote switches to "human" once filled | **partial (blocked on human)** |
| R6 | Rubric explicit, no LLM judge | `docs/GRADING.md` rubric; separate `Quotes verified` column (100.0% every setting); refusal correctness reported as 0/21 in `docs/ANALYSIS.md` | answer grade still folds citation-location into `correct` | keep location in manual `citation_correct` column | `metrics.py`, `grading.py` | `TABLES.md` Table 3 | **done** |
| R7 | Fault injection: failure, timeout, slow, 429, partial, overload, retry exhaustion, day cap | 13 scripted-provider tests + `faulty` scenario (15% 500s, 5% timeouts, 10% truncated) | fault rates are synthetic, not Groq's | keep, label as synthetic | `tests/test_fault_behaviour.py`, `load.py` | `pytest` 13 passed; `faulty` rows 5 error / 1 timeout / 1 parse error | **done** |
| R8 | Sustained overload ≥3–5 min | `sustained`: 240 requests at 60/min, wall 239.0 s | none | keep | `load.py` | `summary.csv` wall 239.02, 12.5% ok | **done** |
| R9 | Bounded queue + admission control, trade-off explained | bounded at 32; sustained run peak_waiting 1, peak_inflight 2 | queue never fills because refusal precedes admission | explain in report rather than fake a queue | `queue.py`, report §5 | `TABLES.md` peak queue column | **done** |
| R10 | Graceful degradation demonstrated | `degraded` scenario runs the ladder: levels 0/1/2 = 22/21/17, context 578→411 tokens, calls 1.64→1.37 | no user received a trimmed answer, only refusals, so "weaker but correct answer" is unproven | state that limit in report §5 | `engine.py`, `load.py`, report §5 | trace `degrade_level` counts | **done** |
| R11 | Retry policy split by error kind | `NEVER_RETRY` covers bad_request/auth/day; tests assert one call for each | none | keep | `retry.py`, `tests/` | `test_permanent_error_is_not_retried`, `test_daily_cap_is_not_retried` | **done** |
| R12 | One experiment where retries made it worse | scripted 500: 1 attempt vs 3 attempts, same failure, >2.5x wall clock | synthetic provider, not Groq | state the limit in report §6 | `tests/test_fault_behaviour.py` | `test_retrying_makes_it_worse_same_failure_later` | **done** |
| R13 | Table 1 columns: limit, value, how found, confidence, in-flight, recovery | 5 columns incl. Confidence, TPD, in-flight, 429 behaviour, recovery | none left; observed cells await the probe | keep | `obs/metrics.py` | `TABLES.md` rows 6-13 | **done** |
| R14 | Table 2a: real/stand-in, requests, duration, offered rate, TTFT p50/95/99, total p50/95/99 | 12 columns, latency over successful requests only | none | keep | `metrics.py`, `load.py` | `TABLES.md` Table 2a | **done** |
| R15 | Table 2b: ok/rate-limited/given-up %, retries/request, peak queue, tokens/answer, cost per 1000 | 1-decimal percentages, peak queue from the runner gauge, cost stated as $0.00 free tier | `tokens/answer` is `not measured` where nothing succeeded | keep | `metrics.py` | `TABLES.md` Table 2b | **done** |
| R16 | Table 3: piece size, fetched, re-rank, questions, correct+cited %, wrong %, refused %, tokens, TTFT p50/95, total p50/95 | 14 columns incl. piece size/fetch/re-rank from `retrieval.yaml` | quality still stand-in only | rerun on real | `metrics.py` | `TABLES.md` Table 3 | **partial** |
| R17 | Single slow request broken down by id | `2ff56ecb7f73`: 31,832 ms = limit wait 27,261 + working 1,050 + queue 0 + retrying 0 | the first attempt showed 49 s unaccounted; limiter wait was untimed | added `limit_wait_ms` to the trace and re-ran | `obs/events.py`, `engine.py`, report §4 | trace JSONL matches report figures | **done** |
| R18 | Three retrieval settings compared on evidence | A/B/C evaluated (stand-in) | comparison is stand-in-only | re-run best-effort on real, keep stand-in for the rest | `experiments/run_eval.py` | Table 3 | **blocked** |
| R19 | Three ways the library misleads a naive retriever, with example questions | written in report | not demonstrated | add concrete question + retrieval result per failure mode | report, `eval/` | retrieved chunks listed | **partial** |
| R20 | README matches reality | stale references rewritten; `limits.json`/`params.json` now described as probe/calibrate outputs | none | keep in sync after step 5 | `README.md`, `docs/SUBMISSION.md`, `docs/conversation-log.md` | `grep -n 'review.csv'` returns nothing | **done** |
| R21 | Relative paths in manifest | `path` now `data/papers/<file>.pdf`, `path_convention` recorded; `fetch.portable()` writes relative from now on | none | keep | `data/index/manifest.json`, `corpus/fetch.py` | all three paths resolve inside a copied tree | **done** |
| R22 | Run from any directory | `relay tables` and manifest resolution verified in `C:/tmp/relay-portability` copy | ask/index from a copy not yet exercised | verify after step 3 reruns | `config.py` | copy tree, run `relay tables` → correct rows | **partial** |
| R23 | Real conversation history preserved | `docs/CONVERSATION.md`: verbatim prompts quoted, turn-by-turn work table, note that the first turn was compacted by the client and is not reconstructed | tool has no export button; pre-compaction text is unrecoverable | user may paste their own export if they have one | `docs/CONVERSATION.md` | prompts quoted match the messages sent | **done (as far as the tool allows)** |
| R24 | Report 2 pages, headings, every number traceable | 2 pages, headings ok | Tables need new columns; real rows missing | regenerate after data changes | `report/REPORT.md` | `build_pdf.py` page check | **partial** |
| R25 | Vaani feedback verified, not invented | live pages read 2026-11-10: hero counters render `0M+` / `0.0%` / `<0ms`; body claims "p90 latency of ~450ms"; `/pricing` has pay-as-you-go (₹1/min, 2 concurrent) and Enterprise, no free plan; screening ~98% under 15 s | not a live call or interview | keep the web-only caveat in the report | `report/FEEDBACK.md`, report | quotes match the fetched pages | **done (web-verified)** |
| R26 | No key exposure | `.env` ignored; zip and repo scanned | ok | re-scan each commit | `.gitignore` | `git grep gsk_` empty | **done** |
| R27 | Every table number recomputable from CSV | `relay tables` reads `results.csv` + `results/load/summary.csv` + `limits.json` | limit/probe cells await R1 | regenerate after R1 | `metrics.py` | rerun tables, diff | **partial** |
| R28 | CSV schema exact | 12 columns, exact order, 493 rows | none | keep | `csvio.py` | header compare | **done** |
| R29 | Separate citation-correctness metric | `Quotes verified` column in Table 3 (100.0% all settings) from `results/eval/*.json`; location judged by hand in `citation_correct` | location half is manual | fill manual column | `metrics.py`, `experiments/review.py` | `TABLES.md` Table 3 | **done** |
| R30 | Refusal and failure categories explained from logs | `docs/ANALYSIS.md`: 0/21 refusals, 210 provider 429s with body quoted, 5x500 with 3 attempts, 1 timeout, 1 truncated stream | synthetic fault rates | keep caveats | `docs/ANALYSIS.md` | figures recomputed from CSV + traces | **done** |
| R31 | Grading file with the required fields | `relay review-sheet` → 60 rows x (final_grade, evidence_support, citation_correct, abstention_correct, notes) + readable sheet | needs human fill | fill and rerun `relay tables` | `experiments/review.py`, `eval/` | files exist, 60 rows | **partial (human)** |

## 4. Safest order of change

1. **R21, R22, R20** — portability and docs first: they touch no results, and every later
   run writes paths into JSON that would otherwise stay absolute.
2. **R13–R16, R27** — table column gaps, because the new columns decide what the load
   runs must record. Add `duration_s`, `offered_rate`, `source`, `in_flight`, `cost`.
3. **R7, R8, R9, R10, R11, R12** — fault injection and the 4-minute overload run on the
   stand-in. No key needed, and this is where the review says the evidence is thinnest.
4. **R4, R5, R6, R17, R19** — answer quality: stand-in refusal logic, manual grading,
   per-request trace breakdown, misleading-library examples.
5. **R1, R2, R18** — the real Groq probe, calibration, and real evaluation. Blocked on
   the key; run last so the code they exercise is already frozen.
6. **R24, R25, R23** — report, feedback, history: regenerate from final data.
7. Re-run `combine`, `tables --write`, `build_pdf.py`, full `pytest`, then the audit.

## 5. Review PDF reconciliation

The review file arrived after this audit was written. It adds these specifics on top of
the findings listed in the prompt; every one is mapped, and the first block is closed by
steps 1-2.

| Review line | Where it is handled | Status |
| --- | --- | --- |
| Percentages must be one decimal (96.7%, 45.5, 36.4, 18.2) | `_pct` now formats `.1f`; Tables 2b/3 show 96.7%, 45.5%, 36.4%, 18.2% | done |
| Burst `total p50 7 ms` mixes instant refusals into latency | latency now covers successful requests only; `Answered` column added, refusals counted in Table 2b | done |
| Table 1 missing tokens/day, in-flight, recovery, Confidence | `table_1` has 5 columns and all 7 limit rows; observed cells await the probe | done (values blocked) |
| Table 2a missing Duration (s) and Offered rate | both columns added, fed by `results/load/summary.csv` | done |
| Table 3 missing p95 first-token and total time | both columns present, plus piece size / fetched / re-rank | done |
| README references `eval/review.csv`, `results/limits.json` | rewritten to name the real file (`eval/manual_grades.csv`) and to say limits.json appears only after the probe | done |
| `manifest.json` has absolute Windows paths | relative paths + `path_convention`, written by `fetch.portable()`; verified inside a copied tree | done |
| Stand-in faults never exercised (fail/slow/partial at 0) | R7: 13 scripted tests + `faulty` scenario (5 errors, 1 timeout, 1 parse error) | done |
| Sustained overload is 45 s | R8: `sustained` ran 239 s at 60/min, 12.5% ok | done |
| Graceful degradation never triggered; burst sheds instead of queueing | R10: ladder measured from the current run (`degraded` levels 0/1/2, context and call counts in `docs/ANALYSIS.md`); burst now waits in the bounded queue instead of being dropped (see §7) | done |
| Section 4 should split one slow request by `request_id` | R17: `2ff56ecb7f73` split; required new instrumentation (`limit_wait_ms`) | done |
| Retrieval behaviour when the limit is close | step 4 (report + setting comparison) | open |
| Conversation history must be the real one | R23: `docs/CONVERSATION.md` quotes the prompts verbatim, lists the rules I set and the decisions I made, and discloses that the first turn was destroyed by the client's context compaction | done (as far as the tool allows) |
| Vaani "0.0% accuracy counters" claim must hold up live | R25: live pages read 2026-11-10 — counters render `0M+`/`0.0%`/`<0ms`, body claims ~450 ms p90, `/pricing` has no free plan | done |
| Real probe, calibration, real eval | R1, R2, R18 — blocked on the API key | open |

## 6. Blockers owned by the user

- **Review PDF** — `The Relay Review Against the Brief.pdf` is not in the project folder
  and did not arrive as an attachment, so I worked from the findings listed in the
  prompt. If the PDF contains requirements beyond those, they are missing here.
- **API key** — `GROQ_API_KEY` is still `replace_me`. Estimated real-service cost:
  probe ≈ 3–5k tokens; real eval for one setting ≈ 55–60k tokens; all three settings
  ≈ 170k of the 200k daily budget. Approval needed before more than one setting.

## 7. Second review: report/CSV drift, and the three harness bugs behind it

The second review found that the report's limit-halved and retry figures did not match
`results/results.csv`. The mismatch was real, and chasing it exposed three defects in the
measurement harness, each of which is now fixed and covered by the notes below.

| Review point | Cause | Fix | Evidence |
| --- | --- | --- | --- |
| limit halved: report says 10 OK / 45.5% / 36.4% / 18.2%, p50 17,146 ms; CSV says 9 OK / 40.9% / 0.0% / 59.1%, p50 2,485 ms | report tables were typed by hand and survived a load re-run | report now imports Tables 1, 2a, 2b and 3 from `report/TABLES.md` at build time (`{{table:2a}}` etc. in `report/REPORT.md`, expanded by `report/build_pdf.py`), and `TABLES.md` is only ever written by `relay tables --write` | `build_pdf.py: table_block/expand_tables`; `relay tables` diff vs `TABLES.md` is empty |
| §5 repeats 45.5/36.4/18.2 | prose written from the old table | §5 rewritten from the current tables | `report/REPORT.md` §5 |
| §6 says 38 retried rows, 3 succeeded; "0.36 when halved" | same stale run; the retried-row count was also read from the wrong filter | §6 now reports the current counts, computed from `results.csv` | `docs/ANALYSIS.md` §2 |
| degraded "levels 22/21/17 of 30" sums to 60 | `results/raw/load_*.jsonl` was opened in append mode, so it accumulated every run ever made while the CSV held only the latest; the ladder counts came from the appended file | `JsonlWriter(truncate=True)` for load runs, so one run writes one file | `src/relay/obs/events.py`; raw line count equals CSV row count per scenario |
| Peak queue is 1 in every scenario | `load.py` wrapped each request in an `asyncio.Semaphore(scenario.concurrency)` *and* the admission queue used the same number as its in-flight limit, so nothing ever waited and `peak_waiting` was structurally 1 | the redundant semaphore is gone: the queue is the only admission control, so waiting is real and counted | `peak_waiting` now 24 (burst) and 9-10 (overload/sustained) |

Two further harness defects were found while re-running and would have produced
misleading numbers even after the above:

* **Fault rates leaked between scenarios.** The stand-in keeps `PARAMS` in process
  globals and the `faulty` scenario set them by query string, so every later scenario in
  the same server process ran with 15% server errors. Every scenario now states
  `fail=0&timeout=0&partial=0` explicitly (`SERVER_DOCUMENTED`), and only `faulty`
  overrides them. Signature of the old behaviour: a `steady` run at 4/min with retries
  and one 30 s timeout, which is impossible without injected faults.
* **Rate windows leaked between scenarios.** The simulator's minute/day buckets are also
  process-global, so `limit_halved` inherited the empty minute left by the 240-request
  `sustained` run and refused all 22 requests in 4 ms. The stand-in now exposes
  `POST /reset`, and the load runner calls it before every scenario.

Both are harness bugs, not scheduler results: they made the system look like it dropped
traffic it never saw. With them fixed, `limit_halved` and `degraded` are measured against
a clean window, which is what the report now shows.

### What did not change

The API-key blockers stand: no real probe, no calibration, no real evaluation, and
`final_grade` is still blank for the author's own judgement. Those are §6 items and this
review did not touch them.
