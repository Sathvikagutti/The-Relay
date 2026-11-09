"""Provider interface shared by the real service and the stand-in.

The pipeline depends on this Protocol only, which is what makes the same code
path testable against a simulated provider and measurable against the real one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

# Failure categories decide retry behaviour, so they are part of the interface.
RATE_LIMITED_MINUTE = "rate_limited_minute"  # window refills in seconds -> retry
RATE_LIMITED_DAY = "rate_limited_day"        # window refills in hours -> do not retry
SERVER_ERROR = "server_error"                # 5xx -> retry with backoff
TIMEOUT = "timeout"                          # read timeout / deadline -> retry once
BAD_REQUEST = "bad_request"                  # 4xx other than 429 -> never retry
AUTH_ERROR = "auth_error"                    # 401/403 -> never retry


@dataclass(slots=True)
class ChatRequest:
    messages: list[dict[str, str]]
    max_tokens: int
    temperature: float = 0.0
    model: str = ""
    extra_query: dict[str, str] | None = None  # stand-in scenario controls only


@dataclass(slots=True)
class ChatResult:
    text: str = ""
    status: str = "ok"  # ok | rate_limited | timeout | error
    error_kind: str | None = None
    error: str | None = None
    ttft_ms: float | None = None
    total_ms: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0
    http_status: int | None = None
    retry_after_s: float | None = None
    headers: dict[str, str] = field(default_factory=dict)
    chunks_received: int = 0
    finish_reason: str | None = None

    @property
    def ok(self) -> bool:
        return self.status == "ok"

    @property
    def partial(self) -> bool:
        """Streamed text arrived but the stream did not finish cleanly."""
        return bool(self.text) and not self.ok


class Provider(Protocol):
    name: str

    async def chat(self, request: ChatRequest) -> ChatResult: ...
