"""
Observability & monitoring layer.
-----------------------------------
Structured, machine-parseable event logs (JSON Lines) rather than free-text
prints. In a real deployment this sink would be swapped for OpenTelemetry /
Datadog / CloudWatch — the event schema below is designed to map directly
onto that later without changing calling code.

Every pipeline run emits one event per stage plus one summary event, so a
dashboard can compute: latency per stage, retry rate, groundedness score
distribution, and hallucination rate over time.
"""
from __future__ import annotations
import json
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

METRICS_PATH = Path(__file__).resolve().parent.parent / "metrics.jsonl"

_SECRET_KEYS = {"api_key", "anthropic_api_key", "token", "secret"}


def redact(payload: dict) -> dict:
    """Never let a secret reach the log sink, even by accident."""
    return {
        k: ("***REDACTED***" if k.lower() in _SECRET_KEYS else v)
        for k, v in payload.items()
    }


def log_event(event_type: str, **fields) -> None:
    record = {
        "ts": time.time(),
        "event": event_type,
        **redact(fields),
    }
    with METRICS_PATH.open("a") as f:
        f.write(json.dumps(record) + "\n")


@contextmanager
def trace_stage(trace_id: str, stage: str):
    """Times a pipeline stage and logs start/end/duration/errors —
    a minimal stand-in for a real tracing span."""
    start = time.time()
    log_event("stage_start", trace_id=trace_id, stage=stage)
    try:
        yield
    except Exception as exc:
        log_event("stage_error", trace_id=trace_id, stage=stage, error=str(exc))
        raise
    finally:
        log_event(
            "stage_end",
            trace_id=trace_id,
            stage=stage,
            duration_ms=round((time.time() - start) * 1000, 2),
        )


def new_trace_id() -> str:
    return uuid.uuid4().hex[:12]
