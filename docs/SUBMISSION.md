# Submission checklist

Mirrors the brief, one line per requirement, with where to find the evidence.
Anything pending is marked **PENDING**, never quietly omitted. Last checked against
commit `8c6a683` (2026-11-11).

## Required artefacts

| Requirement | Status | Where |
| --- | --- | --- |
| Working Python RAG assistant over the three pinned papers | done | `src/relay/`, `relay ask "..."` |
| Pinned versions (1706.03762 v7, 2410.00037 v1, 2507.07955 v2) | done | `config/default.yaml`, `data/index/manifest.json`, `relay fetch-corpus --check` |
| >= 4 pipeline steps | done | analyze -> retrieve -> draft -> verify -> (repair loop) in `pipeline/steps.py` |
| >= 1 tool call | done | `verify_quote` in `pipeline/tools.py`, recorded per request |
| >= 1 branch or loop | done | answerable branch, repair loop, degrade levels, retry loop |
| Retrieval step | done | BM25 over heading+body, `retrieval/index.py` |
| Every answer cites paper + page/section | done, enforced | `verify_citations`; page/section from metadata only |
| Refuses when the papers do not answer | done | out-of-library branch, `REFUSAL_NO_PASSAGE` |
| No unsupported answer sent to look fast | done, measured | latency includes verification; failures are recorded as failures |
| Real Groq free-tier calls, modest | done | probe (2 runs), calibration, eval setting A: 20 real rows in `results/results.csv` |
| Measured limits, not documented guesses | done (5 of 7 rows) | `results/limits.json`; tokens/day and in-flight stay `not measured` |
| Calibrated stand-in for heavy load | done | `services/standin/params.json`, `/health` -> `calibrated: true` |
| State where stand-in differs least/most | done | `params.json` `differences`, report §2 |
| 5 load scenarios | done (8 scenarios, stand-in) | `relay load`, `results/load/*.csv` |
| Per-minute limit halved scenario | done | `limit_halved` |
| Daily budget exhausted scenario | done | `daily_exhausted` |
| Sustained overload 3-5 min | done | `sustained`, 240 requests, 239.0 s |
| `results.csv` with exact columns | done (493 rows) | `results/results.csv`, schema enforced on write |
| Status values from the allowed set | enforced | `obs/csvio.py` raises on anything else |
| Grades from the allowed set | enforced | same |
| Every table number recomputable from the CSV | done | `relay tables` reads the CSV (+ `limits.json` for Table 1) |
| >= 15 self-written questions, 5 buckets | done | `eval/questions.yaml` (20) |
| Explicit grading rules, no LLM judge | done | `docs/GRADING.md` |
| Manual verification of answers | **PENDING (author's judgement)** | `eval/manual_grades.csv` + `eval/review_sheet.md`; 0 of 20 filled |
| Real evaluation of settings B and C | **PENDING (daily token quota)** | command below; A is real, B/C are stand-in |
| 2-page report, headings in order | done | `report/REPORT.pdf` (2 pages, heading check passes) |
| Extra sections after heading 5 | done | Retrieval quality vs cost; How the library misleads a naive retriever |
| Tables 1, 2a, 2b, 3 filled (`not measured` allowed) | done | `report/TABLES.md`, expanded at build time |
| Feedback on Vaani | done (web-verified) | report section; `report/FEEDBACK.md` |
| How I worked with the assistant | done | `docs/CONVERSATION.md` |
| API key never printed or committed | verified | `.env` gitignored; `git grep gsk_` on HEAD is empty |
| No extra accounts or paid services | verified | only Groq + local stand-in |
| Submission ZIP | done locally | `dist/The-Relay.zip` (rebuilt from this commit, `.env` excluded) |

## Commands that produce each artefact

```bash
relay fetch-corpus --check          # pin verification
relay probe-limits                  # ~45 real requests, writes results/limits.json
relay calibrate                     # fits stand-in params from the probe
relay eval --settings A --source real --limits documented
relay eval --settings B C --source real --limits documented   # pending quota reset
relay load --source stand-in        # eight scenarios
relay combine                       # merges row files -> results/results.csv
relay tables --write                # regenerates report/TABLES.md
python report/build_pdf.py          # 2-page PDF, exits non-zero above 2 pages
```

## Pending, and why

* **Real B and C evaluation.** The probe and setting A consumed roughly 150,000 of the
  200,000 daily tokens. B and C need about 33,000 each, so running them the same day
  risks finishing mid-run with `rate_limited` rows in the table. They are left as
  stand-in rows, each labelled `stand-in` in Table 3's new Source column, rather than
  presented as a controlled comparison.
* **Manual grading.** `eval/manual_grades.csv` has 20 real Setting A rows with
  `final_grade` blank. Grading is the author's judgement and is not generated here.
* **Drive upload.** No Drive upload tool is bound to this session. The ZIP is built and
  verified locally; upload instructions are in `docs/SUBMISSION.md` §Upload.

## Upload

`dist/The-Relay.zip` is built from the working tree at this commit and verified to
contain no `.env`, no virtual environment and no API key. To submit:

1. Open https://drive.google.com/drive/u/0/folders/1A3jHjks7wZHlgU9E78GakHlXtuiFxnnJ
2. Right-click -> File upload -> `dist/The-Relay.zip`
3. After the upload completes, right-click the file -> Share -> copy link, and check
   that the link opens in a signed-out window (the folder is shared, not private).

This session had no Drive tool bound, so the upload is left to you rather than claimed.
