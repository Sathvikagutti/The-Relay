# Tables generated from results.csv

Rows: 183. Source(s): stand-in.

## Table 1 - service limits

| Limit | Documented | Observed | Evidence |
| --- | --- | --- | --- |
| Requests per minute | 30 | not measured | `relay probe-limits` needs GROQ_API_KEY |
| Requests per day | 1000 | not measured | header value only |
| Tokens per minute | 8000 | not measured | header value only |
| Tokens per day | 200000 | not measured | docs only |
| 429 body + retry-after | - | not measured | `relay probe-limits` needs GROQ_API_KEY |
| TTFT (small prompt) | - | not measured | `relay probe-limits` needs GROQ_API_KEY |

## Table 2a - latency by scenario

| Scenario | Requests | TTFT p50 | TTFT p95 | TTFT p99 | Total p50 | Total p95 | Total p99 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| burst | 30 | 140 | 1598 | 2159 | 7 | 13254 | 13982 |
| daily_exhausted | 12 | not measured | not measured | not measured | 0 | 0 | 0 |
| limit_halved | 22 | 225 | 751 | 903 | 3856 | 39358 | 48115 |
| overload | 45 | 231 | 347 | 358 | 9 | 11542 | 12846 |
| steady | 14 | 192 | 381 | 420 | 1494 | 2099 | 2195 |

## Table 2b - reliability, retries, queue and cost

| Scenario | Succeeded | Rate-limited | Timed out or given up | Retries/request | Peak queue | Tokens out/answer | Cost/1000 answers |
| --- | --- | --- | --- | --- | --- | --- | --- |
| burst | 3% | 97% | 0% | 0.27 | 11 | 78 | $0.00 (free tier) |
| daily_exhausted | 0% | 100% | 0% | 0.00 | 1 | not measured | $0.00 (free tier) |
| limit_halved | 45% | 36% | 18% | 0.36 | 4 | 67 | $0.00 (free tier) |
| overload | 7% | 93% | 0% | 0.18 | 8 | 82 | $0.00 (free tier) |
| steady | 100% | 0% | 0% | 0.00 | 1 | 75 | $0.00 (free tier) |

## Table 3 - retrieval settings, quality and cost

| Setting | Questions | Correct and cited | Wrong | Refused correctly | Refused when answerable | Tokens out/answer | TTFT p50 | TTFT p95 | Total p50 | Total p95 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | 20 | 25% | 75% | 0% | 0% | 81 | 167 | 591 | 1680 | 2368 |
| B | 20 | 20% | 80% | 0% | 0% | 80 | 168 | 585 | 1647 | 2455 |
| C | 20 | 25% | 75% | 0% | 0% | 81 | 221 | 824 | 1723 | 2505 |

Source: stand-in. Grades: automatic gold-region check, not human.

Peak queue = maximum overlap of [start_time, start_time + total_ms] intervals, computed from the CSV.
Cost is $0.00 because the free tier is not billed; no list price was paid, so no list-price figure is reported.
