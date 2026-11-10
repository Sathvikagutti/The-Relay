# Tables generated from results.csv

Rows: 493. Source(s): stand-in.

## Table 1 - service limits

| Limit | Documented | Observed | How found | Confidence |
| --- | --- | --- | --- | --- |
| Requests per minute | 30 | not measured | documented value only; `relay probe-limits` not run (no API key) | documented |
| Tokens per minute | 8000 | not measured | documented value only; `relay probe-limits` not run (no API key) | documented |
| Requests per day | 1000 | not measured | documented value only; `relay probe-limits` not run (no API key) | documented |
| Tokens per day | 200000 | not measured | documented value only; `relay probe-limits` not run (no API key) | documented |
| Requests in flight | - | not measured | documented value only; `relay probe-limits` not run (no API key) | not measured |
| What happens when a limit is hit | - | not measured | documented value only; `relay probe-limits` not run (no API key) | not measured |
| Time until recovery | - | not measured | documented value only; `relay probe-limits` not run (no API key) | not measured |

Values in the Documented column are from console.groq.com/docs/rate-limits for `openai/gpt-oss-120b`, read 2026-11-09.

## Table 2a - latency by scenario

| Scenario | Source | Requests | Answered | Duration (s) | Offered/min | TTFT p50 | TTFT p95 | TTFT p99 | Total p50 | Total p95 | Total p99 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| burst | stand-in | 30 | 1 | 15.1 | 600.0 | 183 | 183 | 183 | 14243 | 14243 | 14243 |
| daily_exhausted | stand-in | 12 | 0 | 11.0 | 60.0 | not measured | not measured | not measured | not measured | not measured | not measured |
| degraded | stand-in | 30 | 12 | 175.0 | 12.0 | 210 | 439 | 556 | 1200 | 14546 | 23381 |
| faulty | stand-in | 40 | 9 | 80.3 | 30.0 | 187 | 734 | 968 | 1574 | 3157 | 3602 |
| limit_halved | stand-in | 22 | 9 | 90.0 | 25.0 | 392 | 1203 | 1409 | 2485 | 30871 | 31640 |
| overload | stand-in | 45 | 3 | 44.8 | 60.0 | 270 | 352 | 359 | 1779 | 11623 | 12498 |
| steady | stand-in | 14 | 14 | 196.4 | 4.0 | 192 | 381 | 420 | 1494 | 2099 | 2195 |
| sustained | stand-in | 240 | 30 | 239.0 | 60.0 | 188 | 753 | 1029 | 1205 | 1681 | 1905 |

## Table 2b - reliability, retries, queue and cost

| Scenario | Succeeded | Rate-limited | Timed out or given up | Retries/request | Peak queue | Tokens out/answer | Cost/1000 answers |
| --- | --- | --- | --- | --- | --- | --- | --- |
| burst | 3.3% | 96.7% | 0.0% | 0.27 | 1 | 78 | $0.00 (free tier) |
| daily_exhausted | 0.0% | 100.0% | 0.0% | 0.00 | 1 | not measured | $0.00 (free tier) |
| degraded | 40.0% | 43.3% | 16.7% | 0.27 | 1 | 66 | $0.00 (free tier) |
| faulty | 22.5% | 62.5% | 15.0% | 0.20 | 1 | 66 | $0.00 (free tier) |
| limit_halved | 40.9% | 0.0% | 59.1% | 0.18 | 1 | 69 | $0.00 (free tier) |
| overload | 6.7% | 93.3% | 0.0% | 0.18 | 1 | 82 | $0.00 (free tier) |
| steady | 100.0% | 0.0% | 0.0% | 0.00 | 1 | 75 | $0.00 (free tier) |
| sustained | 12.5% | 87.5% | 0.0% | 0.03 | 1 | 66 | $0.00 (free tier) |

## Table 3 - retrieval settings, quality and cost

| Setting | Piece size | Fetched | Re-rank | Questions | Correct and cited | Wrong | Refused correctly | Refused when answerable | Quotes verified | Tokens out/answer | TTFT p50 | TTFT p95 | Total p50 | Total p95 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | 350/60 | 4 | none | 20 | 25.0% | 75.0% | 0.0% | 0.0% | 100.0% | 81 | 167 | 591 | 1680 | 2368 |
| B | 700/100 | 4 | none | 20 | 20.0% | 80.0% | 0.0% | 0.0% | 100.0% | 80 | 168 | 585 | 1647 | 2455 |
| C | 350/60 | 16 | cross_encoder | 20 | 25.0% | 75.0% | 0.0% | 0.0% | 100.0% | 81 | 221 | 824 | 1723 | 2505 |

Source: stand-in. Grades: automatic gold-region check, not human. Quotes verified is a separate axis - the share of quoted citations the `verify_quote` tool matched exactly against the retrieved chunk - and is never folded into the answer grade. Whether a verified quote points at the *right* passage is the other half of citation correctness; that judgement is made by hand in `eval/manual_grades.csv` (`citation_correct` column).

Table 2a latency covers successful requests only; refused and timed-out requests are counted in Table 2b, because a 7 ms refusal is not a 7 ms answer.

Peak queue is the load runner's `peak_waiting` gauge when the run wrote one, otherwise the maximum overlap of [start_time, start_time + total_ms] intervals computed from the CSV. It stays at 1 in the shedding scenarios because a request refused by the limiter is rejected before it is admitted, so it never waits.

Cost is $0.00 because the free tier is not billed; no list price was paid, so no list-price figure is reported.
