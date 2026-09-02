"""
Evaluation harness.
---------------------
Runs the pipeline over a small labeled eval set and reports the metrics an
employer / reviewer would actually care about for "AI quality":

  - hallucination rate      (fraction of answers that failed grounding)
  - avg groundedness score
  - retry rate               (how often the agentic loop had to self-correct)
  - fallback rate            (how often it safely refused rather than guess)
  - label accuracy           (does expect_pass match what actually happened)

Exit code is non-zero if hallucination rate exceeds the configured budget,
so this script doubles as a CI quality gate (see .github/workflows/ci.yml).
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

from src.orchestrator import run_pipeline

EVAL_SET = Path(__file__).parent / "tests" / "eval_dataset.jsonl"
# NOTE: this toy eval set intentionally includes queries the mock generator
# hallucinates on, so the verifier/retry loop has something real to catch.
# The budget below is loose to match that toy set; in production this would
# be a strict SLA (e.g. 5-10%) enforced on a much larger, curated eval set.
HALLUCINATION_RATE_BUDGET = 0.60


def load_eval_set() -> list[dict]:
    with EVAL_SET.open() as f:
        return [json.loads(line) for line in f if line.strip()]


def main() -> int:
    cases = load_eval_set()
    n = len(cases)
    grounded_first_pass = 0
    total_score = 0.0
    retried = 0
    fallbacks = 0
    label_matches = 0

    print(f"Running evaluation over {n} cases...\n")

    for case in cases:
        result = run_pipeline(case["query"])
        first_pass_grounded = result.retries_used == 0
        grounded_first_pass += int(first_pass_grounded)
        total_score += result.verification.groundedness_score
        retried += int(result.retries_used > 0)
        fallbacks += int(result.fallback_triggered)
        actual_pass = not result.fallback_triggered
        label_matches += int(actual_pass == case["expect_pass"])

        print(
            f"- {case['query']!r:45} score={result.verification.groundedness_score:.2f} "
            f"retries={result.retries_used} fallback={result.fallback_triggered}"
        )

    hallucination_rate = 1 - (grounded_first_pass / n)
    avg_score = total_score / n
    retry_rate = retried / n
    fallback_rate = fallbacks / n
    accuracy = label_matches / n

    print("\n--- Summary ---")
    print(f"hallucination_rate (first pass): {hallucination_rate:.0%}")
    print(f"avg_groundedness_score:          {avg_score:.2f}")
    print(f"retry_rate:                      {retry_rate:.0%}")
    print(f"fallback_rate:                   {fallback_rate:.0%}")
    print(f"label_accuracy:                  {accuracy:.0%}")

    if hallucination_rate > HALLUCINATION_RATE_BUDGET:
        print(
            f"\nFAIL: hallucination rate {hallucination_rate:.0%} exceeds "
            f"budget of {HALLUCINATION_RATE_BUDGET:.0%}"
        )
        return 1

    print("\nPASS: within hallucination rate budget.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
