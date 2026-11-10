"""Stand-in chat-completions service (OpenAI-compatible, streaming).

Run:
    .venv\\Scripts\\python -m uvicorn services.standin.app:app --port 8788

Query parameters on POST /v1/chat/completions tune a run without a restart:
    ?rpm=15&tpm=4000&rpd=1000&tpd=200000&seed=7&fail=0.02&timeout=0.01&partial=0.01
    ?exhaust_day=1   -> every request is a daily-limit 429 (scenario 5)
"""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import asdict
from typing import AsyncIterator

from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse

from services.standin.sim import Limits, SimParams, Simulator

app = FastAPI(title="The Relay stand-in model service")

PARAMS = SimParams.load()
LIMITS = Limits(
    rpm=int(os.getenv("STANDIN_RPM", "30")),
    tpm=int(os.getenv("STANDIN_TPM", "8000")),
    rpd=int(os.getenv("STANDIN_RPD", "1000")),
    tpd=int(os.getenv("STANDIN_TPD", "200000")),
)
SIM = Simulator(params=PARAMS, limits=LIMITS)


@app.get("/health")
async def health() -> dict[str, object]:
    return {
        "status": "ok",
        "calibrated": PARAMS.calibrated,
        "calibrated_from": PARAMS.calibrated_from,
        "sample_size": PARAMS.sample_size,
        "params": PARAMS.to_dict(),
        "limits": asdict(LIMITS),
        "inflight": SIM.inflight,
        "peak_queue": SIM.peak_queue,
    }


@app.get("/v1/models")
async def models() -> dict[str, object]:
    return {"data": [{"id": os.getenv("STANDIN_MODEL", "openai/gpt-oss-120b")}]}


def _sse(payload: dict[str, object]) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _tokens(text: str) -> list[str]:
    words = text.split(" ")
    return [word + (" " if index < len(words) - 1 else "") for index, word in enumerate(words)]


async def _stream(
    text: str,
    *,
    model: str,
    ttft_ms: float,
    per_token_ms: float,
    fault: str | None,
    tokens_out: int,
    prompt_tokens: int,
) -> AsyncIterator[str]:
    chunks = _tokens(text) or [" "]
    pace = max(0.0, (per_token_ms / 1000.0))
    await asyncio.sleep(max(0.0, ttft_ms / 1000.0))
    emitted = 0
    for piece in chunks:
        emitted += 1
        if fault == "partial" and emitted == max(1, len(chunks) // 3):
            # Cut the connection without the terminator or usage: the client sees
            # a partial answer, exactly like a dropped stream.
            return
        yield _sse(
            {
                "id": "chatcmpl-standin",
                "object": "chat.completion.chunk",
                "model": model,
                "choices": [{"index": 0, "delta": {"content": piece}, "finish_reason": None}],
            }
        )
        await asyncio.sleep(pace)
    yield _sse(
        {
            "id": "chatcmpl-standin",
            "object": "chat.completion.chunk",
            "model": model,
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
        }
    )
    yield _sse(
        {
            "id": "chatcmpl-standin",
            "object": "chat.completion.chunk",
            "model": model,
            "choices": [],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": min(tokens_out, len(chunks)),
                "total_tokens": prompt_tokens + min(tokens_out, len(chunks)),
            },
        }
    )
    yield "data: [DONE]\n\n"


@app.post("/v1/chat/completions")
async def chat_completions(
    request: Request,
    rpm: int | None = Query(default=None),
    tpm: int | None = Query(default=None),
    rpd: int | None = Query(default=None),
    tpd: int | None = Query(default=None),
    seed: int = Query(default=7),
    fail: float | None = Query(default=None),
    timeout: float | None = Query(default=None),
    partial: float | None = Query(default=None),
    exhaust_day: int = Query(default=0),
):
    body = await request.json()
    messages = body.get("messages", [])
    max_tokens = int(body.get("max_tokens", 256))
    model = str(body.get("model") or "openai/gpt-oss-120b")

    if rpm is not None:
        LIMITS.rpm = rpm
    if tpm is not None:
        LIMITS.tpm = tpm
    if rpd is not None:
        LIMITS.rpd = rpd
    if tpd is not None:
        LIMITS.tpd = tpd
    if fail is not None:
        PARAMS.failure_rate = fail
    if timeout is not None:
        PARAMS.timeout_rate = timeout
    if partial is not None:
        PARAMS.partial_rate = partial
    SIM.force_day_exhausted = bool(exhaust_day)

    system, user = SIM.prompts(messages)
    prompt_tokens = max(1, len(system + user) // 4)
    est_tokens = prompt_tokens + max_tokens

    SIM.inflight += 1
    SIM.peak_queue = max(SIM.peak_queue, max(0, SIM.inflight - PARAMS.concurrency))
    try:
        limit = SIM.check_limits(est_tokens)
        if limit is not None:
            kind, wait = limit
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "message": (
                            f"Rate limit reached for {model} on {kind}. "
                            f"Please try again in {wait:.1f}s."
                        ),
                        "type": "rate_limit_exceeded",
                        "code": "rate_limit_exceeded",
                    }
                },
                headers={**SIM.headers(), "retry-after": f"{wait:.1f}"},
            )

        fault = SIM.fault(user, seed)
        if fault == "server_error":
            return JSONResponse(
                status_code=500,
                content={"error": {"message": "internal server error (simulated)", "type": "server_error"}},
                headers=SIM.headers(),
            )

        if SIM.is_analysis_prompt(messages):
            text, tokens_out = SIM.analysis_response(user), 40
        else:
            _, text = SIM.draft_response(user)  # the JSON payload is what the client parses
            tokens_out = len(text.split())

        sample = SIM.sample_latency(user, max_tokens, seed)
        SIM.record(est_tokens, sample.tokens_out + prompt_tokens)

        if fault == "timeout":
            await asyncio.sleep(PARAMS.timeout_s)
            return JSONResponse(status_code=504, content={"error": {"message": "gateway timeout"}})

        return StreamingResponse(
            _stream(
                text,
                model=model,
                ttft_ms=sample.ttft_ms,
                per_token_ms=PARAMS.per_token_ms,
                fault=fault,
                tokens_out=tokens_out,
                prompt_tokens=prompt_tokens,
            ),
            media_type="text/event-stream",
            headers={**SIM.headers(), "cache-control": "no-cache"},
        )
    finally:
        SIM.inflight = max(0, SIM.inflight - 1)


@app.post("/reset")
async def reset() -> dict[str, object]:
    """Clear the rate windows and counters between load scenarios.

    The simulator keeps its minute and day windows in one process-global object, so
    two scenarios run back to back would share a bucket: a 240-request sustained run
    leaves the next scenario starting with nothing left in the minute. The load runner
    asks for a clean window explicitly instead of hoping the clock has rolled over.
    """
    global SIM
    SIM = Simulator(params=PARAMS, limits=LIMITS)
    return {"status": "reset"}


@app.get("/stats")
async def stats() -> dict[str, object]:
    return {
        "day_requests": SIM._day_requests,  # noqa: SLF001 - diagnostics endpoint
        "day_tokens": SIM._day_tokens,
        "peak_queue": SIM.peak_queue,
        "inflight": SIM.inflight,
        "params": PARAMS.to_dict(),
        "limits": asdict(LIMITS),
    }
