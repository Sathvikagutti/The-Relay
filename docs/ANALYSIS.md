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
deadline. Example request `d87dcc93d942`, with the provider body recorded verbatim in
the trace:

> Rate limit reached for openai/gpt-oss-120b on tokens per minute (TPM). Please try again in 54.1s.

So the refusal rate is arithmetic, not a bug. 30 answers in 239 s is **7.5 answers per
minute** against 60 offered, while the documented request ceiling is 30/min and never
binds. That is the token ceiling: at ~1,150 tokens per answer the 8,000 TPM window
admits roughly seven answers a minute. The bottleneck is exactly where the design
predicted it, and the sustained run is the first evidence that it holds for minutes,
not seconds.

Degradation during the run: the ladder engaged by itself (level 1 on the example
above, 675 context tokens, analysis call skipped), so even the requests that lost the
race had already started cheaper.

## 3. Faulty scenario: what each category is

40 requests at 30/min with the stand-in injecting 15% server errors, 5% timeouts and
10% truncated streams.

| Final status | Rows | Cause in the trace |
| --- | --- | --- |
| `ok` | 9 | completed |
| `rate_limited` | 25 | provider 429 (TPM), one attempt |
| `error` | 5 | three attempts, each HTTP 500 `internal server error (simulated)` |
| `timeout` | 1 | provider never finished inside the 30 s deadline |

Call-level counts: 25 ok, 28 rate-limited, 10 error, 1 timeout. The 5 `error` rows
produced 10+ error calls because the retry budget spent its attempts before failing —
that is the honest cost of retrying a 500, and it is why `docs/AUDIT.md` R12 records a
controlled experiment where retrying is strictly worse.

Partial streams: the stand-in truncates 10% of streams. One request (`f6122ece34b7`)
hit the truncation, failed to parse the draft, and returned `REFUSAL_UNVERIFIED`
("I drafted an answer but could not verify its quotations..."). **Labelling caveat:**
that row carries `status=ok` with `answer_grade=refused_wrongly`, because `status`
describes whether the request completed, and a verified refusal is a completion. It is
the only such row out of 138 `ok` rows, and it is visible in the grade column.

## 4. What these logs do not show

- No real Groq fault rates. The 15%/5%/10% injection is synthetic; a real failure
  frequency can only come from the probe and a longer real run.
- No real 429 recovery timing. `retry-after: 54.1s` is the stand-in's arithmetic from
  its own window, not a measurement of Groq's recovery.
- No user who received a *trimmed but correct* answer. Degradation trimmed context and
  skipped the analysis call, but every trimmed request either completed normally or
  was refused; see `docs/AUDIT.md` R10.
