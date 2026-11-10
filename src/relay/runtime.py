"""Assemble a runnable Relay from configuration.

Both the real service and the stand-in are addressed through the same provider
class, so a stand-in run exercises the identical transport, timing instrumentation
and error handling as a real run. The only thing that changes is the base URL.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from relay.config import PROJECT_ROOT, Settings, load_config, load_retrieval
from relay.corpus.chunk import ChunkingSpec
from relay.llm.groq import GroqProvider
from relay.obs.events import JsonlWriter
from relay.pipeline.engine import PipelineConfig, Relay
from relay.retrieval.index import load_index
from relay.scheduling.limiter import LimiterLimits, RollingLimiter
from relay.scheduling.queue import AdmissionQueue

# Published free-plan values for openai/gpt-oss-120b (docs read 2026-11-09).
# They are the *documented* limits; observed limits live in results/limits.json.
DOCUMENTED_LIMITS = LimiterLimits(rpm=30, tpm=8_000, rpd=1_000, tpd=200_000)


@dataclass
class Runtime:
    relay: Relay
    limiter: RollingLimiter
    queue: AdmissionQueue
    trace_path: Path
    source: str

    async def aclose(self) -> None:
        provider = self.relay.provider
        if hasattr(provider, "aclose"):
            await provider.aclose()

    def peak_queue(self) -> int:
        return self.queue.peak_waiting


def build_runtime(
    *,
    source: str,
    setting_name: str | None = None,
    limits: LimiterLimits | None = None,
    config: PipelineConfig | None = None,
    trace_name: str = "adhoc",
    truncate_trace: bool = False,
    max_inflight: int = 4,
    max_waiting: int = 32,
    budget_state: bool = True,
    model: str | None = None,
    top_k_override: int | None = None,
) -> Runtime:
    settings = Settings()
    corpus = load_config()
    retrieval = load_retrieval()
    name, setting = retrieval.setting(setting_name)
    spec = ChunkingSpec(setting.chunk_tokens, setting.overlap_tokens)
    index = load_index(corpus, spec)

    if source == "real":
        if not settings.groq_api_key or settings.groq_api_key.get_secret_value() in (
            "",
            "replace_me",
        ):
            raise SystemExit(
                "no GROQ_API_KEY in .env; add your free-tier key or use --source stand-in"
            )
        provider = GroqProvider(
            base_url=settings.groq_base_url,
            api_key=settings.groq_api_key.get_secret_value(),
            model=model or settings.groq_model,
        )
        resolved_model = model or settings.groq_model
    elif source == "stand-in":
        provider = GroqProvider(
            base_url=settings.standin_base_url,
            api_key="stand-in",
            model=model or settings.groq_model,
            read_timeout_s=30.0,
        )
        resolved_model = model or settings.groq_model
    else:
        raise SystemExit(f"unknown source {source!r}; use 'real' or 'stand-in'")

    trace_path = PROJECT_ROOT / "results" / "raw" / f"{trace_name}.jsonl"
    limiter = RollingLimiter(
        limits or DOCUMENTED_LIMITS,
        state_path=(PROJECT_ROOT / "results" / "budget_state.json") if budget_state else None,
    )
    queue = AdmissionQueue(max_inflight=max_inflight, max_waiting=max_waiting)
    relay = Relay(
        provider=provider,
        index=index,
        limiter=limiter,
        queue=queue,
        setting_name=name,
        fetch_k=setting.fetch_k,
        top_k=top_k_override or setting.top_k,
        model=resolved_model,
        source=source,
        config=config or PipelineConfig(),
        trace_writer=JsonlWriter(trace_path, truncate=truncate_trace),
    )
    return Runtime(relay=relay, limiter=limiter, queue=queue, trace_path=trace_path, source=source)
