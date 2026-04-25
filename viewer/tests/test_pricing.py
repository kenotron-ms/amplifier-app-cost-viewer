"""Tests for pricing.py — written FIRST before file exists (TDD RED).

Imports UNKNOWN_COLOR, compute_cost, get_model_color from
amplifier_app_cost_viewer.pricing.  All tests are RED until pricing.py
is implemented.
"""

from __future__ import annotations

from amplifier_app_cost_viewer.pricing import (
    UNKNOWN_COLOR,
    compute_cost,
    get_model_color,
)

ONE_MILLION = 1_000_000


class TestComputeCost:
    """9 tests covering cost calculation across token types and models."""

    def test_claude_sonnet_basic_cost(self):
        """claude-sonnet-4-5: $3.00/MTok input + $15.00/MTok output, 1M each = $18.00."""
        cost = compute_cost("claude-sonnet-4-5", ONE_MILLION, ONE_MILLION)
        assert abs(cost - 18.00) < 0.001

    def test_unknown_model_returns_zero(self):
        """A completely unrecognised model name returns 0.0."""
        cost = compute_cost(
            "completely-unknown-model-xyz-9999", ONE_MILLION, ONE_MILLION
        )
        assert abs(cost - 0.0) < 0.001

    def test_zero_tokens_returns_zero(self):
        """Known model with all-zero token counts returns 0.0."""
        cost = compute_cost("claude-sonnet-4-5", 0, 0)
        assert abs(cost - 0.0) < 0.001

    def test_cache_read_tokens(self):
        """cache_read costs $0.30/MTok (10% of $3.00 input rate), 1M tokens = $0.30."""
        cost = compute_cost(
            "claude-sonnet-4-5",
            input_tokens=0,
            output_tokens=0,
            cache_read_tokens=ONE_MILLION,
        )
        assert abs(cost - 0.30) < 0.001

    def test_cache_write_tokens(self):
        """cache_write costs $3.75/MTok (125% of $3.00 input rate per LiteLLM), 1M tokens = $3.75."""
        cost = compute_cost(
            "claude-sonnet-4-5",
            input_tokens=0,
            output_tokens=0,
            cache_write_tokens=ONE_MILLION,
        )
        assert abs(cost - 3.75) < 0.001

    def test_gpt4o_cost(self):
        """gpt-4o: $2.50/MTok input, 1M input tokens = $2.50."""
        cost = compute_cost("gpt-4o", ONE_MILLION, 0)
        assert abs(cost - 2.50) < 0.001

    def test_gpt4o_mini_cost(self):
        """gpt-4o-mini: $0.15/MTok input, 1M input tokens = $0.15."""
        cost = compute_cost("gpt-4o-mini", ONE_MILLION, 0)
        assert abs(cost - 0.15) < 0.001

    def test_gemini_flash_cost(self):
        """gemini-2.0-flash: $0.10/MTok input, 1M input tokens = $0.10."""
        cost = compute_cost("gemini-2.0-flash", ONE_MILLION, 0)
        assert abs(cost - 0.10) < 0.001

    def test_all_token_types_sum(self):
        """All 4 token types combined: input $3.00 + output $15.00 + cache_read $0.30 + cache_write $3.75 = $22.05."""
        cost = compute_cost(
            "claude-sonnet-4-5",
            input_tokens=ONE_MILLION,
            output_tokens=ONE_MILLION,
            cache_read_tokens=ONE_MILLION,
            cache_write_tokens=ONE_MILLION,
        )
        assert abs(cost - 22.05) < 0.001


class TestPrefixMatch:
    """4 tests covering longest-prefix model key resolution."""

    def test_exact_key_match(self):
        """An exact key 'claude-sonnet-4-5' resolves to a nonzero cost."""
        cost = compute_cost("claude-sonnet-4-5", ONE_MILLION, 0)
        assert cost > 0.0

    def test_version_suffix_prefix_match(self):
        """'claude-sonnet-4-6-20251001' matches the 'claude-sonnet-4-6' key via prefix."""
        cost_full = compute_cost("claude-sonnet-4-6-20251001", ONE_MILLION, 0)
        cost_base = compute_cost("claude-sonnet-4-6", ONE_MILLION, 0)
        # Both should resolve to the same price via prefix matching
        assert cost_full > 0.0
        assert abs(cost_full - cost_base) < 0.001

    def test_longer_key_wins_over_shorter(self):
        """'claude-haiku-4-5' matches its specific key, not a shorter common prefix."""
        cost = compute_cost("claude-haiku-4-5", ONE_MILLION, 0)
        # Should resolve to claude-haiku-4-5's own pricing, which is lower than opus
        cost_opus = compute_cost("claude-opus-4-5", ONE_MILLION, 0)
        assert cost > 0.0
        assert cost != cost_opus

    def test_truly_unknown_model_is_zero(self):
        """A model with no matching prefix returns 0.0."""
        cost = compute_cost("no-such-model-ever-12345", ONE_MILLION, ONE_MILLION)
        assert abs(cost - 0.0) < 0.001


class TestGetModelColor:
    """5 tests covering provider-based hex color assignment."""

    def test_claude_model_returns_hex_string(self):
        """A Claude model returns a valid CSS hex color string."""
        color = get_model_color("claude-sonnet-4-5")
        assert isinstance(color, str)
        assert color.startswith("#")
        assert len(color) == 7

    def test_gpt_model_returns_hex_string(self):
        """A GPT model returns a valid CSS hex color string."""
        color = get_model_color("gpt-4o")
        assert isinstance(color, str)
        assert color.startswith("#")
        assert len(color) == 7

    def test_different_providers_give_different_colors(self):
        """Anthropic and OpenAI models receive distinct colors."""
        anthropic_color = get_model_color("claude-sonnet-4-5")
        openai_color = get_model_color("gpt-4o")
        assert anthropic_color != openai_color

    def test_unknown_model_returns_unknown_color(self):
        """An unrecognised model returns the UNKNOWN_COLOR sentinel constant."""
        color = get_model_color("totally-unknown-model-xyz")
        assert color == UNKNOWN_COLOR

    def test_haiku_differs_from_opus(self):
        """Different tier models within the same provider have different colors."""
        haiku_color = get_model_color("claude-haiku-4-5")
        opus_color = get_model_color("claude-opus-4-5")
        assert haiku_color != opus_color
