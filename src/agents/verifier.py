"""
Verifier ("System 3") — the hallucination gate.
-------------------------------------------------
Scores how well a generated answer is grounded in the retrieved context.
This is a lightweight lexical-entailment heuristic (sentence-level overlap),
standing in for a real NLI/groundedness model (e.g. an entailment classifier
or a second LLM-as-judge call). The interface is what matters: the
orchestrator treats this as a black-box "groundedness_score" provider, so
swapping in a real model later is a one-file change.
"""
from __future__ import annotations
from dataclasses import dataclass
import re


@dataclass
class VerificationResult:
    groundedness_score: float
    unsupported_sentences: list[str]
    passed: bool


def _split_sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def _sentence_supported(sentence: str, context: str, min_overlap: float = 0.5) -> bool:
    sent_tokens = set(re.findall(r"[a-z0-9]+", sentence.lower()))
    ctx_tokens = set(re.findall(r"[a-z0-9]+", context.lower()))
    if not sent_tokens:
        return True
    overlap = len(sent_tokens & ctx_tokens) / len(sent_tokens)
    return overlap >= min_overlap


def verify(answer: str, context: str, threshold: float = 0.55) -> VerificationResult:
    sentences = _split_sentences(answer)
    if not sentences:
        return VerificationResult(0.0, [], False)

    unsupported = [s for s in sentences if not _sentence_supported(s, context)]
    score = 1 - (len(unsupported) / len(sentences))

    return VerificationResult(
        groundedness_score=round(score, 3),
        unsupported_sentences=unsupported,
        passed=score >= threshold,
    )
