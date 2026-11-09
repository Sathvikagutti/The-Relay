"""Find out how the real service actually behaves, with a small number of calls.

Budget for one full probe: about 45 requests and ~12k tokens. That is affordable
on a 1,000 RPD / 200,000 TPD free tier, and it is deliberately not repeated.

What it measures, and how:
  * documented limits   - transcribed from the docs page (not guessed)
  * observed limits     - x-ratelimit-limit-requests (RPD) / -tokens (TPM) headers
  * RPM                 - 32 concurrent minimal calls: RPM is not in any header,
                          so the only way to learn it is to cross it
  * TPM                 - two concurrent ~4.5k-token prompts
  * 429 shape           - status, body message, retry-after
  * recovery            - poll until a request succeeds again
  * TTFT / total        - 10 paced minimal calls

Across-the-wire failures are recorded as data, not exceptions: a probe that dies on
the first 429 would learn nothing about the limit it just hit.
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from relay.config import PROJECT_ROOT, Settings
from relay.llm.base import ChatRequest, ChatResult
from relay.llm.groq import GroqProvider
from relay.obs.events import percentile

OUT_DIR = PROJECT_ROOT / "results"
RAW_DIR = OUT_DIR / "raw"

DOCUMENTED = {
    "source_url": "https://console.groq.com/docs/rate-limits",
    "read_on": "2026-11-09",
    "plan": "free",
    "model": "openai/gpt-oss-120b",
    "rpm": 30,
    "rpd": 1000,
    "tpm": 8000,
    "tpd": 200000,
    "note": "Free Plan table; limits apply per organisation, not per key.",
}

SMALL = [{"role": "user", "content": "Reply with the single word: ok"}]


async def _one(provider: GroqProvider, max_tokens: int = 6, prompt: str | None = None) -> ChatResult:
    messages = [{"role": "user", "content": prompt}] if prompt else SMALL
    return await provider.chat(ChatRequest(messages=messages, max_tokens=max_tokens))


async def probe(provider: GroqProvider, *, raw_path: Path) -> dict[str, object]:
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text("", encoding="utf-8")

    def record(kind: str, result: ChatResult, extra: dict[str, object] | None = None) -> None:
        with raw_path.open("a", encoding="utf-8") as fh:
            fh.write(
                json.dumps(
                    {
                        "probe": kind,
                        "at": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
                        "status": result.status,
                        "kind": result.error_kind,
                        "http": result.http_status,
                        "ttft_ms": result.ttft_ms,
                        "total_ms": result.total_ms,
                        "retry_after_s": result.retry_after_s,
                        "tokens_in": result.tokens_in,
                        "tokens_out": result.tokens_out,
                        "headers": result.headers,
                        "error": (result.error or "")[:200],
                        **(extra or {}),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

    report: dict[str, object] = {"documented": DOCUMENTED, "measured_at": datetime.now(timezone.utc).isoformat()}

    models = await provider.list_models()
    report["models_available"] = models
    report["target_model_present"] = provider.model in models

    # 1. paced latency sample: the distribution, not a single lucky call
    latency: list[ChatResult] = []
    for _ in range(10):
        result = await _one(provider)
        record("latency", result)
        latency.append(result)
        await asyncio.sleep(1.2)
    ok = [item for item in latency if item.ok]
    report["latency"] = {
        "sample": len(latency),
        "ok": len(ok),
        "ttft_p50_ms": percentile([item.ttft_ms or 0 for item in ok], 50),
        "ttft_p95_ms": percentile([item.ttft_ms or 0 for item in ok], 95),
        "total_p50_ms": percentile([item.total_ms for item in ok], 50),
        "total_p95_ms": percentile([item.total_ms for item in ok], 95),
        "tokens_out_p50": percentile([float(item.tokens_out) for item in ok], 50),
    }
    header_sample = next((item.headers for item in latency if item.headers), {})
    report["observed_from_headers"] = {
        "rpd": _as_int(header_sample.get("x-ratelimit-limit-requests")),
        "tpm": _as_int(header_sample.get("x-ratelimit-limit-tokens")),
        "headers": header_sample,
    }

    # 2. RPM: cross it on purpose with minimal payloads
    started = time.perf_counter()
    burst = await asyncio.gather(*(_one(provider, max_tokens=4) for _ in range(32)))
    burst_s = time.perf_counter() - started
    for result in burst:
        record("rpm_burst", result)
    limited = [item for item in burst if item.status == "rate_limited"]
    report["rpm_probe"] = {
        "requests": len(burst),
        "concurrent": 32,
        "duration_s": round(burst_s, 2),
        "ok": sum(1 for item in burst if item.ok),
        "rate_limited": len(limited),
        "only_exceeded_at": len(burst) - len(limited),
        "retry_after_s": sorted({item.retry_after_s for item in limited if item.retry_after_s}),
        "sample_body": next((item.error for item in limited if item.error), None),
    }

    # 3. TPM: two large prompts in the same window
    filler = " ".join(["transformer attention sequence model"] * 700)  # ~4.5k tokens
    big = await asyncio.gather(
        _one(provider, max_tokens=16, prompt=f"Summarise in one word. {filler}"),
        _one(provider, max_tokens=16, prompt=f"Summarise in one word. {filler}"),
    )
    for result in big:
        record("tpm_probe", result)
    report["tpm_probe"] = {
        "requests": 2,
        "ok": sum(1 for item in big if item.ok),
        "rate_limited": sum(1 for item in big if item.status == "rate_limited"),
        "prompt_tokens": [item.tokens_in for item in big],
        "sample_body": next((item.error for item in big if item.error), None),
        "retry_after_s": [item.retry_after_s for item in big],
    }

    # 4. recovery: how long until the window frees
    recovery_started = time.perf_counter()
    attempts = 0
    recovered_after: float | None = None
    while attempts < 40:
        attempts += 1
        result = await _one(provider, max_tokens=4)
        record("recovery", result, {"attempt": attempts})
        if result.ok:
            recovered_after = time.perf_counter() - recovery_started
            break
        await asyncio.sleep(2.0)
    report["recovery"] = {
        "seconds": None if recovered_after is None else round(recovered_after, 1),
        "attempts": attempts,
        "note": "polling every 2s after the burst; None means no recovery within 80s",
    }
    report["not_measured"] = {
        "rpd": "would require exhausting 1,000 requests in a day; header value used instead",
        "tpd": "would require spending 200,000 tokens; documented value only",
        "max_in_flight": "not exposed; inferred from RPM/TPM, never observed directly",
    }
    return report


def _as_int(value: str | None) -> int | None:
    try:
        return int(value) if value is not None else None
    except ValueError:
        return None


async def main() -> int:
    settings = Settings()
    key = settings.groq_api_key.get_secret_value() if settings.groq_api_key else ""
    if not key or key == "replace_me":
        print("no GROQ_API_KEY in .env - the real-service probe cannot run")
        return 2
    provider = GroqProvider(
        base_url=settings.groq_base_url, api_key=key, model=settings.groq_model
    )
    try:
        report = await probe(provider, raw_path=RAW_DIR / "limit_probe.jsonl")
    finally:
        await provider.aclose()
    (OUT_DIR / "limits.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2)[:2000])
    print(f"\nwritten: {OUT_DIR / 'limits.json'}")
    return 0
