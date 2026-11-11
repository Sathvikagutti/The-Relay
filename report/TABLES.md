# Tables generated from results.csv

Rows: 493. Source(s): real, stand-in.

## Table 1 - service limits

| Limit | Documented | Observed | How found | Confidence |
| --- | --- | --- | --- | --- |
| Requests per minute | 30 | 30 (429 body; 20 of 32 calls fit) | 32 concurrent minimal calls | measured |
| Tokens per minute | 8000 | 8000 | `x-ratelimit-limit-tokens` header | header |
| Requests per day | 1000 | 1000 | `x-ratelimit-limit-requests` header | header |
| Tokens per day | 200000 | not measured | would cost 200k tokens to reach | documented |
| Requests in flight | - | not measured | ramped concurrency until refusal | not measured |
| What happens when a limit is hit | - | HTTP 429, retry-after [2.0] s | captured 429 response | measured |
| Time until recovery | - | 3.0 s | polled every 2 s | measured |

First token on a small prompt: p50 525 ms, p95 714 ms over 10 calls with visible output.

## Table 2a - latency by scenario

| Scenario | Source | Requests | Answered | Duration (s) | Offered/min | TTFT p50 | TTFT p95 | TTFT p99 | Total p50 | Total p95 | Total p99 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| burst | stand-in | 30 | 5 | 3.0 | 600.0 | 162 | 328 | 359 | 1791 | 2419 | 2501 |
| daily_exhausted | stand-in | 12 | 0 | 11.0 | 60.0 | not measured | not measured | not measured | not measured | not measured | not measured |
| degraded | stand-in | 30 | 19 | 146.3 | 12.0 | 166 | 600 | 1012 | 1607 | 27327 | 30549 |
| faulty | stand-in | 40 | 12 | 92.0 | 30.0 | 142 | 874 | 937 | 1408 | 2342 | 2394 |
| limit_halved | stand-in | 22 | 11 | 69.0 | 25.0 | 93 | 325 | 358 | 25420 | 32859 | 33817 |
| overload | stand-in | 45 | 6 | 44.0 | 60.0 | 172 | 348 | 351 | 1574 | 1983 | 2032 |
| steady | stand-in | 14 | 14 | 196.6 | 4.0 | 175 | 744 | 1049 | 1583 | 2120 | 2164 |
| sustained | stand-in | 240 | 30 | 239.0 | 60.0 | 166 | 757 | 1035 | 1379 | 1834 | 1970 |

## Table 2b - reliability, retries, queue and cost

| Scenario | Succeeded | Rate-limited | Timed out or given up | Retries/request | Peak queue | Tokens out/answer | Cost/1000 answers |
| --- | --- | --- | --- | --- | --- | --- | --- |
| burst | 16.7% | 53.3% | 30.0% | 0.27 | 19 | 88 | $0.00 (free tier) |
| daily_exhausted | 0.0% | 100.0% | 0.0% | 0.00 | 1 | not measured | $0.00 (free tier) |
| degraded | 63.3% | 30.0% | 6.7% | 0.27 | 3 | 64 | $0.00 (free tier) |
| faulty | 30.0% | 62.5% | 7.5% | 0.20 | 1 | 67 | $0.00 (free tier) |
| limit_halved | 50.0% | 0.0% | 50.0% | 0.00 | 5 | 70 | $0.00 (free tier) |
| overload | 13.3% | 86.7% | 0.0% | 0.18 | 1 | 84 | $0.00 (free tier) |
| steady | 100.0% | 0.0% | 0.0% | 0.00 | 1 | 75 | $0.00 (free tier) |
| sustained | 12.5% | 87.5% | 0.0% | 0.03 | 1 | 65 | $0.00 (free tier) |

## Table 3 - retrieval settings, quality and cost

| Setting | Source | Piece size | Fetched | Re-rank | Questions | Correct and cited | Wrong | Refused correctly | Refused when answerable | Quotes verified | Tokens out/answer | TTFT p50 | TTFT p95 | Total p50 | Total p95 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | real | 350/60 | 4 | none | 20 | 15.0% | 25.0% | 30.0% | 30.0% | 100.0% | 745 | 912 | 2015 | 3761 | 58332 |
| B | stand-in | 700/100 | 4 | none | 20 | 20.0% | 80.0% | 0.0% | 0.0% | not measured | 80 | 168 | 585 | 1647 | 2455 |
| C | stand-in | 350/60 | 16 | cross_encoder | 20 | 25.0% | 75.0% | 0.0% | 0.0% | not measured | 81 | 221 | 824 | 1723 | 2505 |

Source: real, stand-in. Grades: automatic gold-region check, not human. Quotes verified is a separate axis - the share of quoted citations the `verify_quote` tool matched exactly against the retrieved chunk - and is never folded into the answer grade. Whether a verified quote points at the *right* passage is the other half of citation correctness; that judgement is made by hand in `eval/manual_grades.csv` (`citation_correct` column).

Table 2a latency covers successful requests only; refused and timed-out requests are counted in Table 2b, because a 7 ms refusal is not a 7 ms answer.

Peak queue is the load runner's `peak_waiting` gauge when the run wrote one, otherwise the maximum overlap of [start_time, start_time + total_ms] intervals computed from the CSV. A request waits when the in-flight slots are busy, so a scenario that offers traffic faster than four calls can drain shows a queue; one that is refused on the token budget before admission does not.

Cost is $0.00 because the free tier is not billed; no list price was paid, so no list-price figure is reported.
