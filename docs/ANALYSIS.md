# Refusal and failure analysis, from the logs

Every figure below comes from `results/results.csv` and the raw traces in
`results/raw/*.jsonl`, matched on `request_id`. Nothing here is estimated.

## 1. Refusals in the evaluation set

The set has 20 questions: 13 answerable from the three papers, 7 deliberately not
(`q14`–`q20`). Each runs under three retrieval settings, so there are 39 answerable
and 21 unanswerable results.

| Bucket | Rows | `correct` | `wrong` | `refused_correctly` | `refused_wrongly` |
| --- | --- | --- | --- | --- | --- |
| Answerable (13 x 3) | 39 | 14 | 25 | 0 | 0 |
| Not answerable (7 x 3) | 21 | 0 | 21 | **0** | 0 |

Per setting: A 5 correct / 15 wrong, B 4/16, C 5/15.

**What that means.** The system refused nothing. All 21 unanswerable rows came back
as answers, and every one was graded `wrong` because the citation check found no gold
region for a question that has no answer in the corpus. This is not a pipeline bug:
it is the stand-in model, which sets `answerable = bool(question)` in
`services/standin/sim.py:187` and therefore always answers. A real model is what makes
the refusal branch behave, which is why the 0% refusal rate in Table 3 must not be
used to choose a retrieval setting.

The refusal *logic* is exercised elsewhere and does work: `pytest tests/test_fault_behaviour.py`
drives `REFUSAL_NO_PASSAGE`, `REFUSAL_UNVERIFIED` and `limit_reply()` paths, and the
`daily_exhausted` scenario returns the verbatim budget message 12/12 times.

## 2. Sustained overload: why 87.5% were refused

240 requests offered at 60/min for 239.0 s.

| Outcome | Rows | Trace evidence |
| --- | --- | --- |
| `ok` | 30 | completed with a verified citation |
| `rate_limited` | 210 | `reason: rate_limited_minute`, **HTTP 429 on attempt 1**, no retry |

Every one of the 210 refusals is a provider 429, not a client-side decision: the
`calls` array shows `{"status": "rate_limited", "kind": "rate_limited_minute", "http": 429}`
and exactly one attempt each, because the provider's hint was longer than the request
deadline. Example request `bdff5cf53266` answered in 5.7 ms this way, at degradation
level 1 with 675 context tokens.

The trace records the status code, kind and timing but not the response body, so the
body was captured directly from the stand-in for this note (2026-11-10, `tpm=1`):

> Rate limit reached for openai/gpt-oss-120b on tokens per minute (TPM). Please try again in 60.0s.

That is the stand-in speaking, shaped like the provider's documented error, not a Groq
response — no real request has been made yet (`docs/AUDIT.md` §6).

So the refusal rate is arithmetic, not a bug. 30 answers in 239 s is **7.5 answers per
minute** against 60 offered, while the documented request ceiling is 30/min and never
binds. That is the token ceiling: at ~1,150 tokens per answer the 8,000 TPM window
admits roughly seven answers a minute. The bottleneck is exactly where the design
predicted it, and the sustained run is the first evidence that it holds for minutes,
not seconds.

Degradation during the run: the ladder engaged by itself — levels 0/1/2 on 5/176/59
of the 240 requests, with the first successful request at level 0 and 456 context
tokens — so even the requests that lost the race had already started cheaper.

## 3. Faulty scenario: what each category is

40 requests at 30/min with the stand-in injecting 15% server errors, 5% timeouts and
10% truncated streams.

| Final status | Rows | Cause in the trace |
| --- | --- | --- |
| `ok` | 12 | completed with a verified citation |
| `rate_limited` | 25 | provider 429 (TPM), one attempt |
| `error` | 2 | HTTP 500, one attempt each because the shared retry budget was already spent |
| `timeout` | 1 | provider never finished inside the 30 s deadline |

Call-level counts: 18 ok, 25 rate-limited, 2 error, 1 timeout. The two `error` rows ran
one attempt each rather than three: the retry budget is shared across the run, so by the
time they arrived there were no attempts left to spend. That is the cost of a global
retry budget - it protects the token ceiling and it gives up on late faults - and it is
why `docs/AUDIT.md` R12 records a controlled experiment where retrying is strictly worse.

Partial streams: the stand-in truncates 10% of streams. This run recorded no
parse-failure row, so the branch is not evidenced here; it is covered by
`tests/test_fault_behaviour.py`, and the earlier draft (before the harness fixes in
`docs/AUDIT.md` §7) contained one such row, `status=ok` with
`answer_grade=refused_wrongly`. The labelling rule is unchanged: `status` describes
whether the request completed, and a verified refusal is a completion, so those rows
show up in the grade column rather than as errors.

## 4. What the queue did under burst and halved limits

With the redundant semaphore removed (`docs/AUDIT.md` §7), the admission queue is the
only thing that bounds concurrency: 4 in-flight, 64 waiting.

| Scenario | Answered | Refused on budget | Deadline spent waiting | Peak waiting |
| --- | --- | --- | --- | --- |
| burst (30 at 600/min) | 5 | 16 | 9 | **19** |
| limit halved (22 at 25/min) | 11 | 0 | 11 | 5 |
| overload (45 at 60/min) | 6 | 39 | 0 | 1 |
| sustained (240 at 60/min) | 30 | 210 | 0 | 1 |

The two shapes are different failures. In `burst` and `limit_halved` a request can wait,
so some of them spend the full 30 s deadline and are recorded as `timeout`: the wait was
ours, not the provider's. In `overload` and `sustained` the limiter knows the wait cannot
fit the deadline and refuses immediately, so nothing queues and every refusal is
`rate_limited`. The halved run is the clearest case: zero instant refusals, half the
requests answered after waiting up to ~33 s, half timed out. Answering half slowly is the
better trade only if the deadline is acceptable; at 4/min with a 30 s deadline nothing
waits at all.

## 5. What these logs do not show

- No real Groq fault rates. The 15%/5%/10% injection is synthetic; a real failure
  frequency can only come from the probe and a longer real run.
- No real 429 recovery timing. `retry-after: 54.1s` is the stand-in's arithmetic from
  its own window, not a measurement of Groq's recovery.
- No user who received a *trimmed but correct* answer. Degradation trimmed context and
  skipped the analysis call, but every trimmed request either completed normally or
  was refused; see `docs/AUDIT.md` R10.
