"""The real Groq service.

We speak HTTP directly rather than through the SDK for three reasons that matter
to this assignment: first-token timing must be measured at the socket, the
`retry-after` / `x-ratelimit-*` headers are primary evidence for Table 1, and we
must know exactly how many requests we sent (a hidden SDK retry would corrupt
every request count in the results).
"""

from __future__ import annotations

import json
import time

import httpx

from relay.llm.base import (
    AUTH_ERROR,
    BAD_REQUEST,
    RATE_LIMITED_DAY,
    RATE_LIMITED_MINUTE,
    SERVER_ERROR,
    TIMEOUT,
    ChatRequest,
    ChatResult,
)

INTERESTING_HEADERS = (
    "retry-after",
    "x-ratelimit-limit-requests",
    "x-ratelimit-remaining-requests",
    "x-ratelimit-reset-requests",
    "x-ratelimit-limit-tokens",
    "x-ratelimit-remaining-tokens",
    "x-ratelimit-reset-tokens",
)


def classify_429(body: str, retry_after_s: float | None) -> str:
    """Distinguish a per-minute rejection from a per-day one.

    The body names the limit ('requests per day (RPD)', 'tokens per minute
    (TPM)'); `retry-after` corroborates it. Getting this wrong is expensive: a
    daily-limit retry cannot succeed this day, so retrying it only delays the
    refusal the user should have received immediately.
    """
    lowered = body.lower()
    if "per day" in lowered or "rpd" in lowered or "tpd" in lowered:
        return RATE_LIMITED_DAY
    if retry_after_s is not None and retry_after_s > 300:
        return RATE_LIMITED_DAY
    return RATE_LIMITED_MINUTE


class GroqProvider:
    name = "groq"

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        client: httpx.AsyncClient | None = None,
        connect_timeout_s: float = 10.0,
        read_timeout_s: float = 45.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._api_key = api_key
        self.model = model
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(read_timeout_s, connect=connect_timeout_s),
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    async def list_models(self) -> list[str]:
        response = await self._client.get(f"{self.base_url}/models", headers=self._headers())
        response.raise_for_status()
        payload = response.json()
        return sorted(item["id"] for item in payload.get("data", []))

    async def chat(self, request: ChatRequest) -> ChatResult:
        body = {
            "model": request.model or self.model,
            "messages": request.messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        started = time.perf_counter()
        first_token_at: float | None = None
        text_parts: list[str] = []
        chunks = 0
        usage: dict[str, int] = {}
        finish_reason: str | None = None

        try:
            async with self._client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=body,
                params=request.extra_query or None,
            ) as response:
                captured = {
                    key: response.headers[key]
                    for key in INTERESTING_HEADERS
                    if key in response.headers
                }
                if response.status_code != 200:
                    raw = (await response.aread()).decode("utf-8", "replace")
                    elapsed = (time.perf_counter() - started) * 1000
                    retry_after = _parse_retry_after(response.headers.get("retry-after"))
                    if response.status_code == 429:
                        kind = classify_429(raw, retry_after)
                        status = "rate_limited"
                    elif response.status_code in (401, 403):
                        kind, status = AUTH_ERROR, "error"
                    elif response.status_code >= 500:
                        kind, status = SERVER_ERROR, "error"
                    else:
                        kind, status = BAD_REQUEST, "error"
                    return ChatResult(
                        status=status,
                        error_kind=kind,
                        error=raw[:500],
                        total_ms=elapsed,
                        http_status=response.status_code,
                        retry_after_s=retry_after,
                        headers=captured,
                    )

                async for line in response.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    payload = line[5:].strip()
                    if payload == "[DONE]":
                        break
                    try:
                        event = json.loads(payload)
                    except json.JSONDecodeError:
                        continue
                    if event.get("usage"):
                        usage = event["usage"]
                    for choice in event.get("choices", []):
                        delta = choice.get("delta") or {}
                        piece = delta.get("content")
                        if piece:
                            if first_token_at is None:
                                first_token_at = time.perf_counter()
                            text_parts.append(piece)
                            chunks += 1
                        if choice.get("finish_reason"):
                            finish_reason = choice["finish_reason"]

            elapsed = (time.perf_counter() - started) * 1000
            return ChatResult(
                text="".join(text_parts),
                status="ok",
                ttft_ms=None if first_token_at is None else (first_token_at - started) * 1000,
                total_ms=elapsed,
                tokens_in=int(usage.get("prompt_tokens", 0)),
                tokens_out=int(usage.get("completion_tokens", 0)),
                http_status=200,
                headers=captured,
                chunks_received=chunks,
                finish_reason=finish_reason,
            )
        except httpx.ReadTimeout as exc:
            return _transport_failure(started, TIMEOUT, "timeout", exc, text_parts, first_token_at)
        except httpx.TimeoutException as exc:
            return _transport_failure(started, TIMEOUT, "timeout", exc, text_parts, first_token_at)
        except httpx.HTTPError as exc:
            return _transport_failure(started, SERVER_ERROR, "error", exc, text_parts, first_token_at)


def _parse_retry_after(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _transport_failure(
    started: float,
    kind: str,
    status: str,
    exc: Exception,
    text_parts: list[str],
    first_token_at: float | None,
) -> ChatResult:
    elapsed = (time.perf_counter() - started) * 1000
    return ChatResult(
        text="".join(text_parts),
        status=status,
        error_kind=kind,
        error=f"{type(exc).__name__}: {exc}",
        ttft_ms=None if first_token_at is None else (first_token_at - started) * 1000,
        total_ms=elapsed,
        chunks_received=len(text_parts),
    )
