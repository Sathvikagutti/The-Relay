# How I worked with the assistant

Short and honest: what I decided, what the assistant did, and where I had to correct it.
This is the material for the report's final section.

## Shape of the work

1. **I asked for a plan before any code.** The plan was reviewed against the brief first,
   because the expensive mistakes in this assignment are architectural (what to measure,
   what to simulate) rather than syntactic.
2. **Ten stages, one gate each.** Corpus pinning, extraction/chunking, retrieval, pipeline,
   stand-in, limits probe, evaluation, load, tables, write-up. A stage was not "done" until
   its check passed - e.g. all three PDF hashes matched before a single chunk was indexed.
3. **Every number came from a file.** No figure was estimated in prose and then "confirmed"
   later; the tables are generated from `results/results.csv` by `relay tables`.

## Where the assistant was useful

* Scaffolding the pipeline quickly once the decisions were fixed, and keeping the same
  provider interface for the real service and the stand-in so the client code is identical.
* Catching a real design bug: the circuit breaker was counting 429s as failures, so a
  burst opened the circuit for 20 s and turned a wait into an outage. That was visible in
  the first full evaluation run (13 requests failed in milliseconds) and is now a decision
  entry, D6.
* Writing the token-budget admission control instead of a naive retry loop, which is the
  difference between shedding load early and burning the daily budget on retries.

## Where I corrected it

* It initially wrote eval rows twice (once ungraded by the pipeline, once graded by the
  runner). Fixed by grading inside the run, before the row is written.
* It assumed `PipelineConfig` owned the queue's concurrency knobs, and the first load run
  died on that assumption after three minutes. Fixed, then re-run from scratch.
* Its first queue test encoded the wrong semantics (admission cap vs waiting cap), which
  exposed that the queue was bounding total admission rather than the queue itself. Both
  the code and the test changed.

## What is mine, and what is not

The decisions (two calls, verify-before-reveal, token admission, calibrated stand-in,
mechanical grading) and their trade-offs are mine. The code was written with the assistant
against a plan I approved; the failing-first evidence for each decision is in `results/`
and `docs/DECISIONS.md`.

## Honest gaps

* The real Groq key was not in `.env` for most of the build, so the probe, the real eval
  and the real load run are scripted but **not yet measured**. The report labels those
  cells `not measured` rather than filling them with stand-in numbers.
* Manual grading of the 20 questions is prepared (`eval/manual_grades.csv`, one row per
  evaluation request with an empty `final_grade`) but not signed off. Table 3 says which
  grades are reviewed and which are mechanical.
* Bucket C (multi-paper synthesis) is the weakest area; the pipeline does not require a
  multi-paper answer to cite more than one paper.
