"""Tests for the pricing / cost computation module."""

from __future__ import annotations


from amplifier_module_hook_observability.pricing import PRICING, compute_cost, _lookup


# ---------------------------------------------------------------------------
# _lookup
# ---------------------------------------------------------------------------


class TestLookup:
    def test_exact_match(self):
        rates = _lookup("claude-opus-4")
        assert rates == PRICING["claude-opus-4"]

    def test_prefix_match(self):
        # Model names often include version suffixes
        rates = _lookup("claude-sonnet-4-5")
        assert rates == PRICING["claude-sonnet-4"]

    def test_case_insensitive(self):
        rates = _lookup("CLAUDE-OPUS-4")
        assert rates == PRICING["claude-opus-4"]

    def test_unknown_model_returns_none(self):
        assert _lookup("gpt-unknown-9000") is None

    def test_longest_prefix_wins(self):
        # claude-3-5-sonnet should match over claude-3-sonnet
        rates = _lookup("claude-3-5-sonnet-20241022")
        assert rates == PRICING["claude-3-5-sonnet"]

    def test_openai_model(self):
        rates = _lookup("gpt-4o-mini")
        assert rates == PRICING["gpt-4o-mini"]

    def test_gemini_model(self):
        rates = _lookup("gemini-2.5-pro-preview")
        assert rates == PRICING["gemini-2.5-pro"]


# ---------------------------------------------------------------------------
# compute_cost
# ---------------------------------------------------------------------------


class TestComputeCost:
    def test_basic_cost(self):
        # claude-sonnet-4: $3.00/$15.00 per MTok
        cost = compute_cost(
            "claude-sonnet-4-5", input_tokens=1_000_000, output_tokens=1_000_000
        )
        assert abs(cost - 18.0) < 0.001  # $3 + $15

    def test_unknown_model_returns_zero(self):
        cost = compute_cost("unknown-model-x", 1000, 1000)
        assert cost == 0.0

    def test_zero_tokens(self):
        cost = compute_cost("claude-sonnet-4-5", 0, 0)
        assert cost == 0.0

    def test_cache_read_tokens(self):
        # cache_read = 10% of input rate
        # claude-sonnet-4: $3.00/MTok input
        # 1M cache_read_tokens = $0.30
        cost = compute_cost(
            "claude-sonnet-4",
            input_tokens=0,
            output_tokens=0,
            cache_read_tokens=1_000_000,
        )
        assert abs(cost - 0.30) < 0.001

    def test_cache_write_tokens(self):
        # cache_write = 25% of input rate
        # claude-sonnet-4: $3.00/MTok input → $0.75/MTok write
        cost = compute_cost(
            "claude-sonnet-4",
            input_tokens=0,
            output_tokens=0,
            cache_write_tokens=1_000_000,
        )
        assert abs(cost - 0.75) < 0.001

    def test_reasoning_tokens_billed_at_output_rate(self):
        # claude-sonnet-4: $15.00/MTok output
        cost_output = compute_cost("claude-sonnet-4", 0, 1_000_000)
        cost_reasoning = compute_cost(
            "claude-sonnet-4", 0, 0, reasoning_tokens=1_000_000
        )
        assert abs(cost_output - cost_reasoning) < 0.001

    def test_combined_tokens(self):
        # Ensure all token types sum correctly
        in_rate, out_rate = PRICING["claude-opus-4"]
        per_in = in_rate / 1_000_000
        per_out = out_rate / 1_000_000
        expected = (
            100 * per_in
            + 50 * per_out
            + 20 * per_out  # reasoning at output rate
            + 10 * per_in * 0.10  # cache_read
            + 5 * per_in * 0.25  # cache_write
        )
        cost = compute_cost(
            "claude-opus-4",
            100,
            50,
            cache_read_tokens=10,
            cache_write_tokens=5,
            reasoning_tokens=20,
        )
        assert abs(cost - expected) < 1e-10
