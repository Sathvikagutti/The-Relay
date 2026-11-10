# Conversation record

The assignment asks for the real conversation with the assistant, not a tidied
narrative. The tool used here does not expose an export button, so this file separates
what can be quoted verbatim from what cannot, and it separates what I decided from what
the assistant implemented.

## Verbatim prompts (quoted, unedited)

These are the messages I sent, copied exactly, including typos and spacing:

1. `https://github.com/Sathvikagutti/The-Relay  push the project into this github link`
2. `https://drive.google.com/drive/u/0/folders/1A3jHjks7wZHlgU9E78GakHlXtuiFxnnJ    upload the project into this drive link`
3. `I connected Google Drive. Go ahead.`
4. `you resolve the bugs`
5. `yes continue to make changes`
6. The long correction brief beginning `THE RELAY — COMPLETE PROJECT CORRECTION AND IMPROVEMENT PROMPT`,
   which lists Phases 1–14. It is reproduced requirement by requirement in
   `docs/AUDIT.md` §5, because quoting 4,000 words twice would help nobody.
7. The final review request beginning `Review my entire **The Relay — Vaani ML Engineering Intern assignment** repository`.

Those prompts are short. They are short because the steering was not in the wording: it
was in the rules I set and in which proposals I accepted or rejected. The next two
sections are the honest account of that, and they are the part worth reading.

## The rules I set, and held the work to

These came from me, in the correction brief and in the review requests, and they are the
reason the repository looks the way it does:

| Rule I set | Where it shows up |
| --- | --- |
| Never fabricate a limit, latency, accuracy figure, token count or cost; every number must come from an execution | Table 1's Observed column says `not measured` for all 7 rows rather than quoting a blog post; every row carries `source` |
| If something is unmeasured, say so and name the blocker instead of claiming completion | `docs/AUDIT.md` §6, the report's §2 and §8, and this file's Drive row |
| Real and stand-in results must be visibly separate | `source` column in every CSV; "stand-in" in every load table caption |
| Answer grading must be mine, not a model's | `eval/manual_grades.csv` ships with `final_grade` blank; no LLM judge anywhere in `src/relay/grading.py` |
| Exactly 2 pages, 12 sections in a fixed order, ms and 1-decimal % | `report/build_pdf.py` exits non-zero above 2 pages; `report/TABLES.md` is generated, not typed |
| Do not throw away work that already passed | the push at `1fa8504` was extended, never rewritten; no `reset --hard`, no force push |
| Same question set across retrieval settings, so A/B/C are comparable | `eval/questions.yaml` is fixed at 20 items and every setting runs all of them |

Two rules changed the design rather than the documents. The first was "measure the
limits before designing the limiter", which is why `probe-limits` and `calibrate` exist
as commands and why the scheduler is token-based. The second was "every table must
regenerate from `results.csv`", which is why `relay tables` is the only writer of
`TABLES.md` and why a mismatch between the report and the CSV is a bug, not a typo.

## Decisions that were mine, with the reason

* **Pin the three papers at the versions named in the brief** (1706.03762 v7, 2410.00037
  v1, 2507.07955 v2) and verify SHA-256 on download. A moving `latest` URL would make
  every citation unreproducible.
* **Refuse rather than answer unverified.** I would rather ship a visible refusal than
  a confident paragraph with a plausible-looking page number.
* **Keep BM25.** The assistant proposed a vector store for 349 chunks; I overruled it,
  because at this corpus size the retrieval failure modes are heading/body and
  appendix-gravity, which BM25 over headings handles and which an embedding model would
  not fix by itself.
* **Let the assistant write the code and the measurements, and keep the judgement
  calls.** Where a call was about honesty (blank `final_grade`, `not measured` cells,
  the blocker list) I insisted; where it was about implementation I let it choose.

## Where the verbatim record is incomplete

The first turn of the session — where the assignment PDF was supplied — is not
reproducible from inside the tool: the conversation was condensed by the client's
context compaction, which replaced early messages with a summary. Reconstructing that
text would be fabrication, so it is not attempted. `docs/conversation-log.md` keeps the
summary that the compaction produced, labelled as a summary.

## What was done in response, in order

| Turn | Request | Work actually performed |
| --- | --- | --- |
| 1 | Build the assignment | Corpus pinned (v7, v1, v2 + SHA-256), 349 chunks indexed, pipeline and scheduler written, stand-in service, 5 load scenarios, 3-setting evaluation, `results.csv`, tables, 2-page report, 21 tests |
| 2 | Push to GitHub | `git init`, single commit, `.gitignore` corrected, pushed to `Sathvikagutti/The-Relay` (`1fa8504`), remote ref verified |
| 3 | Upload to Drive | Archive built and validated (`dist/The-Relay.zip`, 84 files, no `.env`); **not uploaded** — no Drive upload tool was bound to the session and the browser was signed out; reported as a blocker, not claimed |
| 4 | "resolve the bugs" | Audited against the review PDF; relative paths in `manifest.json`, stale README references, table columns (Source, Answered, Duration, Offered, Confidence, p95s), one-decimal percentages, latency over successful requests only |
| 5 | "yes continue to make changes" | 13 deterministic fault tests; `sustained` (239 s), `faulty`, `degraded` scenarios; discovered and fixed 49 s of untimed limiter wait (`limit_wait_ms`); report rewritten, still 2 pages |
| 6 | Final review request | `docs/ANALYSIS.md` refusal/failure breakdown, separate quote-verification metric, `relay review-sheet` and a 60-row grading file, live Vaani page verified |
| 7 | Second review | Report/CSV mismatch fixed at the cause: the report now imports its tables from `TABLES.md` at build time; the `peak queue = 1` bug traced to a redundant semaphore and removed; two further harness leaks found on re-run (fault rates and rate windows surviving between scenarios in the stand-in's process globals) and fixed with explicit fault parameters and a `POST /reset`; load suite re-run and all figures regenerated |

## What the assistant contributed

The implementation, the measurements and the wording of the documents. Where the record
shows the assistant getting something wrong, it is left in rather than smoothed over: the
breaker that counted 429s as outages, the 49 s of untimed limiter wait, and the report
text that survived a load re-run while the CSV did not. Each is listed in `docs/AUDIT.md`
with the fix.
