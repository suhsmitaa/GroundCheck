"""
Orchestrator — the agentic workflow.
--------------------------------------
Wires together three independent systems (retriever, generator, verifier)
into a self-correcting loop:

    retrieve -> generate -> verify -> (retry with stricter prompt if ungrounded)

This is deliberately a small, readable state machine rather than a
framework, so the control flow driving "quality" (retries, thresholds,
fail-safe fallback) is fully visible and testable — the actual point of
the exercise.

Every stage is timed and logged via observability.trace_stage, and every
run's outcome (pass/fail, groundedness score, retry count) is written to
metrics.jsonl for later monitoring/eval.
"""
from __future__ import annotations
from dataclasses import dataclass, field

from src.agents.retriever import retrieve
from src.agents.generator import generate
from src.agents.verifier import verify, VerificationResult
from src.security import sanitize_user_input, load_config
from src.observability import trace_stage, log_event, new_trace_id


@dataclass
class PipelineResult:
    trace_id: str
    query: str
    answer: str
    context: str
    verification: VerificationResult
    retries_used: int
    fallback_triggered: bool = False


FALLBACK_ANSWER = (
    "I'm not confident I can answer that accurately based on what I know. "
    "Please rephrase or contact support directly."
)


def run_pipeline(raw_query: str) -> PipelineResult:
    config = load_config()
    trace_id = new_trace_id()
    query = sanitize_user_input(raw_query)

    log_event("pipeline_start", trace_id=trace_id, query=query)

    with trace_stage(trace_id, "retrieve"):
        docs = retrieve(query, top_k=1)
        context = docs[0].text if docs else ""

    retries_used = 0
    verification = None
    answer = ""

    while retries_used <= config["max_retries"]:
        stage_name = "generate" if retries_used == 0 else f"generate_retry_{retries_used}"
        with trace_stage(trace_id, stage_name):
            answer = generate(query, context)

        with trace_stage(trace_id, "verify"):
            verification = verify(answer, context, threshold=config["groundedness_threshold"])
            log_event(
                "verification_result",
                trace_id=trace_id,
                retry=retries_used,
                score=verification.groundedness_score,
                passed=verification.passed,
                unsupported=verification.unsupported_sentences,
            )

        if verification.passed:
            break
        retries_used += 1

    fallback_triggered = not verification.passed
    if fallback_triggered:
        answer = FALLBACK_ANSWER
        log_event("fallback_triggered", trace_id=trace_id, final_score=verification.groundedness_score)

    log_event(
        "pipeline_end",
        trace_id=trace_id,
        passed=verification.passed,
        retries_used=retries_used,
        fallback_triggered=fallback_triggered,
    )

    return PipelineResult(
        trace_id=trace_id,
        query=query,
        answer=answer,
        context=context,
        verification=verification,
        retries_used=retries_used,
        fallback_triggered=fallback_triggered,
    )
