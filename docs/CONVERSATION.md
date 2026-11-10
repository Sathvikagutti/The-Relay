# Conversation record

The assignment asks for the real conversation with the assistant, not a tidied
narrative. The tool used here does not expose an export button, so this file separates
what can be quoted verbatim from what cannot.

## Verbatim prompts (quoted, unedited)

These are the messages the user sent in this session, copied exactly, including typos
and spacing:

1. `https://github.com/Sathvikagutti/The-Relay  push the project into this github link`
2. `https://drive.google.com/drive/u/0/folders/1A3jHjks7wZHlgU9E78GakHlXtuiFxnnJ    upload the project into this drive link`
3. `I connected Google Drive. Go ahead.`
4. `you resolve the bugs`
5. `yes continue to make changes`
6. The long correction brief beginning `THE RELAY — COMPLETE PROJECT CORRECTION AND IMPROVEMENT PROMPT`,
   which lists Phases 1–14. It is reproduced in full in `docs/AUDIT.md` §5 as a
   requirement table, because quoting 4,000 words twice would help nobody; the table
   keeps every requirement it contains.
7. The final review request beginning `Review my entire **The Relay — Vaani ML Engineering Intern assignment** repository`,
   whose ten completion items map to §5 and §6 of this file.

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

## What is the user's own work

The assignment decisions the user set and this session implemented: the pinned paper
versions, the token-budget admission rule, verify-before-reveal, and the requirement to
label every stand-in row. What the assistant contributed: the implementation, the
measurements, and the wording of the documents. Where the two disagree, the user's
instruction stands — for example the decision to keep BM25 instead of adding a vector
store.
