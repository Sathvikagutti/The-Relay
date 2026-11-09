# Interview questions I expect, and the answers I would give

**Why two model calls per answer?**
The first call is cheap and decides whether the corpus can answer at all; the second
writes only against the passages the first one named. With an 8k-token minute, one call
that both decides and writes costs the same as two, but a wrong citation then wastes the
entire request. Splitting lets refusal happen before the expensive part.

**Your limiter is in the client. Isn't that the wrong place?**
It is the only place I control, and it is where the economics live: I know what a request
will cost before I send it. The server is still the authority - I honour its 429 and
`retry-after`. The client limiter exists to avoid generating those 429s in the first place.

**What happens when the queue is full?**
The request is rejected with a `retry-after` hint and `status=rate_limited`. I chose a
bounded queue because an unbounded one does not create capacity; it only makes people wait
longer to be told the same thing. The cost is that some work is shed early, and Table 2b
shows exactly how much.

**How do you know the citation is real?**
The model returns a quote; I normalise it (strip punctuation, collapse whitespace, merge
pypdf's split letters) and require it to be a substring of the chunk it cites. Page and
section come from the chunk metadata, never from the model. If the check fails twice, the
system refuses instead of shipping an unsupported answer.

**Why not an LLM judge for quality?**
Because the brief forbids it, and because a judge that shares a model family with the
answerer agrees with itself. My automatic check is narrower and more honest: it grades the
citation location, and it explicitly cannot detect a fluent answer that cites the right
chunk and misstates it. Those rows go to the reviewed sheet.

**Your stand-in is fake. How is that useful?**
The load tests need to cross limits thousands of times; doing that against a free tier
would take days and would still only produce one sample of each 429. The stand-in enforces
the documented counters, streams the same SSE shape, and its latency is fitted from real
measurements. Everything it cannot reproduce is listed in `params.json`. I never present
stand-in numbers as provider benchmarks - the `source` column is in every row.

**Where does the stand-in differ most from the real service?**
Cold starts and long prompts. Real TTFT grows with prefill length; the stand-in's does
not. Real concurrency queues at unknown depth; the stand-in approximates it with a linear
slowdown. Rate-limit counters match, and that is the part the load tests depend on.

**What would you do with a bigger budget?**
Move to a paid tier and re-run the same harness with the client limiter raised, to check
that the scheduler's behaviour - not the tier - is what produces the latency curve. Then
add a reranker only if Table 3 shows retrieval, not generation, is the weak link.

**What is the biggest weakness of this submission?**
Bucket C (multi-paper synthesis) is the weakest: BM25 retrieves from one paper at a time
and the pipeline does not enforce that a multi-paper answer cites more than one paper.
The fix is a coverage constraint on the citation set, not a better retriever.

**How would you know the system got worse after a change?**
`relay eval` on the frozen 20 questions, then `relay tables`: correct-and-cited percentage
per setting, plus token cost per answer. The question set and gold regions are versioned,
so the comparison is like-for-like. The load harness catches the other regression class -
latency and shedding - separately.
