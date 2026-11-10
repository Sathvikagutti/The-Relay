"""Pipeline orchestration: the six steps, the repair loop, the degradation ladder.

Branch and loop, explicitly:
  * branch - the query planner can refuse before any drafting call, which is the
    cheapest possible refusal (zero answer tokens);
  * loop   - a draft whose quotations fail verification is repaired at most twice,
    then refused. The loop never removes the verification requirement.
"""

from __future__ import annotations

import asyncio
import random
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from relay.corpus.chunk import estimate_tokens
from relay.llm.base import RATE_LIMITED_DAY, SERVER_ERROR, TIMEOUT, ChatRequest, ChatResult
from relay.models import Answer, Chunk
from relay.obs.events import JsonlWriter, Trace
from relay.pipeline import steps
from relay.pipeline.tools import TOOL_NAME, verify_citations
from relay.retrieval.index import ChunkIndex
from relay.retrieval.select import merge_hits, select_context
from relay.scheduling.breaker import CircuitBreaker, CircuitOpen
from relay.scheduling.limiter import DAY, MINUTE, LimitExceeded, RollingLimiter
from relay.scheduling.queue import AdmissionQueue, QueueFull
from relay.scheduling.retry import RETRYABLE, RetryBudget, RetryPolicy

REFUSAL_NO_PASSAGE = (
    "I could not find a passage in the three papers that answers this. "
    "I will not answer from memory, so I have nothing to cite."
)
REFUSAL_UNVERIFIED = (
    "I drafted an answer but could not verify its quotations against the papers, "
    "so I am not sending it. A wrong citation is worse than no answer here."
)


def limit_reply(kind: str, retry_after_s: float | None = None) -> str:
    """What a waiting person is told. This text is quoted verbatim in the report."""
    if kind == DAY:
        return (
            "I can't answer this one right now: today's free-tier model budget is spent. "
            "The account allows 200,000 tokens and 1,000 requests per day, shared with "
            "every other run, and it resets at the start of the next UTC day. "
            "No partial or guessed answer was sent. "
            "Retry after the reset, or narrow the question so it needs fewer passages."
        )
    wait = f"{retry_after_s:.0f} seconds" if retry_after_s else "a minute"
    return (
        f"I can't answer this one right now: the model service is at its per-minute limit. "
        f"It frees up in about {wait}. Nothing was lost - retry then. "
        "I have not sent a shorter, unverified answer just to stay fast."
    )


@dataclass(slots=True)
class PipelineConfig:
    deadline_ms: float = 30_000.0
    max_tokens_analysis: int = 160
    max_tokens_answer: int = 340
    context_token_budget: int = 1_500
    repair_attempts: int = 2
    max_attempts: int = 3
    max_limit_waits: int = 2


