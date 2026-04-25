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

# fmt: off
STATIC_PRICING: dict[str, dict] = {
    # ── Anthropic ──
    "claude-3-7-sonnet-20250219": {
        "input_cost_per_token": 3e-06,
        "output_cost_per_token": 1.5e-05,
        "cache_read_input_token_cost": 3e-07,
        "cache_creation_input_token_cost": 3.75e-06,
        "litellm_provider": "anthropic",
    },
    "claude-3-haiku-20240307": {
        "input_cost_per_token": 2.5e-07,
        "output_cost_per_token": 1.25e-06,
        "cache_read_input_token_cost": 3e-08,
        "cache_creation_input_token_cost": 3e-07,
        "litellm_provider": "anthropic",
    },
    "claude-3-opus-20240229": {
        "input_cost_per_token": 1.5e-05,
        "output_cost_per_token": 7.5e-05,
        "cache_read_input_token_cost": 1.5e-06,
        "cache_creation_input_token_cost": 1.875e-05,
        "litellm_provider": "anthropic",
    },
    "claude-4-opus-20250514": {
        "input_cost_per_token": 1.5e-05,
        "output_cost_per_token": 7.5e-05,
        "cache_read_input_token_cost": 1.5e-06,
        "cache_creation_input_token_cost": 1.875e-05,
        "litellm_provider": "anthropic",
    },
    "claude-4-sonnet-20250514": {
        "input_cost_per_token": 3e-06,
        "output_cost_per_token": 1.5e-05,
        "cache_read_input_token_cost": 3e-07,
        "cache_creation_input_token_cost": 3.75e-06,
        "litellm_provider": "anthropic",
    },
    "claude-haiku-4-5": {
        "input_cost_per_token": 1e-06,
        "output_cost_per_token": 5e-06,
        "cache_read_input_token_cost": 1e-07,
        "cache_creation_input_token_cost": 1.25e-06,
        "litellm_provider": "anthropic",
    },
    "claude-haiku-4-5-20251001": {
        "input_cost_per_token": 1e-06,
        "output_cost_per_token": 5e-06,
        "cache_read_input_token_cost": 1e-07,
        "cache_creation_input_token_cost": 1.25e-06,
        "litellm_provider": "anthropic",
    },
    "claude-opus-4-1": {
        "input_cost_per_token": 1.5e-05,
        "output_cost_per_token": 7.5e-05,
        "cache_read_input_token_cost": 1.5e-06,
        "cache_creation_input_token_cost": 1.875e-05,
        "litellm_provider": "anthropic",
    },
    "claude-opus-4-1-20250805": {
        "input_cost_per_token": 1.5e-05,
        "output_cost_per_token": 7.5e-05,
        "cache_read_input_token_cost": 1.5e-06,
        "cache_creation_input_token_cost": 1.875e-05,
        "litellm_provider": "anthropic",
    },
    "claude-opus-4-20250514": {
        "input_cost_per_token": 1.5e-05,
        "output_cost_per_token": 7.5e-05,
        "cache_read_input_token_cost": 1.5e-06,
        "cache_creation_input_token_cost": 1.875e-05,
        "litellm_provider": "anthropic",
    },
    "claude-opus-4-5": {
        "input_cost_per_token": 5e-06,
        "output_cost_per_token": 2.5e-05,
        "cache_read_input_token_cost": 5e-07,
        "cache_creation_input_token_cost": 6.25e-06,
        "litellm_provider": "anthropic",
    },
    "claude-opus-4-5-20251101": {
        "input_cost_per_token": 5e-06,
        "output_cost_per_token": 2.5e-05,
        "cache_read_input_token_cost": 5e-07,
        "cache_creation_input_token_cost": 6.25e-06,
        "litellm_provider": "anthropic",
    },
    "claude-opus-4-6": {
        "input_cost_per_token": 5e-06,
        "output_cost_per_token": 2.5e-05,
        "cache_read_input_token_cost": 5e-07,
        "cache_creation_input_token_cost": 6.25e-06,
        "litellm_provider": "anthropic",
    },
    "claude-opus-4-6-20260205": {
        "input_cost_per_token": 5e-06,
        "output_cost_per_token": 2.5e-05,
        "cache_read_input_token_cost": 5e-07,
        "cache_creation_input_token_cost": 6.25e-06,
        "litellm_provider": "anthropic",
    },
    "claude-opus-4-7": {
        "input_cost_per_token": 5e-06,
        "output_cost_per_token": 2.5e-05,
        "cache_read_input_token_cost": 5e-07,
        "cache_creation_input_token_cost": 6.25e-06,
        "litellm_provider": "anthropic",
    },
    "claude-opus-4-7-20260416": {
        "input_cost_per_token": 5e-06,
        "output_cost_per_token": 2.5e-05,
        "cache_read_input_token_cost": 5e-07,
        "cache_creation_input_token_cost": 6.25e-06,
        "litellm_provider": "anthropic",
    },
    "claude-sonnet-4-20250514": {
        "input_cost_per_token": 3e-06,
        "output_cost_per_token": 1.5e-05,
        "cache_read_input_token_cost": 3e-07,
        "cache_creation_input_token_cost": 3.75e-06,
        "litellm_provider": "anthropic",
    },
    "claude-sonnet-4-5": {
        "input_cost_per_token": 3e-06,
        "output_cost_per_token": 1.5e-05,
        "cache_read_input_token_cost": 3e-07,
        "cache_creation_input_token_cost": 3.75e-06,
        "litellm_provider": "anthropic",
    },
    "claude-sonnet-4-5-20250929": {
        "input_cost_per_token": 3e-06,
        "output_cost_per_token": 1.5e-05,
        "cache_read_input_token_cost": 3e-07,
        "cache_creation_input_token_cost": 3.75e-06,
        "litellm_provider": "anthropic",
    },
    "claude-sonnet-4-6": {
        "input_cost_per_token": 3e-06,
        "output_cost_per_token": 1.5e-05,
        "cache_read_input_token_cost": 3e-07,
        "cache_creation_input_token_cost": 3.75e-06,
        "litellm_provider": "anthropic",
    },
    # ── Openai ──
    "chatgpt-4o-latest": {
        "input_cost_per_token": 5e-06,
        "output_cost_per_token": 1.5e-05,
        "litellm_provider": "openai",
    },
    "codex-mini-latest": {
        "input_cost_per_token": 1.5e-06,
        "output_cost_per_token": 6e-06,
        "cache_read_input_token_cost": 3.75e-07,
        "litellm_provider": "openai",
    },
    "ft:gpt-3.5-turbo": {
        "input_cost_per_token": 3e-06,
        "output_cost_per_token": 6e-06,
        "litellm_provider": "openai",
    },
    "ft:gpt-3.5-turbo-0125": {
        "input_cost_per_token": 3e-06,
        "output_cost_per_token": 6e-06,
        "litellm_provider": "openai",
    },
    "ft:gpt-3.5-turbo-0613": {
        "input_cost_per_token": 3e-06,
        "output_cost_per_token": 6e-06,
        "litellm_provider": "openai",
    },
    "ft:gpt-3.5-turbo-1106": {
        "input_cost_per_token": 3e-06,
        "output_cost_per_token": 6e-06,
        "litellm_provider": "openai",
    },
    "ft:gpt-4-0613": {
        "input_cost_per_token": 3e-05,
        "output_cost_per_token": 6e-05,
        "litellm_provider": "openai",
    },
    "ft:gpt-4.1-2025-04-14": {
        "input_cost_per_token": 3e-06,
        "output_cost_per_token": 1.2e-05,
        "cache_read_input_token_cost": 7.5e-07,
        "litellm_provider": "openai",
    },
    "ft:gpt-4.1-mini-2025-04-14": {
        "input_cost_per_token": 8e-07,
        "output_cost_per_token": 3.2e-06,
        "cache_read_input_token_cost": 2e-07,
        "litellm_provider": "openai",
    },
    "ft:gpt-4.1-nano-2025-04-14": {
        "input_cost_per_token": 2e-07,
        "output_cost_per_token": 8e-07,
        "cache_read_input_token_cost": 5e-08,
        "litellm_provider": "openai",
    },
    "ft:gpt-4o-2024-08-06": {
        "input_cost_per_token": 3.75e-06,
        "output_cost_per_token": 1.5e-05,
        "cache_read_input_token_cost": 1.875e-06,
        "litellm_provider": "openai",
    },
    "ft:gpt-4o-2024-11-20": {
        "input_cost_per_token": 3.75e-06,
        "output_cost_per_token": 1.5e-05,
        "cache_creation_input_token_cost": 1.875e-06,
        "litellm_provider": "openai",
    },
    "ft:gpt-4o-mini-2024-07-18": {
        "input_cost_per_token": 3e-07,
        "output_cost_per_token": 1.2e-06,
        "cache_read_input_token_cost": 1.5e-07,
        "litellm_provider": "openai",
    },
    "ft:o4-mini-2025-04-16": {
        "input_cost_per_token": 4e-06,
        "output_cost_per_token": 1.6e-05,
        "cache_read_input_token_cost": 1e-06,
        "litellm_provider": "openai",
    },
    "gpt-3.5-turbo": {
        "input_cost_per_token": 5e-07,
        "output_cost_per_token": 1.5e-06,
        "litellm_provider": "openai",
    },
    "gpt-3.5-turbo-0125": {
        "input_cost_per_token": 5e-07,
        "output_cost_per_token": 1.5e-06,
        "litellm_provider": "openai",
    },
    "gpt-3.5-turbo-1106": {
        "input_cost_per_token": 1e-06,
        "output_cost_per_token": 2e-06,
        "litellm_provider": "openai",
    },
    "gpt-3.5-turbo-16k": {
        "input_cost_per_token": 3e-06,
        "output_cost_per_token": 4e-06,
        "litellm_provider": "openai",
    },
    "gpt-4": {
        "input_cost_per_token": 3e-05,
        "output_cost_per_token": 6e-05,
        "litellm_provider": "openai",
    },
    "gpt-4-0125-preview": {
        "input_cost_per_token": 1e-05,
        "output_cost_per_token": 3e-05,
        "litellm_provider": "openai",
    },
    "gpt-4-0314": {
        "input_cost_per_token": 3e-05,
        "output_cost_per_token": 6e-05,
        "litellm_provider": "openai",
    },
    "gpt-4-0613": {
        "input_cost_per_token": 3e-05,
        "output_cost_per_token": 6e-05,
        "litellm_provider": "openai",
    },
    "gpt-4-1106-preview": {
        "input_cost_per_token": 1e-05,
        "output_cost_per_token": 3e-05,
        "litellm_provider": "openai",
    },
    "gpt-4-turbo": {
        "input_cost_per_token": 1e-05,
        "output_cost_per_token": 3e-05,
        "litellm_provider": "openai",
    },
    "gpt-4-turbo-2024-04-09": {
        "input_cost_per_token": 1e-05,
        "output_cost_per_token": 3e-05,
        "litellm_provider": "openai",
    },
    "gpt-4-turbo-preview": {
        "input_cost_per_token": 1e-05,
        "output_cost_per_token": 3e-05,
        "litellm_provider": "openai",
    },
    "gpt-4.1": {
        "input_cost_per_token": 2e-06,
        "output_cost_per_token": 8e-06,
        "cache_read_input_token_cost": 5e-07,
        "litellm_provider": "openai",
    },
    "gpt-4.1-2025-04-14": {
        "input_cost_per_token": 2e-06,
        "output_cost_per_token": 8e-06,
        "cache_read_input_token_cost": 5e-07,
        "litellm_provider": "openai",
    },
    "gpt-4.1-mini": {
        "input_cost_per_token": 4e-07,
        "output_cost_per_token": 1.6e-06,
        "cache_read_input_token_cost": 1e-07,
        "litellm_provider": "openai",
    },
    "gpt-4.1-mini-2025-04-14": {
        "input_cost_per_token": 4e-07,
        "output_cost_per_token": 1.6e-06,
        "cache_read_input_token_cost": 1e-07,
        "litellm_provider": "openai",
    },
    "gpt-4.1-nano": {
        "input_cost_per_token": 1e-07,
        "output_cost_per_token": 4e-07,
        "cache_read_input_token_cost": 2.5e-08,
        "litellm_provider": "openai",
    },
    "gpt-4.1-nano-2025-04-14": {
        "input_cost_per_token": 1e-07,
        "output_cost_per_token": 4e-07,
        "cache_read_input_token_cost": 2.5e-08,
        "litellm_provider": "openai",
    },
    "gpt-4o": {
        "input_cost_per_token": 2.5e-06,
        "output_cost_per_token": 1e-05,
        "cache_read_input_token_cost": 1.25e-06,
        "litellm_provider": "openai",
    },
    "gpt-4o-2024-05-13": {
        "input_cost_per_token": 5e-06,
        "output_cost_per_token": 1.5e-05,
        "litellm_provider": "openai",
    },
    "gpt-4o-2024-08-06": {
        "input_cost_per_token": 2.5e-06,
        "output_cost_per_token": 1e-05,
        "cache_read_input_token_cost": 1.25e-06,
        "litellm_provider": "openai",
    },
    "gpt-4o-2024-11-20": {
        "input_cost_per_token": 2.5e-06,
        "output_cost_per_token": 1e-05,
        "cache_read_input_token_cost": 1.25e-06,
        "litellm_provider": "openai",
    },
    "gpt-4o-audio-preview": {
        "input_cost_per_token": 2.5e-06,
        "output_cost_per_token": 1e-05,
        "litellm_provider": "openai",
    },
    "gpt-4o-audio-preview-2024-12-17": {
        "input_cost_per_token": 2.5e-06,
        "output_cost_per_token": 1e-05,
        "litellm_provider": "openai",
    },
    "gpt-4o-audio-preview-2025-06-03": {
        "input_cost_per_token": 2.5e-06,
        "output_cost_per_token": 1e-05,
        "litellm_provider": "openai",
    },
    "gpt-4o-mini": {
        "input_cost_per_token": 1.5e-07,
        "output_cost_per_token": 6e-07,
        "cache_read_input_token_cost": 7.5e-08,
        "litellm_provider": "openai",
    },
    "gpt-4o-mini-2024-07-18": {
        "input_cost_per_token": 1.5e-07,
        "output_cost_per_token": 6e-07,
        "cache_read_input_token_cost": 7.5e-08,
        "litellm_provider": "openai",
    },
    "gpt-4o-mini-audio-preview": {
        "input_cost_per_token": 1.5e-07,
        "output_cost_per_token": 6e-07,
        "litellm_provider": "openai",
    },
    "gpt-4o-mini-audio-preview-2024-12-17": {
        "input_cost_per_token": 1.5e-07,
        "output_cost_per_token": 6e-07,
        "litellm_provider": "openai",
    },
    "gpt-4o-mini-realtime-preview": {
        "input_cost_per_token": 6e-07,
        "output_cost_per_token": 2.4e-06,
        "cache_read_input_token_cost": 3e-07,
        "litellm_provider": "openai",
    },
    "gpt-4o-mini-realtime-preview-2024-12-17": {
        "input_cost_per_token": 6e-07,
        "output_cost_per_token": 2.4e-06,
        "cache_read_input_token_cost": 3e-07,
        "litellm_provider": "openai",
    },
    "gpt-4o-mini-search-preview": {
        "input_cost_per_token": 1.5e-07,
        "output_cost_per_token": 6e-07,
        "cache_read_input_token_cost": 7.5e-08,
        "litellm_provider": "openai",
    },
    "gpt-4o-mini-search-preview-2025-03-11": {
        "input_cost_per_token": 1.5e-07,
        "output_cost_per_token": 6e-07,
        "cache_read_input_token_cost": 7.5e-08,
        "litellm_provider": "openai",
    },
    "gpt-4o-mini-transcribe": {
        "input_cost_per_token": 1.25e-06,
        "output_cost_per_token": 5e-06,
        "litellm_provider": "openai",
    },
    "gpt-4o-mini-transcribe-2025-03-20": {
        "input_cost_per_token": 1.25e-06,
        "output_cost_per_token": 5e-06,
        "litellm_provider": "openai",
    },
    "gpt-4o-mini-transcribe-2025-12-15": {
        "input_cost_per_token": 1.25e-06,
        "output_cost_per_token": 5e-06,
        "litellm_provider": "openai",
    },
    "gpt-4o-mini-tts": {
        "input_cost_per_token": 2.5e-06,
        "output_cost_per_token": 1e-05,
        "litellm_provider": "openai",
    },
    "gpt-4o-mini-tts-2025-03-20": {
        "input_cost_per_token": 2.5e-06,
        "output_cost_per_token": 1e-05,
        "litellm_provider": "openai",
    },
    "gpt-4o-mini-tts-2025-12-15": {
        "input_cost_per_token": 2.5e-06,
        "output_cost_per_token": 1e-05,
        "litellm_provider": "openai",
    },
    "gpt-4o-realtime-preview": {
        "input_cost_per_token": 5e-06,
        "output_cost_per_token": 2e-05,
        "cache_read_input_token_cost": 2.5e-06,
        "litellm_provider": "openai",
    },
    "gpt-4o-realtime-preview-2024-12-17": {
        "input_cost_per_token": 5e-06,
        "output_cost_per_token": 2e-05,
        "cache_read_input_token_cost": 2.5e-06,
        "litellm_provider": "openai",
    },
    "gpt-4o-realtime-preview-2025-06-03": {
        "input_cost_per_token": 5e-06,
        "output_cost_per_token": 2e-05,
        "cache_read_input_token_cost": 2.5e-06,
        "litellm_provider": "openai",
    },
    "gpt-4o-search-preview": {
        "input_cost_per_token": 2.5e-06,
        "output_cost_per_token": 1e-05,
        "cache_read_input_token_cost": 1.25e-06,
        "litellm_provider": "openai",
    },
    "gpt-4o-search-preview-2025-03-11": {
        "input_cost_per_token": 2.5e-06,
        "output_cost_per_token": 1e-05,
        "cache_read_input_token_cost": 1.25e-06,
        "litellm_provider": "openai",
    },
    "gpt-4o-transcribe": {
        "input_cost_per_token": 2.5e-06,
        "output_cost_per_token": 1e-05,
        "litellm_provider": "openai",
    },
    "gpt-4o-transcribe-diarize": {
        "input_cost_per_token": 2.5e-06,
        "output_cost_per_token": 1e-05,
        "litellm_provider": "openai",
    },
    "gpt-5": {
        "input_cost_per_token": 1.25e-06,
        "output_cost_per_token": 1e-05,
        "cache_read_input_token_cost": 1.25e-07,
        "litellm_provider": "openai",
    },
    "gpt-5-2025-08-07": {
        "input_cost_per_token": 1.25e-06,
        "output_cost_per_token": 1e-05,
        "cache_read_input_token_cost": 1.25e-07,
        "litellm_provider": "openai",
    },
    "gpt-5-chat": {
        "input_cost_per_token": 1.25e-06,
        "output_cost_per_token": 1e-05,
        "cache_read_input_token_cost": 1.25e-07,
        "litellm_provider": "openai",
    },
    "gpt-5-chat-latest": {
        "input_cost_per_token": 1.25e-06,
        "output_cost_per_token": 1e-05,
        "cache_read_input_token_cost": 1.25e-07,
        "litellm_provider": "openai",
    },
    "gpt-5-codex": {
        "input_cost_per_token": 1.25e-06,
        "output_cost_per_token": 1e-05,
        "cache_read_input_token_cost": 1.25e-07,
        "litellm_provider": "openai",
    },
    "gpt-5-mini": {
        "input_cost_per_token": 2.5e-07,
        "output_cost_per_token": 2e-06,
        "cache_read_input_token_cost": 2.5e-08,
        "litellm_provider": "openai",
    },
    "gpt-5-mini-2025-08-07": {
        "input_cost_per_token": 2.5e-07,
        "output_cost_per_token": 2e-06,
        "cache_read_input_token_cost": 2.5e-08,
        "litellm_provider": "openai",
    },
    "gpt-5-nano": {
        "input_cost_per_token": 5e-08,
        "output_cost_per_token": 4e-07,
        "cache_read_input_token_cost": 5e-09,
        "litellm_provider": "openai",
    },
    "gpt-5-nano-2025-08-07": {
        "input_cost_per_token": 5e-08,
        "output_cost_per_token": 4e-07,
        "cache_read_input_token_cost": 5e-09,
        "litellm_provider": "openai",
    },
    "gpt-5-pro": {
        "input_cost_per_token": 1.5e-05,
        "output_cost_per_token": 0.00012,
        "litellm_provider": "openai",
    },
    "gpt-5-pro-2025-10-06": {
        "input_cost_per_token": 1.5e-05,
        "output_cost_per_token": 0.00012,
        "litellm_provider": "openai",
    },
    "gpt-5-search-api": {
        "input_cost_per_token": 1.25e-06,
        "output_cost_per_token": 1e-05,
        "cache_read_input_token_cost": 1.25e-07,
        "litellm_provider": "openai",
    },
    "gpt-5-search-api-2025-10-14": {
        "input_cost_per_token": 1.25e-06,
        "output_cost_per_token": 1e-05,
        "cache_read_input_token_cost": 1.25e-07,
        "litellm_provider": "openai",
    },
    "gpt-5.1": {
        "input_cost_per_token": 1.25e-06,
        "output_cost_per_token": 1e-05,
        "cache_read_input_token_cost": 1.25e-07,
        "litellm_provider": "openai",
    },
    "gpt-5.1-2025-11-13": {
        "input_cost_per_token": 1.25e-06,
        "output_cost_per_token": 1e-05,
        "cache_read_input_token_cost": 1.25e-07,
        "litellm_provider": "openai",
    },
    "gpt-5.1-chat-latest": {
        "input_cost_per_token": 1.25e-06,
        "output_cost_per_token": 1e-05,
        "cache_read_input_token_cost": 1.25e-07,
        "litellm_provider": "openai",
    },
    "gpt-5.1-codex": {
        "input_cost_per_token": 1.25e-06,
        "output_cost_per_token": 1e-05,
        "cache_read_input_token_cost": 1.25e-07,
        "litellm_provider": "openai",
    },
    "gpt-5.1-codex-max": {
        "input_cost_per_token": 1.25e-06,
        "output_cost_per_token": 1e-05,
        "cache_read_input_token_cost": 1.25e-07,
        "litellm_provider": "openai",
    },
    "gpt-5.1-codex-mini": {
        "input_cost_per_token": 2.5e-07,
        "output_cost_per_token": 2e-06,
        "cache_read_input_token_cost": 2.5e-08,
        "litellm_provider": "openai",
    },
    "gpt-5.2": {
        "input_cost_per_token": 1.75e-06,
        "output_cost_per_token": 1.4e-05,
        "cache_read_input_token_cost": 1.75e-07,
        "litellm_provider": "openai",
    },
    "gpt-5.2-2025-12-11": {
        "input_cost_per_token": 1.75e-06,
        "output_cost_per_token": 1.4e-05,
        "cache_read_input_token_cost": 1.75e-07,
        "litellm_provider": "openai",
    },
    "gpt-5.2-chat-latest": {
        "input_cost_per_token": 1.75e-06,
        "output_cost_per_token": 1.4e-05,
        "cache_read_input_token_cost": 1.75e-07,
        "litellm_provider": "openai",
    },
    "gpt-5.2-codex": {
        "input_cost_per_token": 1.75e-06,
        "output_cost_per_token": 1.4e-05,
        "cache_read_input_token_cost": 1.75e-07,
        "litellm_provider": "openai",
    },
    "gpt-5.2-pro": {
        "input_cost_per_token": 2.1e-05,
        "output_cost_per_token": 0.000168,
        "litellm_provider": "openai",
    },
    "gpt-5.2-pro-2025-12-11": {
        "input_cost_per_token": 2.1e-05,
        "output_cost_per_token": 0.000168,
        "litellm_provider": "openai",
    },
    "gpt-5.3-chat-latest": {
        "input_cost_per_token": 1.75e-06,
        "output_cost_per_token": 1.4e-05,
        "cache_read_input_token_cost": 1.75e-07,
        "litellm_provider": "openai",
    },
    "gpt-5.3-codex": {
        "input_cost_per_token": 1.75e-06,
        "output_cost_per_token": 1.4e-05,
        "cache_read_input_token_cost": 1.75e-07,
        "litellm_provider": "openai",
    },
    "gpt-5.4": {
        "input_cost_per_token": 2.5e-06,
        "output_cost_per_token": 1.5e-05,
        "cache_read_input_token_cost": 2.5e-07,
        "litellm_provider": "openai",
    },
    "gpt-5.4-2026-03-05": {
        "input_cost_per_token": 2.5e-06,
        "output_cost_per_token": 1.5e-05,
        "cache_read_input_token_cost": 2.5e-07,
        "litellm_provider": "openai",
    },
    "gpt-5.4-mini": {
        "input_cost_per_token": 7.5e-07,
        "output_cost_per_token": 4.5e-06,
        "cache_read_input_token_cost": 7.5e-08,
        "litellm_provider": "openai",
    },
    "gpt-5.4-nano": {
        "input_cost_per_token": 2e-07,
        "output_cost_per_token": 1.25e-06,
        "cache_read_input_token_cost": 2e-08,
        "litellm_provider": "openai",
    },
    "gpt-5.4-pro": {
        "input_cost_per_token": 3e-05,
        "output_cost_per_token": 0.00018,
        "cache_read_input_token_cost": 3e-06,
        "litellm_provider": "openai",
    },
    "gpt-5.4-pro-2026-03-05": {
        "input_cost_per_token": 3e-05,
        "output_cost_per_token": 0.00018,
        "cache_read_input_token_cost": 3e-06,
        "litellm_provider": "openai",
    },
    "gpt-5.5": {
        "input_cost_per_token": 5e-06,
        "output_cost_per_token": 3e-05,
        "cache_read_input_token_cost": 5e-07,
        "litellm_provider": "openai",
    },
    "gpt-5.5-2026-04-23": {
        "input_cost_per_token": 5e-06,
        "output_cost_per_token": 3e-05,
        "cache_read_input_token_cost": 5e-07,
        "litellm_provider": "openai",
    },
    "gpt-5.5-pro": {
        "input_cost_per_token": 6e-05,
        "output_cost_per_token": 0.00036,
        "cache_read_input_token_cost": 6e-06,
        "litellm_provider": "openai",
    },
    "gpt-5.5-pro-2026-04-23": {
        "input_cost_per_token": 6e-05,
        "output_cost_per_token": 0.00036,
        "cache_read_input_token_cost": 6e-06,
        "litellm_provider": "openai",
    },
    "gpt-audio": {
        "input_cost_per_token": 2.5e-06,
        "output_cost_per_token": 1e-05,
        "litellm_provider": "openai",
    },
    "gpt-audio-1.5": {
        "input_cost_per_token": 2.5e-06,
        "output_cost_per_token": 1e-05,
        "litellm_provider": "openai",
    },
    "gpt-audio-2025-08-28": {
        "input_cost_per_token": 2.5e-06,
        "output_cost_per_token": 1e-05,
        "litellm_provider": "openai",
    },
    "gpt-audio-mini": {
        "input_cost_per_token": 6e-07,
        "output_cost_per_token": 2.4e-06,
        "litellm_provider": "openai",
    },
    "gpt-audio-mini-2025-10-06": {
        "input_cost_per_token": 6e-07,
        "output_cost_per_token": 2.4e-06,
        "litellm_provider": "openai",
    },
    "gpt-audio-mini-2025-12-15": {
        "input_cost_per_token": 6e-07,
        "output_cost_per_token": 2.4e-06,
        "litellm_provider": "openai",
    },
    "gpt-image-1.5": {
        "input_cost_per_token": 5e-06,
        "output_cost_per_token": 1e-05,
        "cache_read_input_token_cost": 1.25e-06,
        "litellm_provider": "openai",
    },
    "gpt-image-1.5-2025-12-16": {
        "input_cost_per_token": 5e-06,
        "output_cost_per_token": 1e-05,
        "cache_read_input_token_cost": 1.25e-06,
        "litellm_provider": "openai",
    },
    "gpt-realtime": {
        "input_cost_per_token": 4e-06,
        "output_cost_per_token": 1.6e-05,
        "cache_read_input_token_cost": 4e-07,
        "litellm_provider": "openai",
    },
    "gpt-realtime-1.5": {
        "input_cost_per_token": 4e-06,
        "output_cost_per_token": 1.6e-05,
        "cache_read_input_token_cost": 4e-07,
        "litellm_provider": "openai",
    },
    "gpt-realtime-2025-08-28": {
        "input_cost_per_token": 4e-06,
        "output_cost_per_token": 1.6e-05,
        "cache_read_input_token_cost": 4e-07,
        "litellm_provider": "openai",
    },
    "gpt-realtime-mini": {
        "input_cost_per_token": 6e-07,
        "output_cost_per_token": 2.4e-06,
        "litellm_provider": "openai",
    },
    "gpt-realtime-mini-2025-10-06": {
        "input_cost_per_token": 6e-07,
        "output_cost_per_token": 2.4e-06,
        "cache_read_input_token_cost": 6e-08,
        "litellm_provider": "openai",
    },
    "gpt-realtime-mini-2025-12-15": {
        "input_cost_per_token": 6e-07,
        "output_cost_per_token": 2.4e-06,
        "cache_read_input_token_cost": 6e-08,
        "litellm_provider": "openai",
    },
    "o1": {
        "input_cost_per_token": 1.5e-05,
        "output_cost_per_token": 6e-05,
        "cache_read_input_token_cost": 7.5e-06,
        "litellm_provider": "openai",
    },
    "o1-2024-12-17": {
        "input_cost_per_token": 1.5e-05,
        "output_cost_per_token": 6e-05,
        "cache_read_input_token_cost": 7.5e-06,
        "litellm_provider": "openai",
    },
    "o1-pro": {
        "input_cost_per_token": 0.00015,
        "output_cost_per_token": 0.0006,
        "litellm_provider": "openai",
    },
    "o1-pro-2025-03-19": {
        "input_cost_per_token": 0.00015,
        "output_cost_per_token": 0.0006,
        "litellm_provider": "openai",
    },
    "o3": {
        "input_cost_per_token": 2e-06,
        "output_cost_per_token": 8e-06,
        "cache_read_input_token_cost": 5e-07,
        "litellm_provider": "openai",
    },
    "o3-2025-04-16": {
        "input_cost_per_token": 2e-06,
        "output_cost_per_token": 8e-06,
        "cache_read_input_token_cost": 5e-07,
        "litellm_provider": "openai",
    },
    "o3-deep-research": {
        "input_cost_per_token": 1e-05,
        "output_cost_per_token": 4e-05,
        "cache_read_input_token_cost": 2.5e-06,
        "litellm_provider": "openai",
    },
    "o3-deep-research-2025-06-26": {
        "input_cost_per_token": 1e-05,
        "output_cost_per_token": 4e-05,
        "cache_read_input_token_cost": 2.5e-06,
        "litellm_provider": "openai",
    },
    "o3-mini": {
        "input_cost_per_token": 1.1e-06,
        "output_cost_per_token": 4.4e-06,
        "cache_read_input_token_cost": 5.5e-07,
        "litellm_provider": "openai",
    },
    "o3-mini-2025-01-31": {
        "input_cost_per_token": 1.1e-06,
        "output_cost_per_token": 4.4e-06,
        "cache_read_input_token_cost": 5.5e-07,
        "litellm_provider": "openai",
    },
    "o3-pro": {
        "input_cost_per_token": 2e-05,
        "output_cost_per_token": 8e-05,
        "litellm_provider": "openai",
    },
    "o3-pro-2025-06-10": {
        "input_cost_per_token": 2e-05,
        "output_cost_per_token": 8e-05,
        "litellm_provider": "openai",
    },
    "o4-mini": {
        "input_cost_per_token": 1.1e-06,
        "output_cost_per_token": 4.4e-06,
        "cache_read_input_token_cost": 2.75e-07,
        "litellm_provider": "openai",
    },
    "o4-mini-2025-04-16": {
        "input_cost_per_token": 1.1e-06,
        "output_cost_per_token": 4.4e-06,
        "cache_read_input_token_cost": 2.75e-07,
        "litellm_provider": "openai",
    },
    "o4-mini-deep-research": {
        "input_cost_per_token": 2e-06,
        "output_cost_per_token": 8e-06,
        "cache_read_input_token_cost": 5e-07,
        "litellm_provider": "openai",
    },
    "o4-mini-deep-research-2025-06-26": {
        "input_cost_per_token": 2e-06,
        "output_cost_per_token": 8e-06,
        "cache_read_input_token_cost": 5e-07,
        "litellm_provider": "openai",
    },
    "omni-moderation-2024-09-26": {
        "input_cost_per_token": 0.0,
        "output_cost_per_token": 0.0,
        "litellm_provider": "openai",
    },
    "omni-moderation-latest": {
        "input_cost_per_token": 0.0,
        "output_cost_per_token": 0.0,
        "litellm_provider": "openai",
    },
    "text-embedding-3-large": {
        "input_cost_per_token": 1.3e-07,
        "output_cost_per_token": 0.0,
        "litellm_provider": "openai",
    },
    "text-embedding-3-small": {
        "input_cost_per_token": 2e-08,
        "output_cost_per_token": 0.0,
        "litellm_provider": "openai",
    },
    "text-embedding-ada-002": {
        "input_cost_per_token": 1e-07,
        "output_cost_per_token": 0.0,
        "litellm_provider": "openai",
    },
    "text-embedding-ada-002-v2": {
        "input_cost_per_token": 1e-07,
        "output_cost_per_token": 0.0,
        "litellm_provider": "openai",
    },
    "text-moderation-007": {
        "input_cost_per_token": 0.0,
        "output_cost_per_token": 0.0,
        "litellm_provider": "openai",
    },
    "text-moderation-latest": {
        "input_cost_per_token": 0.0,
        "output_cost_per_token": 0.0,
        "litellm_provider": "openai",
    },
    "text-moderation-stable": {
        "input_cost_per_token": 0.0,
        "output_cost_per_token": 0.0,
        "litellm_provider": "openai",
    },
    # ── Google ──
    "deep-research-pro-preview-12-2025": {
        "input_cost_per_token": 2e-06,
        "output_cost_per_token": 1.2e-05,
        "litellm_provider": "google",
    },
    "gemini-2.0-flash": {
        "input_cost_per_token": 1e-07,
        "output_cost_per_token": 4e-07,
        "cache_read_input_token_cost": 2.5e-08,
        "litellm_provider": "google",
    },
    "gemini-2.0-flash-001": {
        "input_cost_per_token": 1.5e-07,
        "output_cost_per_token": 6e-07,
        "cache_read_input_token_cost": 3.75e-08,
        "litellm_provider": "google",
    },
    "gemini-2.0-flash-lite": {
        "input_cost_per_token": 7.5e-08,
        "output_cost_per_token": 3e-07,
        "cache_read_input_token_cost": 1.875e-08,
        "litellm_provider": "google",
    },
    "gemini-2.0-flash-lite-001": {
        "input_cost_per_token": 7.5e-08,
        "output_cost_per_token": 3e-07,
        "cache_read_input_token_cost": 1.875e-08,
        "litellm_provider": "google",
    },
    "gemini-2.5-computer-use-preview-10-2025": {
        "input_cost_per_token": 1.25e-06,
        "output_cost_per_token": 1e-05,
        "litellm_provider": "google",
    },
    "gemini-2.5-flash": {
        "input_cost_per_token": 3e-07,
        "output_cost_per_token": 2.5e-06,
        "cache_read_input_token_cost": 3e-08,
        "litellm_provider": "google",
    },
    "gemini-2.5-flash-image": {
        "input_cost_per_token": 3e-07,
        "output_cost_per_token": 2.5e-06,
        "cache_read_input_token_cost": 3e-08,
        "litellm_provider": "google",
    },
    "gemini-2.5-flash-lite": {
        "input_cost_per_token": 1e-07,
        "output_cost_per_token": 4e-07,
        "cache_read_input_token_cost": 1e-08,
        "litellm_provider": "google",
    },
    "gemini-2.5-flash-lite-preview-06-17": {
        "input_cost_per_token": 1e-07,
        "output_cost_per_token": 4e-07,
        "cache_read_input_token_cost": 2.5e-08,
        "litellm_provider": "google",
    },
    "gemini-2.5-flash-lite-preview-09-2025": {
        "input_cost_per_token": 1e-07,
        "output_cost_per_token": 4e-07,
        "cache_read_input_token_cost": 1e-08,
        "litellm_provider": "google",
    },
    "gemini-2.5-flash-preview-09-2025": {
        "input_cost_per_token": 3e-07,
        "output_cost_per_token": 2.5e-06,
        "cache_read_input_token_cost": 7.5e-08,
        "litellm_provider": "google",
    },
    "gemini-2.5-pro": {
        "input_cost_per_token": 1.25e-06,
        "output_cost_per_token": 1e-05,
        "cache_read_input_token_cost": 1.25e-07,
        "litellm_provider": "google",
    },
    "gemini-2.5-pro-preview-tts": {
        "input_cost_per_token": 1.25e-06,
        "output_cost_per_token": 1e-05,
        "cache_read_input_token_cost": 1.25e-07,
        "litellm_provider": "google",
    },
    "gemini-3-flash-preview": {
        "input_cost_per_token": 5e-07,
        "output_cost_per_token": 3e-06,
        "cache_read_input_token_cost": 5e-08,
        "litellm_provider": "google",
    },
    "gemini-3-pro-image-preview": {
        "input_cost_per_token": 2e-06,
        "output_cost_per_token": 1.2e-05,
        "litellm_provider": "google",
    },
    "gemini-3-pro-preview": {
        "input_cost_per_token": 2e-06,
        "output_cost_per_token": 1.2e-05,
        "cache_read_input_token_cost": 2e-07,
        "litellm_provider": "google",
    },
    "gemini-3.1-flash-image-preview": {
        "input_cost_per_token": 5e-07,
        "output_cost_per_token": 3e-06,
        "litellm_provider": "google",
    },
    "gemini-3.1-flash-lite-preview": {
        "input_cost_per_token": 2.5e-07,
        "output_cost_per_token": 1.5e-06,
        "cache_read_input_token_cost": 2.5e-08,
        "litellm_provider": "google",
    },
    "gemini-3.1-pro-preview": {
        "input_cost_per_token": 2e-06,
        "output_cost_per_token": 1.2e-05,
        "cache_read_input_token_cost": 2e-07,
        "litellm_provider": "google",
    },
    "gemini-3.1-pro-preview-customtools": {
        "input_cost_per_token": 2e-06,
        "output_cost_per_token": 1.2e-05,
        "cache_read_input_token_cost": 2e-07,
        "litellm_provider": "google",
    },
    "gemini-flash-experimental": {
        "input_cost_per_token": 0,
        "output_cost_per_token": 0,
        "litellm_provider": "google",
    },
    "gemini-live-2.5-flash-preview-native-audio-09-2025": {
        "input_cost_per_token": 3e-07,
        "output_cost_per_token": 2e-06,
        "cache_read_input_token_cost": 7.5e-08,
        "litellm_provider": "google",
    },
    "gemini-robotics-er-1.5-preview": {
        "input_cost_per_token": 3e-07,
        "output_cost_per_token": 2.5e-06,
        "cache_read_input_token_cost": 0,
        "litellm_provider": "google",
    },
    "vertex_ai/deep-research-pro-preview-12-2025": {
        "input_cost_per_token": 2e-06,
        "output_cost_per_token": 1.2e-05,
        "litellm_provider": "google",
    },
    "vertex_ai/gemini-2.5-flash-image": {
        "input_cost_per_token": 3e-07,
        "output_cost_per_token": 2.5e-06,
        "cache_read_input_token_cost": 3e-08,
        "litellm_provider": "google",
    },
    "vertex_ai/gemini-3-pro-image-preview": {
        "input_cost_per_token": 2e-06,
        "output_cost_per_token": 1.2e-05,
        "litellm_provider": "google",
    },
    "vertex_ai/gemini-3.1-flash-image-preview": {
        "input_cost_per_token": 5e-07,
        "output_cost_per_token": 3e-06,
        "litellm_provider": "google",
    },
    "vertex_ai/gemini-3.1-flash-lite-preview": {
        "input_cost_per_token": 2.5e-07,
        "output_cost_per_token": 1.5e-06,
        "cache_read_input_token_cost": 2.5e-08,
        "litellm_provider": "google",
    },
}
# fmt: on

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
