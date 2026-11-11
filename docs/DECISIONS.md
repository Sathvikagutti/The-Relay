# Decisions and the evidence behind them

Each entry states the decision, the alternative I rejected, and what would change my mind.
Numbers quoted here come from the artefacts in `results/`; regenerate them with
`relay combine && relay tables`.

## D1. Admission control on tokens, not retries on 429

`openai/gpt-oss-120b` on the free tier allows 8,000 tokens per minute but 30 requests
per minute (documented, `results/limits.json`). A measured evaluation answer costs 2,406
tokens (1,662 in, 745 out), so 8,000 TPM buys about three answers a minute while 30 RPM
would allow thirty: the token ceiling binds about nine times earlier than the request
ceiling. So the scheduler estimates tokens *before* sending, holds work in a
bounded queue, and fails fast only when the queue or the day budget is exhausted.

Rejected: retry-on-429 as the primary policy. It converts a known budget into
avoidable failed requests, and each failed request still costs a round trip and a
`retry-after` wait. Retries remain, but only as the last line of defence (D6).

## D2. Two model calls per answer, not one

Call one decides answerable/not and names the passages; call two writes the answer
against only those passages. One call is cheaper, but it lets the model invent a
citation that the verifier then has to reject, wasting the whole request. Splitting
means the cheap call can refuse early, which is the behaviour the brief cares about.

## D3. Citations are verified before the answer is revealed

The model returns `paper`, `page`, `section` and a verbatim quote. The page and section
are overwritten from chunk metadata - the model never gets to choose them. The quote is
matched after alphanumeric normalisation (pypdf splits words like `T ext`), as a
substring of the cited chunk. A failed check triggers at most two repairs, then a
refusal. This is why a "wrong but confident" answer cannot reach the user.

## D4. Provider TTFT and user-perceived TTFT are reported separately

`first_token_ms` in `results.csv` is measured from the moment the provider returns its
first streamed token. Time spent queueing, retrying or verifying is *not* included
there - it is in `total_ms`. Reporting only one number would either flatter the
pipeline (provider view) or hide that the first token is not the answer (user view).
`total_ms` is what a user experiences, so Table 2a leads with it.

## D5. BM25 over headings and body, not a vector store

Section headings are indexed with their chunks. Five gate queries were checked by
hand; the passage a human would cite is in the top four for 9 of 13 answerable
questions without any embedding model, and one miss is a genuine cross-paper collision
worth reporting. A vector index would add a model download, a build step and a new
failure mode for a corpus of 349 chunks.

## D6. The circuit breaker ignores 429s

Observed during the first full evaluation run: the stand-in returned 429 for a burst,
the breaker counted five of them as failures, opened for 20 seconds, and 13 requests
failed instantly with `error` instead of waiting. A 429 says the provider is healthy
and busy. Only 5xx and timeouts now count toward the breaker. Backoff also takes the
larger of jitter and the provider's `retry-after`, because retrying 300 ms into a
60-second window just burns a request.

## D7. Load rows are graded mechanically; quality claims use human grades

Every row in `results.csv` has an `answer_grade`, so the file is self-describing. Load
rows are graded by a gold-region check (does the cited chunk overlap the region a human
identified as answering the question). That check is honest about what it is: it cannot
tell a fluent wrong answer from a right one. Table 3's quality percentages therefore use
`final_grade` from `eval/manual_grades.csv` when it is filled, and otherwise say in the
table and its footnote that they are automatic. The sheet is still blank at submission,
so the table is labelled automatic and reports how many rows a human has reviewed.

## D8. The stand-in is a calibrated stand-in, never a claim about Groq

`services/standin/` enforces the documented limits with real counters and produces
OpenAI-compatible SSE, so the client code is identical for both sources. Its latency
parameters are fitted from real measurements by `relay calibrate`. Where it cannot
match - cold starts, prefill scaling with prompt length, unknown provider queue depth -
the differences are listed in `services/standin/params.json` and in the report. Load
results are labelled `stand-in` in the `source` column and never presented as
provider benchmarks.
