"""Model pricing table for cost calculation.

Prices in USD per million tokens (input_per_mtok, output_per_mtok).
Update when rates change and note the date at the top.

Last updated: 2026-04-22
Sources: Anthropic, OpenAI, Google published pricing pages.
"""

from __future__ import annotations

# (input_per_mtok, output_per_mtok) in USD.
# Lookup uses longest-prefix match on model name (case-insensitive).
PRICING: dict[str, tuple[float, float]] = {
    # Anthropic Claude 4 family
    "claude-opus-4": (15.00, 75.00),
    "claude-sonnet-4": (3.00, 15.00),
    "claude-haiku-4": (0.80, 4.00),
    # Anthropic Claude 3.x legacy
    "claude-3-5-sonnet": (3.00, 15.00),
    "claude-3-5-haiku": (0.80, 4.00),
    "claude-3-opus": (15.00, 75.00),
    "claude-3-haiku": (0.25, 1.25),
    "claude-3-sonnet": (3.00, 15.00),
    # OpenAI
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4.1-nano": (0.10, 0.40),
    "gpt-4.1": (2.00, 8.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    "o4-mini": (1.10, 4.40),
    "o3-mini": (1.10, 4.40),
    "o3": (10.00, 40.00),
    "o1-mini": (3.00, 12.00),
    "o1": (15.00, 60.00),
    # Google Gemini
    "gemini-3.1-flash": (0.30, 1.20),
    "gemini-3-pro": (2.50, 15.00),
    "gemini-2.5-pro": (1.25, 10.00),
    "gemini-2.5-flash": (0.15, 0.60),
    "gemini-2.0-flash": (0.10, 0.40),
    "gemini-1.5-pro": (1.25, 5.00),
    "gemini-1.5-flash": (0.075, 0.30),
}

# Cache token pricing factors (relative to the input rate for that model)
CACHE_READ_FACTOR = 0.10  # cache_read  = 10% of input rate
CACHE_WRITE_FACTOR = 0.25  # cache_write = 25% of input rate
# Reasoning tokens are billed the same as output tokens.


def _lookup(model: str) -> tuple[float, float] | None:
    """Return (input_rate, output_rate) for model, or None if unknown."""
    lower = model.lower()
    for key in sorted(PRICING, key=len, reverse=True):
        if lower.startswith(key.lower()):
            return PRICING[key]
    return None


def compute_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int = 0,
    cache_write_tokens: int = 0,
    reasoning_tokens: int = 0,
) -> float:
    """Return estimated cost in USD for one LLM call.

    Returns 0.0 when the model is not in the pricing table -- never raises.
    Reasoning tokens are billed at the output rate.
    """
    rates = _lookup(model)
    if rates is None:
        return 0.0
    input_rate, output_rate = rates
    per_in = input_rate / 1_000_000
    per_out = output_rate / 1_000_000
    return (
        input_tokens * per_in
        + output_tokens * per_out
        + reasoning_tokens * per_out
        + cache_read_tokens * per_in * CACHE_READ_FACTOR
        + cache_write_tokens * per_in * CACHE_WRITE_FACTOR
    )
