# How answers are graded

The brief forbids an LLM judge, so grading is either a mechanical check against a
region a human chose, or a human reading the answer next to that region. No model
decides whether an answer is good.

## The question set

`eval/questions.yaml` holds 20 questions, four per bucket:

| Bucket | What it probes |
| --- | --- |
| A. Single-paper fact | One paper, one section, answer is stated explicitly |
| B. Cross-section synthesis | Two sections of one paper must be combined |
| C. Multi-paper | Answer needs at least two of the three pinned papers |
| D. Not in the papers | Plausible-sounding question the corpus cannot answer |
| E. Adversarial / bait | Near-miss wording, wrong premise, or a real term from another paper |

Each question carries `gold`: the paper id plus a distinctive phrase from the passage a
human would cite, or `null` for unanswerable questions. Bucket D and E questions are the
ones that punish a retriever that always returns something.

## The four grades

| Grade | Meaning |
| --- | --- |
| `correct` | Answer is right *and* the citation resolves to a chunk overlapping the gold region |
| `wrong` | Answer is asserted confidently but is wrong, unsupported, or cites the wrong region |
| `refused_correctly` | Question is unanswerable from the corpus and the system said so |
| `refused_wrongly` | Question is answerable and the system refused, or refused for the wrong reason |

Refusing an unanswerable question is a success, not a non-answer. That is why
`refused_correctly` is a first-class outcome in `results.csv` rather than a blank.

## Automatic grading (all load rows)

`relay.grading.auto_grade` compares the cited chunk with the gold region:

* unanswerable question + refusal -> `refused_correctly`
* unanswerable question + answer -> `wrong`
* answerable question + refusal -> `refused_wrongly`
* answerable question + citation overlapping a gold chunk -> `correct`
* answerable question + any other citation -> `wrong`

This is a citation-location check. It is deliberately conservative: a right answer
citing a neighbouring chunk scores `wrong`. It cannot detect a fluent answer that cites
the right chunk but misstates it, which is exactly why Table 3 uses reviewed grades.

## Reviewed grades (Table 3)

`eval/manual_grades.csv` lists every evaluation row with its `request_id`, retrieval
setting, the automatic grade and an empty `final_grade`. Each row is read once against
the `reference` answer in `eval/questions.yaml` and gets a `final_grade`;
`relay tables` prefers that column whenever it is present and says in the footnote
whether the grades are reviewed or automatic - they are never silently blended. At
submission time the column is still empty, so Table 3 is labelled automatic.
