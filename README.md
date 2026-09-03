# GroundCheck

An **agentic workflow that reduces
hallucinations** through evaluation, testing, observability and a secured
CI pipeline.

## What it demonstrates

| Requirement                       | Where                                             |
|-----------------------------------|----------------------------------------------------|
| Agentic workflow pipeline         | `src/orchestrator.py` , retrieve -> generate -> verify -> retry/fallback loop |
| Multiple systems, orchestrated    | `src/agents/{retriever,generator,verifier}.py` , three independent, swappable components |
| Hallucination evaluation          | `evaluate.py` + `tests/eval_dataset.jsonl` , groundedness scoring & hallucination-rate report |
| Testing                           | `tests/` , pytest unit tests for the verifier and the orchestrator's retry/fallback logic |
| Observability & monitoring        | `src/observability.py` , structured JSON trace events per stage, `monitoring/README.md` |
| Secure pipeline                   | `src/security.py` (input validation, prompt-injection filter, fail-closed secrets) + `.github/workflows/ci.yml` (least-privilege token, dependency/static scans, mock-mode CI needing zero secrets) |

## Architecture

```
 user query
     │
     ▼
 [security.sanitize_user_input]   ← rejects injection attempts, empty/oversized input
     │
     ▼
 [retriever]  ──────────────► context (System 1: knowledge base / vector store)
     │
     ▼
 [generator]  ──────────────► draft answer (System 2: LLM, mock or live)
     │
     ▼
 [verifier]   ──────────────► groundedness score (System 3: hallucination gate)
     │
     ├── passed ─────────────────────────────► return answer
     │
     └── failed ── retry generate (up to N) ── still failing -> safe fallback answer

 Every stage above is timed + logged to metrics.jsonl (observability.py)
```

The three "systems" are deliberately decoupled , each is a plain function
with a narrow interface, so any one of them (e.g. swapping the lexical
verifier for a real NLI/LLM-judge model, or the mock generator for a live
API call) can change without touching the orchestrator or the tests.

## Running it

```bash
pip install -r requirements.txt

# Unit tests
pytest -q

# Hallucination-rate evaluation (also the CI quality gate)
python evaluate.py

# Try a single query interactively
python -c "from src.orchestrator import run_pipeline; r = run_pipeline('What is the refund policy?'); print(r.answer, r.verification)"
```

No API key is required , the generator runs in `MOCK` mode by default so
the whole thing (tests, eval, CI) is fully reproducible offline. Set
`LLM_MODE=live` and `ANTHROPIC_API_KEY` in `.env` to route through a real
Claude call instead (see `.env.example`).

## Why the mock generator "hallucinates" on purpose

The mock LLM in `src/agents/generator.py` intentionally tacks on an
unsupported claim for refund/warranty queries (e.g. "refunds are also
available for gift cards" , not in the knowledge base). This isn't a bug ,
it's what lets the verifier, retry loop, fallback path, and eval harness
all have something real to catch, without needing a flaky live model to
reproduce a hallucination on demand.

## CI pipeline

`.github/workflows/ci.yml` runs on every push/PR:
1. Unit tests (`pytest`)
2. Static security scan (`bandit`)
3. Dependency vulnerability scan (`pip-audit`)
4. The hallucination-rate quality gate (`evaluate.py`) , fails the build if
   the eval set's hallucination rate exceeds budget

It runs entirely in mock mode, so CI needs zero secrets or network calls to
an LLM provider.
