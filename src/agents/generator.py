"""
Generator ("System 2")
-----------------------
Wraps the LLM call. Supports two modes, switched purely by environment
config (no code changes needed):

  * MOCK mode (default): deterministic canned responses so tests/CI/eval
    never depend on network access or an API key.
  * LIVE mode: real call to the Anthropic Messages API, used only when
    ANTHROPIC_API_KEY is present and LLM_MODE=live.

Keeping this boundary explicit is what lets the same orchestrator and eval
harness run in CI, in a sandbox, and in production unchanged.
"""
from __future__ import annotations
import os


def _mock_generate(prompt: str, context: str) -> str:
    """Deterministic stand-in for an LLM, intentionally includes a couple of
    unsupported claims sometimes so the verifier has something to catch."""
    prompt_l = prompt.lower()
    if "refund" in prompt_l:
        return (context + " Refunds are also available for gift cards.")
    if "shipping" in prompt_l:
        return context
    if "warranty" in prompt_l:
        return (context + " Extended warranty is free for loyalty members.")
    if "support" in prompt_l:
        return context
    return "I don't have enough information to answer that confidently."


def _live_generate(prompt: str, context: str) -> str:
    import anthropic  # imported lazily so mock mode has zero hard dependency

    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
    system = (
        "Answer the user's question using ONLY the provided context. "
        "If the context does not contain the answer, say you don't know."
    )
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        system=system,
        messages=[{"role": "user", "content": f"Context:\n{context}\n\nQuestion: {prompt}"}],
    )
    return "".join(block.text for block in message.content if block.type == "text")


def generate(prompt: str, context: str) -> str:
    mode = os.getenv("LLM_MODE", "mock").lower()
    if mode == "live" and os.getenv("ANTHROPIC_API_KEY"):
        return _live_generate(prompt, context)
    return _mock_generate(prompt, context)
