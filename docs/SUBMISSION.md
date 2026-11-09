# Submission checklist

Mirrors the brief, one line per requirement, with where to find the evidence.
Anything pending is marked **PENDING**, never quietly omitted.

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
| Real Groq free-tier calls, modest | **PENDING key** (nothing invented) | `relay probe-limits`, `relay calibrate`, `relay eval --source real` |
| Calibrated stand-in for heavy load | code done, params **PENDING key** | `services/standin/`, `relay calibrate` |
| State where stand-in differs least/most | done (template), numbers pending | `services/standin/params.json` `differences` |
| 5 load scenarios | done (stand-in) | `relay load`, `results/load/*.csv` |
| Per-minute limit halved scenario | done | `limit_halved` scenario |
| Daily budget exhausted scenario | done | `daily_exhausted` scenario |
| `results.csv` with exact columns | done | `results/results.csv` (schema enforced on write) |
| Status values from the allowed set | enforced | `obs/csvio.py` raises on anything else |
| Grades from the allowed set | enforced | same |
| Every table number recomputable from the CSV | done | `relay tables` reads only the CSV (+ `limits.json` for Table 1) |
| >= 15 self-written questions, 5 buckets | done | `eval/questions.yaml` (20) |
| Explicit grading rules | done | `docs/GRADING.md` |
| Manual verification of answers | **PENDING** | `eval/review.csv` + `eval/manual_grades.csv` |
| No LLM-as-judge | done | mechanical quote/gold checks only |
| 2-page report, headings 1-8 in order | done (stand-in numbers) | `report/REPORT.pdf` (2 pages, heading check passes) |
| Extra sections after heading 5 | done in draft | Retrieval quality vs cost; How the library misleads a naive retriever |
| Tables 1, 2a, 2b, 3 filled ("not measured" allowed) | done | `report/TABLES.md`, embedded in the report |
| Feedback on Vaani | **PENDING user voice** | `report/FEEDBACK.md` draft |
| How I worked with the assistant | done | `docs/conversation-log.md` |
| API key never printed or committed | verified | `.env` gitignored; no key in any tracked file |
| No extra accounts or paid services | verified | only Groq + local stand-in |

## Commands that produce each artefact

```bash
relay fetch-corpus --check          # pin verification
relay probe-limits                  # ~45 real requests, writes results/limits.json
relay calibrate                     # fits stand-in params from the probe
relay eval --settings A B C --source stand-in
relay eval --settings A --source real
relay load --source stand-in        # five scenarios
relay combine                       # merges row files -> results/results.csv
relay tables --write                # regenerates report/TABLES.md
```

## Pending because the key is not in `.env`

The free-tier key is a placeholder (`replace_me`). Everything that needs it is written
and runnable, but no real number has been invented to fill the gap: those tables say
`not measured` and the report says so in the caveats.