@dataclass(slots=True)
class Relay:
    provider: object
    index: ChunkIndex
    limiter: RollingLimiter
    queue: AdmissionQueue
    setting_name: str
    fetch_k: int
    top_k: int
    model: str
    source: str = "stand-in"
    breaker: CircuitBreaker = field(default_factory=CircuitBreaker)
    policy: RetryPolicy = field(default_factory=RetryPolicy)
    retry_budget: RetryBudget = field(default_factory=lambda: RetryBudget(RetryPolicy()))
    config: PipelineConfig = field(default_factory=PipelineConfig)
    trace_writer: JsonlWriter | None = None
    extra_query: dict[str, str] | None = None
    seed: int = 7
    _rng: random.Random | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        self._rng = random.Random(self.seed)
        if self.retry_budget is None:
            self.retry_budget = RetryBudget(self.policy)

    # ---- public ----------------------------------------------------------
    async def run(
        self,
        question: str,
        *,
        scenario: str = "adhoc",
        degrade: int | None = None,
        grader: Callable[[Answer], str] | None = None,
    ) -> tuple[Trace, Answer]:
        trace = Trace(
            scenario=scenario,
            source=self.source,
            retrieval_setting=self.setting_name,
            question=question,
        )
        level = self._auto_degrade() if degrade is None else degrade
        trace.notes["degrade_level"] = level
        run_started = time.perf_counter()
        waits = 0
        answer: Answer | None = None
        try:
            while True:
                queued_started = time.perf_counter()
                try:
                    async with self.queue.slot():
                        trace.queued_ms += (time.perf_counter() - queued_started) * 1000
                        answer = await self._answer(question, trace, level)
                    break
                except QueueFull as exc:
                    trace.status = "rate_limited"
                    trace.notes["reason"] = "queue_full"
                    answer = Answer(
                        "refused", limit_reply(MINUTE, exc.retry_after_s), reason="queue_full"
                    )
                    break
                except LimitExceeded as exc:
                    elapsed_ms = (time.perf_counter() - run_started) * 1000
                    wait_ms = exc.retry_after_s * 1000
                    hits = trace.notes.setdefault("limit_hits", [])
                    assert isinstance(hits, list)
                    hits.append({"kind": exc.kind, "retry_after_s": round(exc.retry_after_s, 1)})
                    # Waiting is only worth it if the answer can still arrive inside the
                    # deadline, and never for a daily cap - no wait inside one request
                    # brings tomorrow's budget back. Otherwise fail in the status that
                    # tells the truth: a timeout, not a rate limit we chose not to take.
                    can_wait = (
                        exc.kind != DAY
                        and waits < self.config.max_limit_waits
                        and elapsed_ms + wait_ms <= self.config.deadline_ms - 250
                    )
                    if can_wait:
                        waits += 1
                        trace.limit_wait_ms += wait_ms
                        trace.notes["limit_waits"] = waits
                        await asyncio.sleep(exc.retry_after_s)
                        continue
                    trace.status = "rate_limited" if exc.kind == DAY else "timeout"
                    trace.notes["reason"] = (
                        "budget_exhausted" if exc.kind == DAY else f"deadline_exceeded_{exc.kind}"
                    )
                    trace.notes["retry_after_s"] = round(exc.retry_after_s, 1)
                    answer = Answer(
                        "refused", limit_reply(exc.kind, exc.retry_after_s), reason=exc.kind
                    )
                    break
        except asyncio.CancelledError:
            trace.status = "timeout"
            trace.notes["reason"] = "cancelled"
            trace.finish()
            self._write(trace)
            raise
        finally:
            trace.finish()
        assert answer is not None
        # Grade every outcome, including limit/queue refusals: a request that was
        # never attempted is still a result the tables must account for.
        if grader is not None:
            trace.answer_grade = grader(answer)
        self._write(trace)
        return trace, answer

    # ---- steps -----------------------------------------------------------
    async def _answer(self, question: str, trace: Trace, level: int) -> Answer:
        queries = [question]
        if level < 1:
            result = await self._call(
                steps.build_analysis_messages(question),
                self.config.max_tokens_analysis,
                trace,
                "analyze",
            )
            if not result.ok:
                return self._failure(result, trace)
            analysis = steps.parse_analysis(result.text)
            trace.notes["analysis"] = {
                "answerable": analysis.answerable,
                "queries": list(analysis.queries),
                "needs_multi": analysis.needs_multi,
            }
            if not analysis.answerable:
                return Answer(
                    "refused",
                    "The three papers in this library do not cover that. "
                    "I only answer from Attention Is All You Need, Moshi, and Dynamic Chunking.",
                    reason="out_of_library",
                )
            if analysis.queries:
                queries = list(analysis.queries)

        hits = self._retrieve(queries, fetch_k=self.fetch_k)
        trace.notes["retrieved"] = [hit.chunk.chunk_id for hit in hits]
        if not hits:
            return Answer("refused", REFUSAL_NO_PASSAGE, reason="no_passage")

        wanted = self.top_k if level < 2 else max(1, self.top_k - 2)
        chunks = select_context(
            hits, token_budget=self.config.context_token_budget, top_k=wanted
        )
        trace.notes["context"] = [chunk.chunk_id for chunk in chunks]
        trace.notes["context_tokens"] = sum(chunk.est_tokens for chunk in chunks)

        result = await self._call(
            steps.build_draft_messages(question, chunks),
            self.config.max_tokens_answer,
            trace,
            "draft",
        )
        if not result.ok:
            return self._failure(result, trace)
        draft = steps.parse_draft(result.text)
        if draft is None:
            trace.notes["parse_error"] = True
            return Answer("refused", REFUSAL_UNVERIFIED, reason="unparseable_draft")
        if not draft.answerable:
            return Answer("refused", draft.answer or REFUSAL_NO_PASSAGE, reason="model_refused")

        by_id: dict[str, Chunk] = {chunk.chunk_id: chunk for chunk in chunks}
        citations, errors = verify_citations(draft.citations, by_id)
        self._log_tool(trace, draft, citations, errors)

        repairs = 0
        while errors and repairs < self.config.repair_attempts and level < 2:
            repairs += 1
            result = await self._call(
                steps.build_repair_messages(question, chunks, errors, draft.answer),
                self.config.max_tokens_answer,
                trace,
                f"repair_{repairs}",
            )
            if not result.ok:
                return self._failure(result, trace)
            repaired = steps.parse_draft(result.text)
            if repaired is None:
                break
            draft = repaired
            citations, errors = verify_citations(draft.citations, by_id)
            self._log_tool(trace, draft, citations, errors)

        trace.notes["repairs"] = repairs
        if errors:
            trace.notes["citation_errors"] = errors
            return Answer("refused", REFUSAL_UNVERIFIED, reason="unverified_citations")
        if not citations:
            return Answer("refused", REFUSAL_UNVERIFIED, reason="no_citations")
        return Answer("ok", draft.answer, tuple(citations))

    def _retrieve(self, queries: list[str], *, fetch_k: int):
        lists = [self.index.search(query, top_k=fetch_k) for query in queries if query.strip()]
        return merge_hits(lists)

    def _log_tool(self, trace: Trace, draft, citations, errors) -> None:
        trace.notes.setdefault("tool_calls", []).append(
            {
                "tool": TOOL_NAME,
                "requested": len(draft.citations),
                "verified": len(citations),
                "errors": errors[:4],
            }
        )

    # ---- provider call with budget, breaker and retry --------------------
    async def _call(
        self, messages: list[dict[str, str]], max_tokens: int, trace: Trace, label: str
    ) -> ChatResult:
        est_tokens = estimate_tokens("".join(m["content"] for m in messages)) + max_tokens
        for attempt in range(1, self.config.max_attempts + 1):
            remaining_ms = self.config.deadline_ms - (
                time.perf_counter() - trace.start_perf
            ) * 1000
            if remaining_ms <= 100:
                trace.status = "timeout"
                return ChatResult(status="timeout", error_kind="timeout", error="deadline")

            try:
                self.breaker.before_call()
            except CircuitOpen as exc:
                trace.status = "error"
                trace.notes["reason"] = "circuit_open"
                return ChatResult(
                    status="error",
                    error_kind="server_error",
                    error=str(exc),
                    retry_after_s=exc.retry_after_s,
                )

            acquire_started = time.perf_counter()
            reservation = await self.limiter.acquire(
                est_tokens, deadline_s=remaining_ms / 1000
            )
            # Budget waiting is its own bucket: without this the 50 s request in the
            # half-limits run looked like it spent 49 s nowhere at all.
            trace.limit_wait_ms += (time.perf_counter() - acquire_started) * 1000
            started = time.perf_counter()
            result = await self.provider.chat(
                ChatRequest(
                    messages=messages,
                    max_tokens=max_tokens,
                    model=self.model,
                    extra_query=self.extra_query,
                )
            )
            elapsed_ms = (time.perf_counter() - started) * 1000

            if result.ok:
                trace.working_ms += elapsed_ms
                trace.tokens_in += result.tokens_in
                trace.tokens_out += result.tokens_out
                if trace.ttft_ms is None and result.ttft_ms is not None:
                    trace.ttft_ms = result.ttft_ms
                self.breaker.record_success()
                self.retry_budget.record_success()
                await self.limiter.reconcile(reservation, result.tokens_in + result.tokens_out)
                trace.calls.append(
                    {
                        "label": label,
                        "attempt": attempt,
                        "status": "ok",
                        "ms": round(elapsed_ms, 1),
                        "ttft_ms": None if result.ttft_ms is None else round(result.ttft_ms, 1),
                        "tokens_in": result.tokens_in,
                        "tokens_out": result.tokens_out,
                    }
                )
                return result

            trace.retrying_ms += elapsed_ms
            used = result.tokens_in + result.tokens_out
            if used:
                await self.limiter.reconcile(reservation, used)
            else:
                self.limiter.release(reservation)
            trace.calls.append(
                {
                    "label": label,
                    "attempt": attempt,
                    "status": result.status,
                    "kind": result.error_kind,
                    "ms": round(elapsed_ms, 1),
                    "http": result.http_status,
                }
            )

            retryable = result.error_kind in RETRYABLE
            can_retry = (
                retryable
                and attempt < self.config.max_attempts
                and self.retry_budget.spend()
            )
            if not can_retry:
                return result
            # Only genuine provider failures trip the breaker. A 429 means the
            # provider is healthy and busy; counting it as a failure opened the
            # circuit for 20 s during a burst and turned a wait into an outage.
            if result.error_kind in (SERVER_ERROR, TIMEOUT):
                self.breaker.record_failure()
            delay_ms = self.policy.delay_ms(attempt, self._rng)
            if result.retry_after_s:
                # Re-sending before the provider's own hint burns requests for nothing.
                delay_ms = max(delay_ms, result.retry_after_s * 1000)
            trace.backoff_ms += delay_ms
            trace.retries += 1
            budget_left_ms = self.config.deadline_ms - (
                time.perf_counter() - trace.start_perf
            ) * 1000
            if delay_ms >= budget_left_ms:
                return result
            await asyncio.sleep(delay_ms / 1000)
        return ChatResult(status="error", error_kind="server_error", error="attempts exhausted")

    # ---- helpers ---------------------------------------------------------
    def _auto_degrade(self) -> int:
        """Trim work when the minute budget is nearly spent (see report, §5)."""
        limits = self.limiter.limits
        if not limits.tpm:
            return 0
        _, used = self.limiter.minute_usage()
        if used >= 0.8 * limits.tpm:
            return 2
        if used >= 0.55 * limits.tpm:
            return 1
        return 0

    def _failure(self, result: ChatResult, trace: Trace) -> Answer:
        if result.error_kind == RATE_LIMITED_DAY:
            trace.status = "rate_limited"
            kind = DAY
        elif result.status == "rate_limited":
            trace.status = "rate_limited"
            kind = MINUTE
        elif result.status == "timeout":
            trace.status = "timeout"
            kind = MINUTE
        else:
            trace.status = "error"
            kind = MINUTE
        trace.notes["reason"] = result.error_kind or result.status
        trace.notes.setdefault("errors", []).append((result.error or "")[:200])
        if trace.status == "error":
            return Answer(
                "refused",
                "Something went wrong on the model side and I could not produce a verified "
                "answer. I would rather fail than guess; please retry.",
                reason="provider_error",
            )
        return Answer("refused", limit_reply(kind, result.retry_after_s), reason=trace.status)

    def _write(self, trace: Trace) -> None:
        if self.trace_writer is not None:
            self.trace_writer.append(trace.to_dict())
