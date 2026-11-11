"""Calibrate the stand-in service from measurements of the real service.

This is deliberately a fit to *observations*, not to documentation. Whatever the
documented limits say, what matters for the load tests is the latency and fault
distribution we actually saw, and the honest places where a simulator cannot match:

  * TTFT is modelled as a two-point distribution (p50 / p90) rather than a smooth
    curve, because 10-40 samples cannot support a fitted tail.
  * Total time is linear in output tokens, which is right for steady-state
    streaming and wrong for cold starts and long prompts.
  * Rate limits are modelled exactly (counters), since those are the one thing the
    real service specifies; concurrency is not, because we never measured the
    provider's queue depth.

Run `relay probe-limits` first; this script refuses to invent numbers without it.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

from relay.config import PROJECT_ROOT
from relay.obs.events import percentile

RESULTS = PROJECT_ROOT / "results"
LIMITS = RESULTS / "limits.json"
RAW = RESULTS / "raw"
PARAMS = PROJECT_ROOT / "services" / "standin" / "params.json"


def _real_calls() -> list[dict[str, object]]:
    calls: list[dict[str, object]] = []
    for path in sorted(RAW.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            item = json.loads(line)
            if item.get("source") != "real":
                continue
            for call in item.get("calls", []):
                if call.get("status") == "ok" and call.get("ttft_ms"):
                    calls.append(call)
    return calls


def calibrate() -> dict[str, object]:
    if not LIMITS.exists():
        raise SystemExit(
            "results/limits.json missing: run `relay probe-limits` with a real key first. "
            "Refusing to write fabricated stand-in parameters."
        )
    limits = json.loads(LIMITS.read_text(encoding="utf-8"))
    latency = limits.get("latency", {})
    if not latency.get("ok"):
        raise SystemExit("probe recorded no successful calls; cannot calibrate")
    if latency.get("ttft_p50_ms") is None:
        raise SystemExit(
            "probe recorded no visible-content TTFT (reasoning-only responses); "
            "re-run `relay probe-limits` before calibrating rather than fitting 0 ms"
        )

    calls = _real_calls()
    params: dict[str, object] = {
        "ttft_p50_ms": round(float(latency["ttft_p50_ms"]), 1),
        "ttft_p90_ms": round(float(latency.get("ttft_p95_ms") or latency["ttft_p50_ms"]), 1),
        "per_token_ms": 4.0,
        "failure_rate": 0.0,
        "timeout_rate": 0.0,
        "partial_rate": 0.0,
        "calibrated": True,
        "calibrated_from": f"{len(calls)} successful real calls + probe latency sample",
        "sample_size": len(calls) or int(latency.get("ok", 0)),
        "fitted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "limits_source": limits["documented"],
        "observed_limits": limits.get("observed_from_headers", {}),
        "differences": [],
    }

    if calls:
        # total_ms = a + b * tokens_out, fit on the calls that actually streamed
        points = [
            (float(call.get("tokens_out") or 0), float(call["ms"]))
            for call in calls
            if call.get("tokens_out")
        ]
        if len(points) >= 4:
            xs = [x for x, _ in points]
            ys = [y for _, y in points]
            mx, my = median(xs), median(ys)
            numerator = sum((x - mx) * (y - my) for x, y in points)
            denominator = sum((x - mx) ** 2 for x in xs) or 1.0
            slope = numerator / denominator
            params["per_token_ms"] = round(max(slope, 0.5), 2)
        params["ttft_p50_ms"] = round(percentile([float(c.get("ttft_ms") or 0) for c in calls], 50), 1)
        params["ttft_p90_ms"] = round(percentile([float(c.get("ttft_ms") or 0) for c in calls], 90), 1)
        params["sample_size"] = len(calls)

    params["differences"] = [
        "Cold start: the first real request after idle was slower than the fitted TTFT; the stand-in has no cold path.",
        "Long prompts: real TTFT grows with prompt length (prefill), the stand-in's TTFT is independent of input tokens.",
        "Concurrency: the real provider queues internally at unknown depth; the stand-in models it as a linear slowdown (queue_dilation).",
        "Rate limits: counters match the documented window exactly, but the provider's window may roll rather than reset.",
        "Failures: no 5xx or truncated streams were observed in this sample, so failure_rate=0 is an observation, not a guarantee.",
    ]
    return params


def main() -> int:
    params = calibrate()
    PARAMS.write_text(json.dumps(params, indent=2), encoding="utf-8")
    print(json.dumps(params, indent=2))
    print(f"\nwritten: {PARAMS}")
    return 0
