# Pricing data sourced from LiteLLM's model_prices_and_context_window.json
# (MIT license, BerriAI).

"""Static pricing table and cost utilities for LLM model calls.

All per-token prices are in USD.  Prices per million tokens are divided by
1_000_000 before storage so callers can multiply directly by token counts.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Static pricing table
# Keys are model-name prefixes; longest-prefix match is used for lookups.
# All costs are USD per token (not per million).
# ---------------------------------------------------------------------------

STATIC_PRICING: dict[str, dict] = {
    # ── Anthropic Claude 4 ──────────────────────────────────────────────────
    "claude-opus-4": {
        "input_cost_per_token": 15e-6,
        "output_cost_per_token": 75e-6,
        "cache_read_input_token_cost": 1.5e-6,
        "cache_creation_input_token_cost": 3.75e-6,
        "litellm_provider": "anthropic",
    },
    "claude-sonnet-4-6": {
        "input_cost_per_token": 3e-6,
        "output_cost_per_token": 15e-6,
        "cache_read_input_token_cost": 3e-7,
        "cache_creation_input_token_cost": 7.5e-7,
        "litellm_provider": "anthropic",
    },
    "claude-sonnet-4-5": {
        "input_cost_per_token": 3e-6,
        "output_cost_per_token": 15e-6,
        "cache_read_input_token_cost": 3e-7,
        "cache_creation_input_token_cost": 7.5e-7,
        "litellm_provider": "anthropic",
    },
    "claude-haiku-4-5": {
        "input_cost_per_token": 0.80e-6,
        "output_cost_per_token": 4e-6,
        "cache_read_input_token_cost": 0.08e-6,
        "cache_creation_input_token_cost": 0.20e-6,
        "litellm_provider": "anthropic",
    },
    # ── Anthropic Claude 3.x ────────────────────────────────────────────────
    "claude-3-5-sonnet": {
        "input_cost_per_token": 3e-6,
        "output_cost_per_token": 15e-6,
        "cache_read_input_token_cost": 3e-7,
        "cache_creation_input_token_cost": 7.5e-7,
        "litellm_provider": "anthropic",
    },
    "claude-3-5-haiku": {
        "input_cost_per_token": 0.80e-6,
        "output_cost_per_token": 4e-6,
        "cache_read_input_token_cost": 0.08e-6,
        "cache_creation_input_token_cost": 0.20e-6,
        "litellm_provider": "anthropic",
    },
    "claude-3-opus": {
        "input_cost_per_token": 15e-6,
        "output_cost_per_token": 75e-6,
        "cache_read_input_token_cost": 1.5e-6,
        "cache_creation_input_token_cost": 3.75e-6,
        "litellm_provider": "anthropic",
    },
    # ── OpenAI ──────────────────────────────────────────────────────────────
    "gpt-4.5": {
        "input_cost_per_token": 75e-6,
        "output_cost_per_token": 150e-6,
        "litellm_provider": "openai",
    },
    "gpt-4o-mini": {
        "input_cost_per_token": 0.15e-6,
        "output_cost_per_token": 0.60e-6,
        "litellm_provider": "openai",
    },
    "gpt-4o": {
        "input_cost_per_token": 2.50e-6,
        "output_cost_per_token": 10e-6,
        "litellm_provider": "openai",
    },
    "gpt-4.1-mini": {
        "input_cost_per_token": 0.40e-6,
        "output_cost_per_token": 1.60e-6,
        "litellm_provider": "openai",
    },
    "gpt-4.1": {
        "input_cost_per_token": 2e-6,
        "output_cost_per_token": 8e-6,
        "litellm_provider": "openai",
    },
    "o4-mini": {
        "input_cost_per_token": 1.10e-6,
        "output_cost_per_token": 4.40e-6,
        "litellm_provider": "openai",
    },
    "o3-mini": {
        "input_cost_per_token": 1.10e-6,
        "output_cost_per_token": 4.40e-6,
        "litellm_provider": "openai",
    },
    "o3": {
        "input_cost_per_token": 10e-6,
        "output_cost_per_token": 40e-6,
        "litellm_provider": "openai",
    },
    # ── Google Gemini ───────────────────────────────────────────────────────
    "gemini-2.5-pro": {
        "input_cost_per_token": 1.25e-6,
        "output_cost_per_token": 10e-6,
        "litellm_provider": "google",
    },
    "gemini-2.5-flash": {
        "input_cost_per_token": 0.15e-6,
        "output_cost_per_token": 0.60e-6,
        "litellm_provider": "google",
    },
    "gemini-2.0-flash": {
        "input_cost_per_token": 0.10e-6,
        "output_cost_per_token": 0.40e-6,
        "litellm_provider": "google",
    },
    "gemini-1.5-pro": {
        "input_cost_per_token": 1.25e-6,
        "output_cost_per_token": 5e-6,
        "litellm_provider": "google",
    },
    "gemini-1.5-flash": {
        "input_cost_per_token": 0.075e-6,
        "output_cost_per_token": 0.30e-6,
        "litellm_provider": "google",
    },
}

# ---------------------------------------------------------------------------
# Provider colors
# ---------------------------------------------------------------------------

PROVIDER_COLORS: dict[str, str] = {
    "anthropic": "#7B2FBE",
    "openai": "#10A37F",
    "google": "#4285F4",
    "azure": "#3B82F6",
}

# ---------------------------------------------------------------------------
# Per-model colors (longest-prefix match, same algorithm as pricing)
# Purple family for Anthropic, teal/green for OpenAI, blue for Google.
# ---------------------------------------------------------------------------

_MODEL_COLORS: dict[str, str] = {
    # Anthropic — purple family
    "claude-opus": "#7B2FBE",
    "claude-3-opus": "#7B2FBE",
    "claude-sonnet": "#9C59D1",
    "claude-haiku": "#C08FE8",
    # OpenAI — teal/green family
    "gpt-4.5": "#047857",
    "gpt-4o-mini": "#34D399",
    "gpt-4o": "#10A37F",
    "gpt-4.1-mini": "#6EE7B7",
    "gpt-4.1": "#059669",
    "o4-mini": "#10B981",
    "o3-mini": "#0D9488",
    "o3": "#0F766E",
    # Google — blue family
    "gemini-2.5-pro": "#1E40AF",
    "gemini-2.5-flash": "#2563EB",
    "gemini-2.0-flash": "#3B82F6",
    "gemini-1.5-pro": "#1D4ED8",
    "gemini-1.5-flash": "#60A5FA",
}

# ---------------------------------------------------------------------------
# Special-purpose colors
# ---------------------------------------------------------------------------

TOOL_COLOR: str = "#64748B"  # slate gray
THINKING_COLOR: str = "#6366F1"  # indigo
UNKNOWN_COLOR: str = "#F59E0B"  # amber

# ---------------------------------------------------------------------------
# Internal: pre-sorted key lists (longest first) for O(n) prefix lookups
# ---------------------------------------------------------------------------

_sorted_pricing_keys: list[str] = sorted(STATIC_PRICING.keys(), key=len, reverse=True)
_sorted_model_color_keys: list[str] = sorted(
    _MODEL_COLORS.keys(), key=len, reverse=True
)


def _lookup_pricing(model: str) -> dict | None:
    """Longest-prefix match against STATIC_PRICING keys (case-insensitive).

    Returns the matched pricing dict, or None if no prefix matched.
    """
    model_lower = model.lower()
    for key in _sorted_pricing_keys:
        if model_lower.startswith(key):
            return STATIC_PRICING[key]
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_pricing() -> dict:
    """Return the static pricing table.

    Phase 1: returns STATIC_PRICING directly.
    Phase 2 will add LiteLLM fetch + local cache.
    """
    return STATIC_PRICING


def compute_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int = 0,
    cache_write_tokens: int = 0,
) -> float:
    """Calculate total USD cost for a model invocation.

    Uses longest-prefix match against STATIC_PRICING.  Returns 0.0 for
    models that do not match any known prefix.
    """
    pricing = _lookup_pricing(model)
    if pricing is None:
        return 0.0

    return (
        input_tokens * pricing["input_cost_per_token"]
        + output_tokens * pricing["output_cost_per_token"]
        + cache_read_tokens * pricing.get("cache_read_input_token_cost", 0.0)
        + cache_write_tokens * pricing.get("cache_creation_input_token_cost", 0.0)
    )


def get_model_color(model: str, provider: str = "") -> str:
    """Return a CSS hex color for the given model.

    Resolution order:
    1. Longest-prefix match in _MODEL_COLORS.
    2. Provider name lookup in PROVIDER_COLORS (case-insensitive).
    3. UNKNOWN_COLOR sentinel.
    """
    model_lower = model.lower()
    for key in _sorted_model_color_keys:
        if model_lower.startswith(key):
            return _MODEL_COLORS[key]

    if provider:
        color = PROVIDER_COLORS.get(provider.lower())
        if color is not None:
            return color

    return UNKNOWN_COLOR
