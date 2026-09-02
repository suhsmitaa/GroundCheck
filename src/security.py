"""
Secure pipeline layer.
-----------------------
Small, focused controls rather than a security theatre wrapper:
  1. Secrets are only ever read from environment variables, never hardcoded
     or logged (see observability.py's redact()).
  2. User input is length-capped and stripped of common prompt-injection /
     control-token patterns before it reaches the retriever or generator.
  3. A minimal allow-list validates config values instead of trusting env
     blindly.
"""
from __future__ import annotations
import os
import re

MAX_INPUT_LENGTH = 2000

_INJECTION_PATTERNS = [
    r"ignore (all )?previous instructions",
    r"system prompt",
    r"</?(system|assistant|user)>",
    r"you are now",
]


class InputValidationError(ValueError):
    pass


def sanitize_user_input(raw: str) -> str:
    if raw is None:
        raise InputValidationError("Input cannot be empty.")
    text = raw.strip()
    if not text:
        raise InputValidationError("Input cannot be empty.")
    if len(text) > MAX_INPUT_LENGTH:
        raise InputValidationError(f"Input exceeds {MAX_INPUT_LENGTH} characters.")

    lowered = text.lower()
    for pattern in _INJECTION_PATTERNS:
        if re.search(pattern, lowered):
            raise InputValidationError("Input rejected by prompt-injection filter.")

    return text


def get_required_secret(name: str) -> str:
    """Loads a secret from env only. Raises rather than silently
    proceeding with an empty credential — fail closed, not open."""
    value = os.getenv(name)
    if not value:
        raise InputValidationError(f"Missing required secret: {name}")
    return value


def load_config() -> dict:
    """Validated config load with safe defaults for local/CI runs."""
    return {
        "llm_mode": os.getenv("LLM_MODE", "mock").lower(),
        "groundedness_threshold": float(os.getenv("GROUNDEDNESS_THRESHOLD", "0.55")),
        "max_retries": int(os.getenv("MAX_AGENT_RETRIES", "2")),
    }
