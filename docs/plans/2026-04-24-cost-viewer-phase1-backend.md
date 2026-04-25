# Cost Viewer — Phase 1: Backend Implementation Plan

> **Execution:** Use the subagent-driven-development workflow to implement this plan.

**Goal:** Build the complete Python backend of the `amplifier-cost-viewer` package — package scaffolding, cost computation (`pricing.py`), and the session/span data pipeline (`reader.py`) — with full test coverage, no server routes, no frontend.

**Architecture:** A new independently-installable package lives at `viewer/` inside the existing `token-cost` repo. `pricing.py` owns model cost lookup and color assignment via a static fallback dict (LiteLLM-format, attributed). `reader.py` reads raw `events.jsonl` kernel logs from `~/.amplifier/projects/*/sessions/*/` and produces `Span` and `SessionNode` dataclasses through a five-stage pipeline: discover → parse → cost → aggregate → normalize.

**Tech Stack:** Python 3.11+, hatchling build, pytest + pytest-asyncio, FastAPI + uvicorn (declared as deps, used in Phase 2), `unittest.mock` for mocking, real filesystem for reader tests.

---

## Background: What the event logs look like

Before touching any code, read this. Every `events.jsonl` is a file of newline-delimited JSON records written by the Amplifier kernel's `hooks-logging` module. Each line looks like:

```json
{
  "ts": "2026-04-15T02:13:24.253+00:00",
  "lvl": "INFO",
  "schema": {"name": "amplifier.log", "ver": "1.0.0"},
  "event": "session:start",
  "session_id": "0000000000000000-049740008fcd4c86_foundation-file-ops",
  "data": {"parent_id": "982946ea-6e9f-455f-9f9f-3eaa9014e608", "timestamp": "..."}
}
```

Events we care about, with the fields `reader.py` reads:

| event | top-level fields | `data` fields used |
|---|---|---|
| `session:start` | `ts`, `session_id` | `data.parent_id` (nullable) |
| `session:end` | `ts`, `session_id` | — |
| `provider:request` | `ts`, `session_id` | `data.provider` |
| `llm:response` | `ts`, `session_id`, `duration_ms` | `data.model`, `data.provider`, `data.usage.input`, `data.usage.output`, `data.usage.cache_read`, `data.usage.cache_write` |
| `tool:pre` | `ts`, `session_id` | `data.tool_call_id`, `data.tool_name`, `data.tool_input` |
| `tool:post` | `ts`, `session_id` | `data.tool_call_id`, `data.result.success`, `data.result.output` |
| `thinking:delta` | `ts`, `session_id` | — |
| `thinking:final` | `ts`, `session_id` | — |

And every session directory has a `metadata.json`:

```json
{
  "session_id": "0000000000000000-049740008fcd4c86_foundation-file-ops",
  "parent_id": "982946ea-6e9f-455f-9f9f-3eaa9014e608",
  "agent_name": "foundation:file-ops",
  "created": "2026-04-15T02:13:54.305362+00:00",
  "project_slug": "-Users-ken",
  "project_name": "ken"
}
```

Sessions live at: `~/.amplifier/projects/<project_slug>/sessions/<session_id>/`

---

## File structure to create in Phase 1

```
viewer/
├── pyproject.toml
└── amplifier_app_cost_viewer/
    ├── __init__.py
    ├── __main__.py
    ├── pricing.py
    └── reader.py

viewer/tests/
├── __init__.py
├── conftest.py
├── test_pricing.py
└── test_reader.py
```

Do **not** create `server.py`, `static/`, or `scripts/` — those are Phase 2.

---

## Task 1: Package Scaffold

**Files to create:**
- `viewer/pyproject.toml`
- `viewer/amplifier_app_cost_viewer/__init__.py`
- `viewer/amplifier_app_cost_viewer/__main__.py`
- `viewer/tests/__init__.py`

**Step 1: Create `viewer/pyproject.toml`**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "amplifier-app-cost-viewer"
version = "0.1.0"
description = "Amplifier session cost and performance viewer"
requires-python = ">=3.11"
license = { text = "MIT" }
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",
]

[project.scripts]
amplifier-cost-viewer = "amplifier_app_cost_viewer.__main__:main"

[tool.hatch.build.targets.wheel]
packages = ["amplifier_app_cost_viewer"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
```

**Step 2: Create `viewer/amplifier_app_cost_viewer/__init__.py`**

```python
"""Amplifier session cost and performance viewer."""
```

**Step 3: Create `viewer/amplifier_app_cost_viewer/__main__.py`**

```python
"""Entry point: amplifier-cost-viewer."""
from __future__ import annotations

import argparse

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="Amplifier cost viewer")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8181)
    args = parser.parse_args()
    uvicorn.run(
        "amplifier_app_cost_viewer.server:app",
        host=args.host,
        port=args.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
```

**Step 4: Create `viewer/tests/__init__.py`**

```python
```
(empty file)

**Step 5: Install the package and verify**

```bash
cd /Users/ken/workspace/ms/token-cost/viewer
uv pip install -e "." --quiet
echo "Exit: $?"
```

Expected output:
```
Exit: 0
```

If uv is not available, try: `pip install -e "." -q`

**Step 6: Commit**

```bash
cd /Users/ken/workspace/ms/token-cost
git add viewer/
git commit -m "feat(viewer): package scaffold — pyproject.toml, __init__, __main__"
```

---

## Task 2: Write failing tests for `pricing.py`

**Files:**
- Create: `viewer/tests/test_pricing.py`

**Step 1: Write the failing tests**

Create `viewer/tests/test_pricing.py` with the full contents below:

```python
"""Tests for viewer pricing / cost computation module."""
from __future__ import annotations

import pytest

from amplifier_app_cost_viewer.pricing import (
    UNKNOWN_COLOR,
    compute_cost,
    get_model_color,
)


# ---------------------------------------------------------------------------
# compute_cost
# ---------------------------------------------------------------------------


class TestComputeCost:
    def test_claude_sonnet_basic_cost(self):
        # claude-sonnet-4-5: $3.00/MTok input, $15.00/MTok output
        # 1M input + 1M output = $18.00
        cost = compute_cost("claude-sonnet-4-5", input_tokens=1_000_000, output_tokens=1_000_000)
        assert abs(cost - 18.0) < 0.001

    def test_unknown_model_returns_zero(self):
        cost = compute_cost("completely-unknown-model-xyz-9999", 1_000_000, 1_000_000)
        assert cost == 0.0

    def test_zero_tokens_returns_zero(self):
        cost = compute_cost("claude-sonnet-4-5", 0, 0)
        assert cost == 0.0

    def test_cache_read_tokens(self):
        # claude-sonnet-4-5 cache_read: $0.30/MTok (10% of $3.00)
        cost = compute_cost("claude-sonnet-4-5", 0, 0, cache_read_tokens=1_000_000)
        assert abs(cost - 0.30) < 0.001

    def test_cache_write_tokens(self):
        # claude-sonnet-4-5 cache_write: $0.75/MTok (25% of $3.00)
        cost = compute_cost("claude-sonnet-4-5", 0, 0, cache_write_tokens=1_000_000)
        assert abs(cost - 0.75) < 0.001

    def test_gpt4o_cost(self):
        # gpt-4o: $2.50/MTok input, $10.00/MTok output
        cost = compute_cost("gpt-4o", input_tokens=1_000_000, output_tokens=0)
        assert abs(cost - 2.50) < 0.001

    def test_gpt4o_mini_cost(self):
        # gpt-4o-mini: $0.15/MTok input
        cost = compute_cost("gpt-4o-mini", input_tokens=1_000_000, output_tokens=0)
        assert abs(cost - 0.15) < 0.001

    def test_gemini_flash_cost(self):
        # gemini-2.0-flash: $0.10/MTok input
        cost = compute_cost("gemini-2.0-flash", input_tokens=1_000_000, output_tokens=0)
        assert abs(cost - 0.10) < 0.001

    def test_all_token_types_sum(self):
        # Verify input + output + cache_read + cache_write all contribute
        cost_all = compute_cost(
            "claude-sonnet-4-5",
            input_tokens=1_000_000,
            output_tokens=1_000_000,
            cache_read_tokens=1_000_000,
            cache_write_tokens=1_000_000,
        )
        # $3.00 + $15.00 + $0.30 + $0.75 = $19.05
        assert abs(cost_all - 19.05) < 0.001


# ---------------------------------------------------------------------------
# Prefix matching
# ---------------------------------------------------------------------------


class TestPrefixMatch:
    def test_exact_key_match(self):
        # Direct key "claude-sonnet-4-5" should resolve and return nonzero cost
        cost = compute_cost("claude-sonnet-4-5", 1_000_000, 0)
        assert cost > 0

    def test_version_suffix_prefix_match(self):
        # "claude-sonnet-4-6-20251001" has a suffix; should match "claude-sonnet-4-6"
        cost_suffix = compute_cost("claude-sonnet-4-6-20251001", 1_000_000, 0)
        cost_base = compute_cost("claude-sonnet-4-6", 1_000_000, 0)
        # Both should be non-zero and equal
        assert cost_base > 0
        assert abs(cost_suffix - cost_base) < 0.0001

    def test_longer_key_wins_over_shorter(self):
        # "claude-haiku-4-5" should not accidentally match "claude-haiku-4"
        # if both exist; it picks the longer (more specific) one first
        cost = compute_cost("claude-haiku-4-5", 1_000_000, 0)
        assert cost > 0

    def test_truly_unknown_model_is_zero(self):
        assert compute_cost("no-such-model-ever-12345", 100, 100) == 0.0


# ---------------------------------------------------------------------------
# get_model_color
# ---------------------------------------------------------------------------


class TestGetModelColor:
    def test_claude_model_returns_hex_string(self):
        color = get_model_color("claude-sonnet-4-5", "anthropic")
        assert color.startswith("#"), f"Expected hex color, got: {color!r}"
        assert len(color) == 7

    def test_gpt_model_returns_hex_string(self):
        color = get_model_color("gpt-4o", "openai")
        assert color.startswith("#")
        assert len(color) == 7

    def test_different_providers_give_different_colors(self):
        claude_color = get_model_color("claude-sonnet-4-5", "anthropic")
        gpt_color = get_model_color("gpt-4o", "openai")
        assert claude_color != gpt_color

    def test_unknown_model_returns_unknown_color(self):
        color = get_model_color("completely-unknown-model-9999", "unknown-provider")
        assert color == UNKNOWN_COLOR

    def test_haiku_differs_from_opus(self):
        # Different tier models should have different colors
        haiku = get_model_color("claude-haiku-4-5", "anthropic")
        opus = get_model_color("claude-opus-4", "anthropic")
        # Both valid hex
        assert haiku.startswith("#") and len(haiku) == 7
        assert opus.startswith("#") and len(opus) == 7
        # Different saturation tiers → different colors
        assert haiku != opus
```

**Step 2: Run tests to verify they fail**

```bash
cd /Users/ken/workspace/ms/token-cost/viewer
python -m pytest tests/test_pricing.py -v 2>&1 | head -30
```

Expected: `ModuleNotFoundError: No module named 'amplifier_app_cost_viewer.pricing'` (or similar import error). The tests cannot pass yet because `pricing.py` does not exist.

---

## Task 3: Run pricing tests → verify RED

**Step 1: Run**

```bash
cd /Users/ken/workspace/ms/token-cost/viewer
python -m pytest tests/test_pricing.py -v
```

Expected output (abbreviated):
```
ERRORS
ERROR tests/test_pricing.py - ImportError: cannot import name 'compute_cost' from 'amplifier_app_cost_viewer.pricing'
```

Or if the file doesn't exist yet:
```
ModuleNotFoundError: No module named 'amplifier_app_cost_viewer.pricing'
```

Either error confirms the tests are correctly failing. Do not proceed to Task 4 until you see a failure.

---

## Task 4: Implement `pricing.py`

**Files:**
- Create: `viewer/amplifier_app_cost_viewer/pricing.py`

**Step 1: Create the file**

```python
# Pricing data sourced from LiteLLM's model_prices_and_context_window.json
# https://github.com/BerriAI/litellm/blob/main/model_prices_and_context_window.json
# Licensed under MIT. LiteLLM is maintained by BerriAI.
#
# This module provides:
#   - STATIC_PRICING: bundled fallback prices (per-token, USD)
#   - load_pricing(): returns pricing dict (static fallback in Phase 1)
#   - compute_cost(): returns USD cost for one LLM call
#   - get_model_color(): returns hex color for Gantt rendering
"""Pricing lookup and cost computation for the cost viewer."""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Static fallback pricing table
# Keys are model name prefixes. Longest-prefix match wins.
# Prices are USD per token (not per million — divide by 1e6 from the MTok rate).
# ---------------------------------------------------------------------------

# fmt: off
STATIC_PRICING: dict[str, dict] = {
    # ── Anthropic Claude 4 ──────────────────────────────────────────────
    "claude-opus-4": {
        "input_cost_per_token":              15.00e-6,
        "output_cost_per_token":             75.00e-6,
        "cache_read_input_token_cost":        1.50e-6,  # 10% of input
        "cache_creation_input_token_cost":    3.75e-6,  # 25% of input
        "litellm_provider": "anthropic",
    },
    "claude-sonnet-4-6": {
        "input_cost_per_token":               3.00e-6,
        "output_cost_per_token":             15.00e-6,
        "cache_read_input_token_cost":        0.30e-6,
        "cache_creation_input_token_cost":    0.75e-6,
        "litellm_provider": "anthropic",
    },
    "claude-sonnet-4-5": {
        "input_cost_per_token":               3.00e-6,
        "output_cost_per_token":             15.00e-6,
        "cache_read_input_token_cost":        0.30e-6,
        "cache_creation_input_token_cost":    0.75e-6,
        "litellm_provider": "anthropic",
    },
    "claude-haiku-4-5": {
        "input_cost_per_token":               0.80e-6,
        "output_cost_per_token":              4.00e-6,
        "cache_read_input_token_cost":        0.08e-6,
        "cache_creation_input_token_cost":    0.20e-6,
        "litellm_provider": "anthropic",
    },
    # ── Anthropic Claude 3.x ────────────────────────────────────────────
    "claude-3-5-sonnet": {
        "input_cost_per_token":               3.00e-6,
        "output_cost_per_token":             15.00e-6,
        "cache_read_input_token_cost":        0.30e-6,
        "cache_creation_input_token_cost":    0.75e-6,
        "litellm_provider": "anthropic",
    },
    "claude-3-5-haiku": {
        "input_cost_per_token":               0.80e-6,
        "output_cost_per_token":              4.00e-6,
        "cache_read_input_token_cost":        0.08e-6,
        "cache_creation_input_token_cost":    0.20e-6,
        "litellm_provider": "anthropic",
    },
    "claude-3-opus": {
        "input_cost_per_token":              15.00e-6,
        "output_cost_per_token":             75.00e-6,
        "cache_read_input_token_cost":        1.50e-6,
        "cache_creation_input_token_cost":    3.75e-6,
        "litellm_provider": "anthropic",
    },
    # ── OpenAI ──────────────────────────────────────────────────────────
    "gpt-4.5": {
        "input_cost_per_token":              75.00e-6,
        "output_cost_per_token":            150.00e-6,
        "litellm_provider": "openai",
    },
    "gpt-4o-mini": {
        "input_cost_per_token":               0.15e-6,
        "output_cost_per_token":              0.60e-6,
        "litellm_provider": "openai",
    },
    "gpt-4o": {
        "input_cost_per_token":               2.50e-6,
        "output_cost_per_token":             10.00e-6,
        "litellm_provider": "openai",
    },
    "gpt-4.1-mini": {
        "input_cost_per_token":               0.40e-6,
        "output_cost_per_token":              1.60e-6,
        "litellm_provider": "openai",
    },
    "gpt-4.1": {
        "input_cost_per_token":               2.00e-6,
        "output_cost_per_token":              8.00e-6,
        "litellm_provider": "openai",
    },
    "o4-mini": {
        "input_cost_per_token":               1.10e-6,
        "output_cost_per_token":              4.40e-6,
        "litellm_provider": "openai",
    },
    "o3-mini": {
        "input_cost_per_token":               1.10e-6,
        "output_cost_per_token":              4.40e-6,
        "litellm_provider": "openai",
    },
    "o3": {
        "input_cost_per_token":              10.00e-6,
        "output_cost_per_token":             40.00e-6,
        "litellm_provider": "openai",
    },
    # ── Google Gemini ────────────────────────────────────────────────────
    "gemini-2.5-pro": {
        "input_cost_per_token":               1.25e-6,
        "output_cost_per_token":             10.00e-6,
        "litellm_provider": "google",
    },
    "gemini-2.5-flash": {
        "input_cost_per_token":               0.15e-6,
        "output_cost_per_token":              0.60e-6,
        "litellm_provider": "google",
    },
    "gemini-2.0-flash": {
        "input_cost_per_token":               0.10e-6,
        "output_cost_per_token":              0.40e-6,
        "litellm_provider": "google",
    },
    "gemini-1.5-pro": {
        "input_cost_per_token":               1.25e-6,
        "output_cost_per_token":              5.00e-6,
        "litellm_provider": "google",
    },
    "gemini-1.5-flash": {
        "input_cost_per_token":               0.075e-6,
        "output_cost_per_token":              0.30e-6,
        "litellm_provider": "google",
    },
}
# fmt: on

# ---------------------------------------------------------------------------
# Color tables
# ---------------------------------------------------------------------------

PROVIDER_COLORS: dict[str, str] = {
    "anthropic": "#7B2FBE",
    "openai":    "#10A37F",
    "google":    "#4285F4",
    "azure":     "#3B82F6",
}

# Preset colors per model-name prefix (longest-match wins).
# Within a provider family, lighter shades = lower-tier / cheaper models.
_MODEL_COLORS: dict[str, str] = {
    # Anthropic (purple family)
    "claude-opus":    "#7B2FBE",  # full purple  (opus = most expensive)
    "claude-sonnet":  "#9C59D1",  # medium purple
    "claude-haiku":   "#C08FE8",  # light purple  (haiku = cheapest)
    # OpenAI (teal/green family)
    "gpt-4.5":        "#10A37F",  # full teal
    "gpt-4o-mini":    "#6BBFA6",  # light teal
    "gpt-4o":         "#3DB88E",  # medium teal
    "gpt-4.1":        "#3DB88E",
    "o4-mini":        "#6BBFA6",
    "o3-mini":        "#6BBFA6",
    "o3":             "#10A37F",
    # Google (blue family)
    "gemini-2.5-pro":   "#4285F4",  # full blue
    "gemini-2.0-pro":   "#4285F4",
    "gemini-1.5-pro":   "#5E9CF5",  # medium blue
    "gemini-2.5-flash": "#89B6F9",  # light blue
    "gemini-2.0-flash": "#89B6F9",
    "gemini-1.5-flash": "#89B6F9",
}

TOOL_COLOR:     str = "#64748B"  # slate gray
THINKING_COLOR: str = "#6366F1"  # indigo
UNKNOWN_COLOR:  str = "#F59E0B"  # amber


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _lookup_pricing(model: str) -> dict | None:
    """Return pricing dict for model using longest-prefix match, or None."""
    lower = model.lower()
    for key in sorted(STATIC_PRICING, key=len, reverse=True):
        if lower.startswith(key.lower()):
            return STATIC_PRICING[key]
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_pricing() -> dict[str, dict]:
    """Return the active pricing table.

    Phase 1: returns STATIC_PRICING only.
    Phase 2 (update_pricing.py): will fetch from LiteLLM and cache at
    ~/.amplifier/pricing-cache.json, falling back to STATIC_PRICING on error.
    """
    return STATIC_PRICING


def compute_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int = 0,
    cache_write_tokens: int = 0,
) -> float:
    """Return estimated cost in USD for one LLM call.

    Returns 0.0 when the model is not in the pricing table — never raises.
    """
    rates = _lookup_pricing(model)
    if rates is None:
        return 0.0
    return (
        input_tokens       * rates.get("input_cost_per_token", 0.0)
        + output_tokens    * rates.get("output_cost_per_token", 0.0)
        + cache_read_tokens  * rates.get("cache_read_input_token_cost", 0.0)
        + cache_write_tokens * rates.get("cache_creation_input_token_cost", 0.0)
    )


def get_model_color(model: str, provider: str = "") -> str:
    """Return a hex color string for this model/provider combination.

    Uses longest-prefix match against _MODEL_COLORS. Falls back to the
    provider base color, then UNKNOWN_COLOR.
    """
    lower = model.lower()
    for key in sorted(_MODEL_COLORS, key=len, reverse=True):
        if lower.startswith(key):
            return _MODEL_COLORS[key]
    # Fall back to provider color
    prov_color = PROVIDER_COLORS.get(provider.lower())
    return prov_color if prov_color is not None else UNKNOWN_COLOR
```

---

## Task 5: Run pricing tests → verify GREEN, commit

**Step 1: Run tests**

```bash
cd /Users/ken/workspace/ms/token-cost/viewer
python -m pytest tests/test_pricing.py -v
```

Expected output:
```
tests/test_pricing.py::TestComputeCost::test_claude_sonnet_basic_cost PASSED
tests/test_pricing.py::TestComputeCost::test_unknown_model_returns_zero PASSED
tests/test_pricing.py::TestComputeCost::test_zero_tokens_returns_zero PASSED
tests/test_pricing.py::TestComputeCost::test_cache_read_tokens PASSED
tests/test_pricing.py::TestComputeCost::test_cache_write_tokens PASSED
tests/test_pricing.py::TestComputeCost::test_gpt4o_cost PASSED
tests/test_pricing.py::TestComputeCost::test_gpt4o_mini_cost PASSED
tests/test_pricing.py::TestComputeCost::test_gemini_flash_cost PASSED
tests/test_pricing.py::TestComputeCost::test_all_token_types_sum PASSED
tests/test_pricing.py::TestPrefixMatch::test_exact_key_match PASSED
tests/test_pricing.py::TestPrefixMatch::test_version_suffix_prefix_match PASSED
tests/test_pricing.py::TestPrefixMatch::test_longer_key_wins_over_shorter PASSED
tests/test_pricing.py::TestPrefixMatch::test_truly_unknown_model_is_zero PASSED
tests/test_pricing.py::TestGetModelColor::test_claude_model_returns_hex_string PASSED
tests/test_pricing.py::TestGetModelColor::test_gpt_model_returns_hex_string PASSED
tests/test_pricing.py::TestGetModelColor::test_different_providers_give_different_colors PASSED
tests/test_pricing.py::TestGetModelColor::test_unknown_model_returns_unknown_color PASSED
tests/test_pricing.py::TestGetModelColor::test_haiku_differs_from_opus PASSED

18 passed in 0.XXs
```

All 18 tests must pass. If any fail, fix `pricing.py` before continuing.

**Step 2: Commit**

```bash
cd /Users/ken/workspace/ms/token-cost
git add viewer/amplifier_app_cost_viewer/pricing.py viewer/tests/test_pricing.py
git commit -m "feat(viewer): pricing.py with static fallback dict, cost compute, model colors"
```

---

## Task 6: Write failing tests for `parse_spans()` and `normalize_timestamps()`

**Files:**
- Create: `viewer/tests/test_reader.py`

**Step 1: Write the failing tests**

Create `viewer/tests/test_reader.py` with the full contents below:

```python
"""Tests for reader.py — span parsing and session tree building."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Synthetic events.jsonl content
#
# Timeline (all offsets in ms from session:start):
#   0ms      session:start
#   2000ms   provider:request  (LLM call begins)
#   3000ms   thinking:delta    (thinking begins inside LLM window)
#   5000ms   thinking:final    (thinking ends)
#   10700ms  llm:response      (LLM responds — 8700ms duration)
#   10900ms  tool:pre          (bash tool starts)
#   11242ms  tool:post         (bash tool ends — 342ms)
#   30000ms  session:end
#
# Expected spans (sorted by start_ms):
#   LLM     start=2000   end=10700
#   thinking start=3000  end=5000
#   tool    start=10900  end=11242
# ---------------------------------------------------------------------------

SYNTHETIC_EVENTS = """\
{"ts":"2026-04-24T10:00:00.000+00:00","lvl":"INFO","schema":{"name":"amplifier.log","ver":"1.0.0"},"event":"session:start","session_id":"test-session","data":{"timestamp":"2026-04-24T10:00:00.000000+00:00"}}
{"ts":"2026-04-24T10:00:02.000+00:00","lvl":"INFO","schema":{"name":"amplifier.log","ver":"1.0.0"},"event":"provider:request","session_id":"test-session","data":{"provider":"anthropic","timestamp":"2026-04-24T10:00:02.000000+00:00"}}
{"ts":"2026-04-24T10:00:03.000+00:00","lvl":"INFO","schema":{"name":"amplifier.log","ver":"1.0.0"},"event":"thinking:delta","session_id":"test-session","data":{"text":"Let me think through this..."}}
{"ts":"2026-04-24T10:00:05.000+00:00","lvl":"INFO","schema":{"name":"amplifier.log","ver":"1.0.0"},"event":"thinking:final","session_id":"test-session","data":{"text":"I have a plan."}}
{"ts":"2026-04-24T10:00:10.700+00:00","lvl":"INFO","schema":{"name":"amplifier.log","ver":"1.0.0"},"event":"llm:response","session_id":"test-session","duration_ms":8700,"status":"ok","data":{"model":"claude-sonnet-4-5","provider":"anthropic","usage":{"input":512,"output":128,"cache_read":0,"cache_write":0}}}
{"ts":"2026-04-24T10:00:10.900+00:00","lvl":"INFO","schema":{"name":"amplifier.log","ver":"1.0.0"},"event":"tool:pre","session_id":"test-session","data":{"tool_call_id":"call_abc123","tool_name":"bash","tool_input":{"command":"ls -la"},"timestamp":"2026-04-24T10:00:10.900000+00:00"}}
{"ts":"2026-04-24T10:00:11.242+00:00","lvl":"INFO","schema":{"name":"amplifier.log","ver":"1.0.0"},"event":"tool:post","session_id":"test-session","data":{"tool_call_id":"call_abc123","result":{"success":true,"output":"file1.txt\\nfile2.txt","error":null},"timestamp":"2026-04-24T10:00:11.242000+00:00"}}
{"ts":"2026-04-24T10:00:30.000+00:00","lvl":"INFO","schema":{"name":"amplifier.log","ver":"1.0.0"},"event":"session:end","session_id":"test-session","data":{"timestamp":"2026-04-24T10:00:30.000000+00:00"}}
"""

# Synthetic events with an UNPAIRED tool:pre (no matching tool:post)
EVENTS_UNPAIRED_TOOL = """\
{"ts":"2026-04-24T10:00:00.000+00:00","lvl":"INFO","schema":{"name":"amplifier.log","ver":"1.0.0"},"event":"session:start","session_id":"test-session","data":{"timestamp":"2026-04-24T10:00:00.000000+00:00"}}
{"ts":"2026-04-24T10:00:05.000+00:00","lvl":"INFO","schema":{"name":"amplifier.log","ver":"1.0.0"},"event":"tool:pre","session_id":"test-session","data":{"tool_call_id":"call_orphan","tool_name":"bash","tool_input":{"command":"ls"},"timestamp":"2026-04-24T10:00:05.000000+00:00"}}
{"ts":"2026-04-24T10:00:10.000+00:00","lvl":"INFO","schema":{"name":"amplifier.log","ver":"1.0.0"},"event":"session:end","session_id":"test-session","data":{"timestamp":"2026-04-24T10:00:10.000000+00:00"}}
"""


# ---------------------------------------------------------------------------
# normalize_timestamps
# ---------------------------------------------------------------------------


class TestNormalizeTimestamps:
    def test_returns_session_start_ms(self, tmp_path: Path):
        from amplifier_app_cost_viewer.reader import normalize_timestamps

        events_file = tmp_path / "events.jsonl"
        events_file.write_text(SYNTHETIC_EVENTS)

        result_ms = normalize_timestamps(events_file)

        # The session:start ts is "2026-04-24T10:00:00.000+00:00"
        # We verify it's a sensible Unix ms timestamp (year 2026)
        import datetime
        dt = datetime.datetime(2026, 4, 24, 10, 0, 0, tzinfo=datetime.timezone.utc)
        expected_ms = int(dt.timestamp() * 1000)
        assert result_ms == expected_ms

    def test_returns_int(self, tmp_path: Path):
        from amplifier_app_cost_viewer.reader import normalize_timestamps

        events_file = tmp_path / "events.jsonl"
        events_file.write_text(SYNTHETIC_EVENTS)
        assert isinstance(normalize_timestamps(events_file), int)


# ---------------------------------------------------------------------------
# parse_spans — LLM spans
# ---------------------------------------------------------------------------


class TestParseSpansLlm:
    def test_llm_span_created(self, tmp_path: Path):
        from amplifier_app_cost_viewer.reader import normalize_timestamps, parse_spans

        events_file = tmp_path / "events.jsonl"
        events_file.write_text(SYNTHETIC_EVENTS)

        root_start_ms = normalize_timestamps(events_file)
        spans = parse_spans(events_file, root_start_ms, root_start_ms)

        llm_spans = [s for s in spans if s.type == "llm"]
        assert len(llm_spans) == 1, f"Expected 1 LLM span, got {len(llm_spans)}"

    def test_llm_span_start_offset(self, tmp_path: Path):
        from amplifier_app_cost_viewer.reader import normalize_timestamps, parse_spans

        events_file = tmp_path / "events.jsonl"
        events_file.write_text(SYNTHETIC_EVENTS)
        root_start_ms = normalize_timestamps(events_file)
        spans = parse_spans(events_file, root_start_ms, root_start_ms)

        llm = next(s for s in spans if s.type == "llm")
        assert llm.start_ms == 2000, f"Expected start_ms=2000, got {llm.start_ms}"
        assert llm.end_ms == 10700, f"Expected end_ms=10700, got {llm.end_ms}"

    def test_llm_span_tokens(self, tmp_path: Path):
        from amplifier_app_cost_viewer.reader import normalize_timestamps, parse_spans

        events_file = tmp_path / "events.jsonl"
        events_file.write_text(SYNTHETIC_EVENTS)
        root_start_ms = normalize_timestamps(events_file)
        spans = parse_spans(events_file, root_start_ms, root_start_ms)

        llm = next(s for s in spans if s.type == "llm")
        assert llm.input_tokens == 512
        assert llm.output_tokens == 128
        assert llm.provider == "anthropic"
        assert llm.model == "claude-sonnet-4-5"

    def test_llm_span_cost_nonzero(self, tmp_path: Path):
        from amplifier_app_cost_viewer.reader import normalize_timestamps, parse_spans

        events_file = tmp_path / "events.jsonl"
        events_file.write_text(SYNTHETIC_EVENTS)
        root_start_ms = normalize_timestamps(events_file)
        spans = parse_spans(events_file, root_start_ms, root_start_ms)

        llm = next(s for s in spans if s.type == "llm")
        # 512 * 3e-6 + 128 * 15e-6 = 0.001536 + 0.001920 = 0.003456
        assert abs(llm.cost_usd - 0.003456) < 0.0001

    def test_llm_span_color_is_hex(self, tmp_path: Path):
        from amplifier_app_cost_viewer.reader import normalize_timestamps, parse_spans

        events_file = tmp_path / "events.jsonl"
        events_file.write_text(SYNTHETIC_EVENTS)
        root_start_ms = normalize_timestamps(events_file)
        spans = parse_spans(events_file, root_start_ms, root_start_ms)

        llm = next(s for s in spans if s.type == "llm")
        assert llm.color.startswith("#") and len(llm.color) == 7


# ---------------------------------------------------------------------------
# parse_spans — tool spans
# ---------------------------------------------------------------------------


class TestParseSpansTool:
    def test_tool_span_created(self, tmp_path: Path):
        from amplifier_app_cost_viewer.reader import normalize_timestamps, parse_spans

        events_file = tmp_path / "events.jsonl"
        events_file.write_text(SYNTHETIC_EVENTS)
        root_start_ms = normalize_timestamps(events_file)
        spans = parse_spans(events_file, root_start_ms, root_start_ms)

        tool_spans = [s for s in spans if s.type == "tool"]
        assert len(tool_spans) == 1

    def test_tool_span_matched_by_tool_call_id(self, tmp_path: Path):
        from amplifier_app_cost_viewer.reader import normalize_timestamps, parse_spans

        events_file = tmp_path / "events.jsonl"
        events_file.write_text(SYNTHETIC_EVENTS)
        root_start_ms = normalize_timestamps(events_file)
        spans = parse_spans(events_file, root_start_ms, root_start_ms)

        tool = next(s for s in spans if s.type == "tool")
        assert tool.start_ms == 10900
        assert tool.end_ms == 11242
        assert tool.tool_name == "bash"
        assert tool.success is True

    def test_tool_span_color_is_slate(self, tmp_path: Path):
        from amplifier_app_cost_viewer.reader import normalize_timestamps, parse_spans
        from amplifier_app_cost_viewer.pricing import TOOL_COLOR

        events_file = tmp_path / "events.jsonl"
        events_file.write_text(SYNTHETIC_EVENTS)
        root_start_ms = normalize_timestamps(events_file)
        spans = parse_spans(events_file, root_start_ms, root_start_ms)

        tool = next(s for s in spans if s.type == "tool")
        assert tool.color == TOOL_COLOR

    def test_unpaired_tool_pre_silently_dropped(self, tmp_path: Path):
        from amplifier_app_cost_viewer.reader import normalize_timestamps, parse_spans

        events_file = tmp_path / "events.jsonl"
        events_file.write_text(EVENTS_UNPAIRED_TOOL)
        root_start_ms = normalize_timestamps(events_file)
        spans = parse_spans(events_file, root_start_ms, root_start_ms)

        # The orphaned tool:pre has no matching tool:post → dropped, no error
        tool_spans = [s for s in spans if s.type == "tool"]
        assert len(tool_spans) == 0


# ---------------------------------------------------------------------------
# parse_spans — thinking spans
# ---------------------------------------------------------------------------


class TestParseSpansThinking:
    def test_thinking_span_created(self, tmp_path: Path):
        from amplifier_app_cost_viewer.reader import normalize_timestamps, parse_spans

        events_file = tmp_path / "events.jsonl"
        events_file.write_text(SYNTHETIC_EVENTS)
        root_start_ms = normalize_timestamps(events_file)
        spans = parse_spans(events_file, root_start_ms, root_start_ms)

        thinking = [s for s in spans if s.type == "thinking"]
        assert len(thinking) == 1

    def test_thinking_span_offsets(self, tmp_path: Path):
        from amplifier_app_cost_viewer.reader import normalize_timestamps, parse_spans

        events_file = tmp_path / "events.jsonl"
        events_file.write_text(SYNTHETIC_EVENTS)
        root_start_ms = normalize_timestamps(events_file)
        spans = parse_spans(events_file, root_start_ms, root_start_ms)

        th = next(s for s in spans if s.type == "thinking")
        assert th.start_ms == 3000
        assert th.end_ms == 5000

    def test_thinking_span_color_is_indigo(self, tmp_path: Path):
        from amplifier_app_cost_viewer.reader import normalize_timestamps, parse_spans
        from amplifier_app_cost_viewer.pricing import THINKING_COLOR

        events_file = tmp_path / "events.jsonl"
        events_file.write_text(SYNTHETIC_EVENTS)
        root_start_ms = normalize_timestamps(events_file)
        spans = parse_spans(events_file, root_start_ms, root_start_ms)

        th = next(s for s in spans if s.type == "thinking")
        assert th.color == THINKING_COLOR


# ---------------------------------------------------------------------------
# parse_spans — ordering
# ---------------------------------------------------------------------------


class TestParseSpansOrder:
    def test_spans_sorted_by_start_ms(self, tmp_path: Path):
        from amplifier_app_cost_viewer.reader import normalize_timestamps, parse_spans

        events_file = tmp_path / "events.jsonl"
        events_file.write_text(SYNTHETIC_EVENTS)
        root_start_ms = normalize_timestamps(events_file)
        spans = parse_spans(events_file, root_start_ms, root_start_ms)

        assert len(spans) == 3  # LLM, thinking, tool
        starts = [s.start_ms for s in spans]
        assert starts == sorted(starts), f"Spans not sorted by start_ms: {starts}"

    def test_span_types_in_order(self, tmp_path: Path):
        from amplifier_app_cost_viewer.reader import normalize_timestamps, parse_spans

        events_file = tmp_path / "events.jsonl"
        events_file.write_text(SYNTHETIC_EVENTS)
        root_start_ms = normalize_timestamps(events_file)
        spans = parse_spans(events_file, root_start_ms, root_start_ms)

        types = [s.type for s in spans]
        # LLM starts at 2000, thinking at 3000, tool at 10900
        assert types == ["llm", "thinking", "tool"]
```

**Step 2: Run tests to verify they fail**

```bash
cd /Users/ken/workspace/ms/token-cost/viewer
python -m pytest tests/test_reader.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'amplifier_app_cost_viewer.reader'`

---

## Task 7: Run parse_spans tests → verify RED

**Step 1: Run**

```bash
cd /Users/ken/workspace/ms/token-cost/viewer
python -m pytest tests/test_reader.py -v 2>&1 | tail -10
```

Expected: all tests erroring with import errors. Confirm before moving on.

---

## Task 8: Implement `parse_spans()` and `normalize_timestamps()` in `reader.py`

**Files:**
- Create: `viewer/amplifier_app_cost_viewer/reader.py`

**Step 1: Create the file**

```python
"""Event log reader — parses events.jsonl into Span and SessionNode trees."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from amplifier_app_cost_viewer.pricing import (
    THINKING_COLOR,
    TOOL_COLOR,
    UNKNOWN_COLOR,
    compute_cost,
    get_model_color,
)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class Span:
    """One timing unit in the session timeline."""

    type: str               # "llm" | "tool" | "thinking"
    start_ms: int           # ms offset from root session:start
    end_ms: int
    provider: str | None
    model: str | None
    cost_usd: float
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_write_tokens: int
    tool_name: str | None
    success: bool | None
    input: Any | None       # present only when log_io=true
    output: Any | None
    color: str              # hex color for Gantt rendering


@dataclass
class SessionNode:
    """One session in the delegation tree, with its spans and children."""

    session_id: str
    project_slug: str
    parent_id: str | None
    start_ts: str               # ISO timestamp of session:start
    end_ts: str | None
    duration_ms: int
    cost_usd: float             # own LLM cost (not including children)
    total_cost_usd: float       # own + all descendants
    spans: list[Span]
    children: list["SessionNode"]
    events_path: Path | None = field(default=None, compare=False, repr=False)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _ts_to_ms(ts_str: str) -> int:
    """Parse ISO 8601 timestamp string to Unix milliseconds (integer)."""
    return int(datetime.fromisoformat(ts_str).timestamp() * 1000)


def _offset_ms(ts_str: str, root_start_ms: int) -> int:
    """Return ms offset of a timestamp from the root session start."""
    return _ts_to_ms(ts_str) - root_start_ms


def _read_events(events_path: Path) -> list[dict]:
    """Read all valid JSON lines from an events.jsonl file."""
    events: list[dict] = []
    try:
        for line in events_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    except OSError:
        pass
    return events


# ---------------------------------------------------------------------------
# Public parsing functions
# ---------------------------------------------------------------------------


def normalize_timestamps(events_path: Path) -> int:
    """Return the Unix millisecond timestamp of the session:start event.

    This is used as the absolute anchor for computing all span offsets.
    Raises ValueError if no session:start event is found.
    """
    for event in _read_events(events_path):
        if event.get("event") == "session:start":
            return _ts_to_ms(event["ts"])
    raise ValueError(f"No session:start event found in {events_path}")


def parse_spans(
    events_path: Path,
    root_start_ms: int,
    session_start_ms: int,  # noqa: ARG001  (reserved for child-offset use in Phase 2)
) -> list[Span]:
    """Read events.jsonl and produce a sorted list of Span objects.

    Pairing rules:
    - LLM spans:      provider:request → llm:response  (sequential)
    - Tool spans:     tool:pre → tool:post              (matched by tool_call_id)
    - Thinking spans: thinking:delta(first) → thinking:final  (sequential)

    Unpaired start events are silently dropped. Unpaired end events are ignored.
    All start_ms / end_ms values are offsets in milliseconds from root_start_ms.
    """
    events = _read_events(events_path)
    spans: list[Span] = []

    # ── LLM spans — sequential pairing ──────────────────────────────────
    provider_requests = [e for e in events if e.get("event") == "provider:request"]
    llm_responses     = [e for e in events if e.get("event") == "llm:response"]

    for req, resp in zip(provider_requests, llm_responses):
        data    = resp.get("data", {})
        usage   = data.get("usage", {})
        model   = data.get("model", "unknown")
        provider = data.get("provider", "")
        in_tok  = int(usage.get("input",       0))
        out_tok = int(usage.get("output",      0))
        cr_tok  = int(usage.get("cache_read",  0))
        cw_tok  = int(usage.get("cache_write", 0))
        cost    = compute_cost(model, in_tok, out_tok, cr_tok, cw_tok)
        spans.append(
            Span(
                type="llm",
                start_ms=_offset_ms(req["ts"], root_start_ms),
                end_ms=_offset_ms(resp["ts"], root_start_ms),
                provider=provider,
                model=model,
                cost_usd=cost,
                input_tokens=in_tok,
                output_tokens=out_tok,
                cache_read_tokens=cr_tok,
                cache_write_tokens=cw_tok,
                tool_name=None,
                success=None,
                input=None,
                output=None,
                color=get_model_color(model, provider),
            )
        )

    # ── Tool spans — match by tool_call_id ───────────────────────────────
    tool_pre_map: dict[str, dict] = {}
    for e in events:
        if e.get("event") == "tool:pre":
            tcid = e.get("data", {}).get("tool_call_id")
            if tcid:
                tool_pre_map[tcid] = e

    for e in events:
        if e.get("event") != "tool:post":
            continue
        data = e.get("data", {})
        tcid = data.get("tool_call_id")
        if not tcid or tcid not in tool_pre_map:
            continue
        pre    = tool_pre_map.pop(tcid)
        result = data.get("result", {})
        spans.append(
            Span(
                type="tool",
                start_ms=_offset_ms(pre["ts"], root_start_ms),
                end_ms=_offset_ms(e["ts"], root_start_ms),
                provider=None,
                model=None,
                cost_usd=0.0,
                input_tokens=0,
                output_tokens=0,
                cache_read_tokens=0,
                cache_write_tokens=0,
                tool_name=pre.get("data", {}).get("tool_name"),
                success=result.get("success"),
                input=pre.get("data", {}).get("tool_input"),
                output=result.get("output"),
                color=TOOL_COLOR,
            )
        )

    # ── Thinking spans — first delta → final ─────────────────────────────
    thinking_start: dict | None = None
    for e in events:
        ev = e.get("event", "")
        if ev == "thinking:delta" and thinking_start is None:
            thinking_start = e
        elif ev == "thinking:final" and thinking_start is not None:
            spans.append(
                Span(
                    type="thinking",
                    start_ms=_offset_ms(thinking_start["ts"], root_start_ms),
                    end_ms=_offset_ms(e["ts"], root_start_ms),
                    provider=None,
                    model=None,
                    cost_usd=0.0,
                    input_tokens=0,
                    output_tokens=0,
                    cache_read_tokens=0,
                    cache_write_tokens=0,
                    tool_name=None,
                    success=None,
                    input=None,
                    output=None,
                    color=THINKING_COLOR,
                )
            )
            thinking_start = None

    return sorted(spans, key=lambda s: s.start_ms)


# ---------------------------------------------------------------------------
# Tree building (stubbed — full implementation in Task 12)
# ---------------------------------------------------------------------------


def discover_sessions(amplifier_home: Path) -> dict[str, SessionNode]:
    """Stub — implemented in Task 12."""
    raise NotImplementedError


def build_tree(sessions: dict[str, SessionNode]) -> list[SessionNode]:
    """Stub — implemented in Task 12."""
    raise NotImplementedError


def aggregate_costs(node: SessionNode) -> None:
    """Stub — implemented in Task 12."""
    raise NotImplementedError


def build_session_tree(amplifier_home: Path) -> list[SessionNode]:
    """Stub — implemented in Task 12."""
    raise NotImplementedError
```

---

## Task 9: Run parse_spans tests → verify GREEN, commit

**Step 1: Run just the span-parsing tests**

```bash
cd /Users/ken/workspace/ms/token-cost/viewer
python -m pytest tests/test_reader.py::TestNormalizeTimestamps \
                 tests/test_reader.py::TestParseSpansLlm \
                 tests/test_reader.py::TestParseSpansTool \
                 tests/test_reader.py::TestParseSpansThinking \
                 tests/test_reader.py::TestParseSpansOrder \
                 -v
```

Expected output:
```
tests/test_reader.py::TestNormalizeTimestamps::test_returns_session_start_ms PASSED
tests/test_reader.py::TestNormalizeTimestamps::test_returns_int PASSED
tests/test_reader.py::TestParseSpansLlm::test_llm_span_created PASSED
tests/test_reader.py::TestParseSpansLlm::test_llm_span_start_offset PASSED
tests/test_reader.py::TestParseSpansLlm::test_llm_span_tokens PASSED
tests/test_reader.py::TestParseSpansLlm::test_llm_span_cost_nonzero PASSED
tests/test_reader.py::TestParseSpansLlm::test_llm_span_color_is_hex PASSED
tests/test_reader.py::TestParseSpansTool::test_tool_span_created PASSED
tests/test_reader.py::TestParseSpansTool::test_tool_span_matched_by_tool_call_id PASSED
tests/test_reader.py::TestParseSpansTool::test_tool_span_color_is_slate PASSED
tests/test_reader.py::TestParseSpansTool::test_unpaired_tool_pre_silently_dropped PASSED
tests/test_reader.py::TestParseSpansThinking::test_thinking_span_created PASSED
tests/test_reader.py::TestParseSpansThinking::test_thinking_span_offsets PASSED
tests/test_reader.py::TestParseSpansThinking::test_thinking_span_color_is_indigo PASSED
tests/test_reader.py::TestParseSpansOrder::test_spans_sorted_by_start_ms PASSED
tests/test_reader.py::TestParseSpansOrder::test_span_types_in_order PASSED

16 passed in 0.XXs
```

All 16 must pass. If any fail, fix `reader.py` before committing.

**Step 2: Commit**

```bash
cd /Users/ken/workspace/ms/token-cost
git add viewer/amplifier_app_cost_viewer/reader.py viewer/tests/test_reader.py
git commit -m "feat(viewer): reader.py parse_spans + normalize_timestamps with tests"
```

---

## Task 10: Write failing tests for session tree building

**Files:**
- Create: `viewer/tests/conftest.py`
- Modify: `viewer/tests/test_reader.py` (append new test classes)

**Step 1: Create `viewer/tests/conftest.py`**

```python
"""Shared fixtures for amplifier-cost-viewer tests.

Provides `amp_home` — a temporary directory containing a fake
~/.amplifier/projects/ tree with 1 root session and 2 child sessions,
each with realistic events.jsonl and metadata.json files.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

# ── Session IDs and timestamps ───────────────────────────────────────────────
ROOT_SESSION_ID  = "root-aabbccdd"
CHILD1_SESSION_ID = "child1-11223344"
CHILD2_SESSION_ID = "child2-55667788"
PROJECT_SLUG = "test-project"

ROOT_START_ISO   = "2026-04-24T10:00:00.000+00:00"
CHILD1_START_ISO = "2026-04-24T10:00:05.000+00:00"  # 5 s after root
CHILD2_START_ISO = "2026-04-24T10:00:15.000+00:00"  # 15 s after root

# Pre-computed expected cost per session:
#   512 input  × $3.00/MTok  =  $0.001536
#   128 output × $15.00/MTok =  $0.001920
#   total                    =  $0.003456
COST_PER_SESSION = 0.003456


# ── Helpers ──────────────────────────────────────────────────────────────────


def _iso_plus(start_iso: str, offset_s: float) -> str:
    """Return an ISO timestamp `offset_s` seconds after `start_iso`."""
    dt = datetime.fromisoformat(start_iso) + timedelta(seconds=offset_s)
    return dt.isoformat()


def _session_events_jsonl(
    session_id: str,
    start_iso: str,
    parent_id: str | None = None,
) -> str:
    """Generate synthetic events.jsonl for one session.

    Contains: session:start, provider:request, llm:response (512 in / 128 out
    claude-sonnet-4-5), session:end. No thinking or tool events — keeps fixture
    simple for tree-building tests.
    """

    def _line(ts: str, event: str, extra: dict, **top) -> str:
        record: dict = {
            "ts": ts,
            "lvl": "INFO",
            "schema": {"name": "amplifier.log", "ver": "1.0.0"},
            "event": event,
            "session_id": session_id,
            **top,
            "data": extra,
        }
        return json.dumps(record)

    start_data: dict = {"timestamp": start_iso}
    if parent_id:
        start_data["parent_id"] = parent_id

    llm_req_iso  = _iso_plus(start_iso, 2.0)
    llm_resp_iso = _iso_plus(start_iso, 10.7)
    end_iso      = _iso_plus(start_iso, 30.0)

    llm_resp_record = {
        "ts": llm_resp_iso,
        "lvl": "INFO",
        "schema": {"name": "amplifier.log", "ver": "1.0.0"},
        "event": "llm:response",
        "session_id": session_id,
        "duration_ms": 8700,
        "status": "ok",
        "data": {
            "model": "claude-sonnet-4-5",
            "provider": "anthropic",
            "usage": {"input": 512, "output": 128, "cache_read": 0, "cache_write": 0},
        },
    }

    lines = [
        _line(start_iso,  "session:start",    start_data),
        _line(llm_req_iso, "provider:request", {"provider": "anthropic", "timestamp": llm_req_iso}),
        json.dumps(llm_resp_record),
        _line(end_iso,    "session:end",       {"timestamp": end_iso}),
    ]
    return "\n".join(lines)


def _session_metadata(
    session_id: str,
    parent_id: str | None,
    project_slug: str,
    created: str,
) -> str:
    return json.dumps({
        "session_id":   session_id,
        "parent_id":    parent_id,
        "agent_name":   "test-agent",
        "created":      created,
        "project_slug": project_slug,
        "project_name": "test",
    })


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def amp_home(tmp_path: Path) -> Path:
    """Fake ~/.amplifier with 3 sessions: 1 root + 2 children.

    Directory layout:
        <tmp_path>/
          projects/
            test-project/
              sessions/
                root-aabbccdd/
                  events.jsonl
                  metadata.json         (parent_id = null)
                child1-11223344/
                  events.jsonl
                  metadata.json         (parent_id = root-aabbccdd)
                child2-55667788/
                  events.jsonl
                  metadata.json         (parent_id = root-aabbccdd)
    """
    session_specs = [
        (ROOT_SESSION_ID,   ROOT_START_ISO,   None),
        (CHILD1_SESSION_ID, CHILD1_START_ISO, ROOT_SESSION_ID),
        (CHILD2_SESSION_ID, CHILD2_START_ISO, ROOT_SESSION_ID),
    ]

    for sid, start_iso, parent_id in session_specs:
        sdir = tmp_path / "projects" / PROJECT_SLUG / "sessions" / sid
        sdir.mkdir(parents=True)
        (sdir / "events.jsonl").write_text(
            _session_events_jsonl(sid, start_iso, parent_id)
        )
        (sdir / "metadata.json").write_text(
            _session_metadata(sid, parent_id, PROJECT_SLUG, start_iso)
        )

    return tmp_path
```

**Step 2: Append new test classes to `viewer/tests/test_reader.py`**

Open `viewer/tests/test_reader.py` and **append** the following to the bottom of the file (after all existing content):

```python
# ---------------------------------------------------------------------------
# discover_sessions
# ---------------------------------------------------------------------------


class TestDiscoverSessions:
    def test_finds_all_three_sessions(self, amp_home):
        from amplifier_app_cost_viewer.reader import discover_sessions

        sessions = discover_sessions(amp_home)
        assert len(sessions) == 3

    def test_session_ids_are_correct(self, amp_home):
        from amplifier_app_cost_viewer.reader import discover_sessions
        from viewer.tests.conftest import ROOT_SESSION_ID, CHILD1_SESSION_ID, CHILD2_SESSION_ID  # noqa: F401

        sessions = discover_sessions(amp_home)
        # Import the IDs from conftest constants
        expected = {"root-aabbccdd", "child1-11223344", "child2-55667788"}
        assert set(sessions.keys()) == expected

    def test_root_has_no_parent_id(self, amp_home):
        from amplifier_app_cost_viewer.reader import discover_sessions

        sessions = discover_sessions(amp_home)
        root = sessions["root-aabbccdd"]
        assert root.parent_id is None

    def test_children_have_correct_parent_id(self, amp_home):
        from amplifier_app_cost_viewer.reader import discover_sessions

        sessions = discover_sessions(amp_home)
        assert sessions["child1-11223344"].parent_id == "root-aabbccdd"
        assert sessions["child2-55667788"].parent_id == "root-aabbccdd"

    def test_session_node_has_project_slug(self, amp_home):
        from amplifier_app_cost_viewer.reader import discover_sessions

        sessions = discover_sessions(amp_home)
        assert sessions["root-aabbccdd"].project_slug == "test-project"

    def test_empty_projects_dir_returns_empty(self, tmp_path):
        from amplifier_app_cost_viewer.reader import discover_sessions

        # No projects directory at all
        sessions = discover_sessions(tmp_path)
        assert sessions == {}

    def test_session_node_has_events_path(self, amp_home):
        from amplifier_app_cost_viewer.reader import discover_sessions

        sessions = discover_sessions(amp_home)
        root = sessions["root-aabbccdd"]
        assert root.events_path is not None
        assert root.events_path.exists()


# ---------------------------------------------------------------------------
# build_tree
# ---------------------------------------------------------------------------


class TestBuildTree:
    def test_returns_one_root(self, amp_home):
        from amplifier_app_cost_viewer.reader import discover_sessions, build_tree

        sessions = discover_sessions(amp_home)
        roots = build_tree(sessions)
        assert len(roots) == 1

    def test_root_has_two_children(self, amp_home):
        from amplifier_app_cost_viewer.reader import discover_sessions, build_tree

        sessions = discover_sessions(amp_home)
        roots = build_tree(sessions)
        root = roots[0]
        assert len(root.children) == 2

    def test_root_session_id(self, amp_home):
        from amplifier_app_cost_viewer.reader import discover_sessions, build_tree

        sessions = discover_sessions(amp_home)
        roots = build_tree(sessions)
        assert roots[0].session_id == "root-aabbccdd"

    def test_children_session_ids(self, amp_home):
        from amplifier_app_cost_viewer.reader import discover_sessions, build_tree

        sessions = discover_sessions(amp_home)
        roots = build_tree(sessions)
        child_ids = {c.session_id for c in roots[0].children}
        assert child_ids == {"child1-11223344", "child2-55667788"}


# ---------------------------------------------------------------------------
# aggregate_costs
# ---------------------------------------------------------------------------


class TestAggregateCosts:
    def test_root_total_includes_children(self, amp_home):
        from amplifier_app_cost_viewer.reader import (
            discover_sessions,
            build_tree,
            aggregate_costs,
        )

        sessions = discover_sessions(amp_home)
        roots = build_tree(sessions)
        root = roots[0]

        # Set known costs manually (simulating parsed spans)
        root.cost_usd = 1.0
        for child in root.children:
            child.cost_usd = 0.5
            child.total_cost_usd = 0.5  # leaf nodes

        aggregate_costs(root)

        assert abs(root.total_cost_usd - 2.0) < 0.0001  # 1.0 + 0.5 + 0.5

    def test_leaf_total_equals_own_cost(self, amp_home):
        from amplifier_app_cost_viewer.reader import (
            discover_sessions,
            build_tree,
            aggregate_costs,
        )

        sessions = discover_sessions(amp_home)
        roots = build_tree(sessions)
        root = roots[0]

        root.cost_usd = 0.0
        for child in root.children:
            child.cost_usd = 0.25

        aggregate_costs(root)

        for child in root.children:
            # Leaf nodes: total_cost_usd == cost_usd (no descendants)
            assert abs(child.total_cost_usd - 0.25) < 0.0001


# ---------------------------------------------------------------------------
# build_session_tree (end-to-end)
# ---------------------------------------------------------------------------


class TestBuildSessionTree:
    def test_returns_list_of_roots(self, amp_home):
        from amplifier_app_cost_viewer.reader import build_session_tree

        roots = build_session_tree(amp_home)
        assert isinstance(roots, list)
        assert len(roots) == 1

    def test_root_has_children(self, amp_home):
        from amplifier_app_cost_viewer.reader import build_session_tree

        roots = build_session_tree(amp_home)
        assert len(roots[0].children) == 2

    def test_root_spans_parsed(self, amp_home):
        from amplifier_app_cost_viewer.reader import build_session_tree

        roots = build_session_tree(amp_home)
        root = roots[0]
        # Each fixture session has 1 LLM span
        assert len(root.spans) == 1
        assert root.spans[0].type == "llm"

    def test_own_cost_nonzero(self, amp_home):
        from amplifier_app_cost_viewer.reader import build_session_tree

        roots = build_session_tree(amp_home)
        root = roots[0]
        # Root has its own LLM call → own cost > 0
        assert root.cost_usd > 0

    def test_total_cost_aggregated(self, amp_home):
        from amplifier_app_cost_viewer.reader import build_session_tree

        roots = build_session_tree(amp_home)
        root = roots[0]
        # 3 sessions × COST_PER_SESSION = 0.003456 × 3 = 0.010368
        expected_total = 0.003456 * 3
        assert abs(root.total_cost_usd - expected_total) < 0.001

    def test_sorted_most_recent_first(self, amp_home, tmp_path):
        """When there are two root sessions, the most recent is first."""
        from amplifier_app_cost_viewer.reader import build_session_tree
        import json as _json

        # Add a second root session starting BEFORE the existing root
        older_id = "older-root-zz"
        older_start = "2026-04-24T09:00:00.000+00:00"  # 1 hour before root
        sdir = amp_home / "projects" / "test-project" / "sessions" / older_id
        sdir.mkdir(parents=True)

        events = (
            _json.dumps({
                "ts": older_start, "lvl": "INFO",
                "schema": {"name": "amplifier.log", "ver": "1.0.0"},
                "event": "session:start", "session_id": older_id,
                "data": {"timestamp": older_start},
            }) + "\n" +
            _json.dumps({
                "ts": "2026-04-24T09:00:30.000+00:00", "lvl": "INFO",
                "schema": {"name": "amplifier.log", "ver": "1.0.0"},
                "event": "session:end", "session_id": older_id,
                "data": {"timestamp": "2026-04-24T09:00:30.000+00:00"},
            })
        )
        (sdir / "events.jsonl").write_text(events)
        (sdir / "metadata.json").write_text(_json.dumps({
            "session_id": older_id,
            "parent_id": None,
            "agent_name": "test",
            "created": older_start,
            "project_slug": "test-project",
            "project_name": "test",
        }))

        roots = build_session_tree(amp_home)
        assert len(roots) == 2
        # Most recent first: root-aabbccdd (10:00) before older-root-zz (09:00)
        assert roots[0].session_id == "root-aabbccdd"
        assert roots[1].session_id == "older-root-zz"
```

**Step 3: Verify the new tests fail**

```bash
cd /Users/ken/workspace/ms/token-cost/viewer
python -m pytest tests/test_reader.py::TestDiscoverSessions -v 2>&1 | tail -5
```

Expected: `NotImplementedError` from the stub functions.

---

## Task 11: Run tree building tests → verify RED

**Step 1: Run**

```bash
cd /Users/ken/workspace/ms/token-cost/viewer
python -m pytest tests/test_reader.py::TestDiscoverSessions \
                 tests/test_reader.py::TestBuildTree \
                 tests/test_reader.py::TestAggregateCosts \
                 tests/test_reader.py::TestBuildSessionTree \
                 -v 2>&1 | tail -10
```

Expected: failures with `NotImplementedError` for all new test classes. Confirm before proceeding.

---

## Task 12: Implement `discover_sessions`, `build_tree`, `aggregate_costs`, `build_session_tree`

**Files:**
- Modify: `viewer/amplifier_app_cost_viewer/reader.py`

**Step 1: Replace the stub functions at the bottom of `reader.py`**

Find and replace the four stub functions (the `raise NotImplementedError` stubs at the bottom of `reader.py`) with the full implementations below. Replace everything from `def discover_sessions(` to the end of the file:

```python
def discover_sessions(amplifier_home: Path) -> dict[str, SessionNode]:
    """Scan ~/.amplifier/projects/*/sessions/*/metadata.json.

    Returns a flat dict of session_id → SessionNode (no spans, no cost yet).
    Sessions missing either metadata.json or events.jsonl are silently skipped.
    """
    sessions: dict[str, SessionNode] = {}
    projects_dir = amplifier_home / "projects"
    if not projects_dir.exists():
        return sessions

    for project_dir in sorted(projects_dir.iterdir()):
        if not project_dir.is_dir():
            continue
        sessions_dir = project_dir / "sessions"
        if not sessions_dir.exists():
            continue

        for session_dir in sorted(sessions_dir.iterdir()):
            if not session_dir.is_dir():
                continue

            metadata_path = session_dir / "metadata.json"
            events_path   = session_dir / "events.jsonl"
            if not metadata_path.exists() or not events_path.exists():
                continue

            try:
                meta = json.loads(metadata_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue

            session_id   = meta.get("session_id") or session_dir.name
            parent_id    = meta.get("parent_id")
            project_slug = meta.get("project_slug") or project_dir.name
            created      = meta.get("created", "")

            # Compute duration from session:start to session:end timestamps
            try:
                session_start_ms = normalize_timestamps(events_path)
                end_ms: int | None = None
                for evt in _read_events(events_path):
                    if evt.get("event") == "session:end":
                        end_ms = _ts_to_ms(evt["ts"])
                duration_ms = (end_ms - session_start_ms) if end_ms is not None else 0
            except (ValueError, OSError, KeyError):
                duration_ms = 0

            sessions[session_id] = SessionNode(
                session_id=session_id,
                project_slug=project_slug,
                parent_id=parent_id,
                start_ts=created,
                end_ts=None,
                duration_ms=duration_ms,
                cost_usd=0.0,
                total_cost_usd=0.0,
                spans=[],
                children=[],
                events_path=events_path,
            )

    return sessions


def build_tree(sessions: dict[str, SessionNode]) -> list[SessionNode]:
    """Link each child SessionNode to its parent; return root nodes.

    A root is any session whose parent_id is None or not present in `sessions`
    (i.e. the parent is an external session we don't have logs for).
    """
    for node in sessions.values():
        if node.parent_id and node.parent_id in sessions:
            sessions[node.parent_id].children.append(node)

    return [
        node
        for node in sessions.values()
        if not node.parent_id or node.parent_id not in sessions
    ]


def aggregate_costs(node: SessionNode) -> None:
    """Recursively propagate descendant costs up to this node.

    After this call, node.total_cost_usd = node.cost_usd + sum of all
    descendants' total_cost_usd values.
    """
    for child in node.children:
        aggregate_costs(child)
    node.total_cost_usd = node.cost_usd + sum(c.total_cost_usd for c in node.children)


def _parse_all_spans(node: SessionNode, root_start_ms: int) -> None:
    """Recursively parse spans for this node and all its descendants."""
    if node.events_path and node.events_path.exists():
        try:
            session_start_ms = normalize_timestamps(node.events_path)
        except ValueError:
            session_start_ms = root_start_ms
        node.spans    = parse_spans(node.events_path, root_start_ms, session_start_ms)
        node.cost_usd = sum(s.cost_usd for s in node.spans)
    for child in node.children:
        _parse_all_spans(child, root_start_ms)


def build_session_tree(amplifier_home: Path) -> list[SessionNode]:
    """Discover → parse → aggregate → return sorted root SessionNodes.

    Pipeline:
    1. DISCOVER  — scan all session directories, build stub nodes
    2. BUILD TREE — link children to parents, identify roots
    3. PARSE     — read events.jsonl for every session, extract spans + cost
    4. AGGREGATE — sum descendant costs up to each root
    5. NORMALIZE — timestamps are already ms offsets from root start (done in parse_spans)

    Returns root nodes sorted by start_ts descending (most-recent first).
    """
    sessions = discover_sessions(amplifier_home)
    if not sessions:
        return []

    roots = build_tree(sessions)

    for root in roots:
        if root.events_path and root.events_path.exists():
            try:
                root_start_ms = normalize_timestamps(root.events_path)
            except ValueError:
                root_start_ms = 0
        else:
            root_start_ms = 0
        _parse_all_spans(root, root_start_ms)
        aggregate_costs(root)

    return sorted(roots, key=lambda n: n.start_ts, reverse=True)
```

---

## Task 13: Run ALL viewer tests → verify GREEN, commit

**Step 1: Run all tests**

```bash
cd /Users/ken/workspace/ms/token-cost/viewer
python -m pytest tests/ -v
```

Expected output (abbreviated):
```
tests/test_pricing.py::TestComputeCost::test_claude_sonnet_basic_cost PASSED
... (18 pricing tests)

tests/test_reader.py::TestNormalizeTimestamps::test_returns_session_start_ms PASSED
tests/test_reader.py::TestNormalizeTimestamps::test_returns_int PASSED
tests/test_reader.py::TestParseSpansLlm::test_llm_span_created PASSED
... (16 span tests)

tests/test_reader.py::TestDiscoverSessions::test_finds_all_three_sessions PASSED
tests/test_reader.py::TestDiscoverSessions::test_session_ids_are_correct PASSED
tests/test_reader.py::TestDiscoverSessions::test_root_has_no_parent_id PASSED
tests/test_reader.py::TestDiscoverSessions::test_children_have_correct_parent_id PASSED
tests/test_reader.py::TestDiscoverSessions::test_session_node_has_project_slug PASSED
tests/test_reader.py::TestDiscoverSessions::test_empty_projects_dir_returns_empty PASSED
tests/test_reader.py::TestDiscoverSessions::test_session_node_has_events_path PASSED
tests/test_reader.py::TestBuildTree::test_returns_one_root PASSED
tests/test_reader.py::TestBuildTree::test_root_has_two_children PASSED
tests/test_reader.py::TestBuildTree::test_root_session_id PASSED
tests/test_reader.py::TestBuildTree::test_children_session_ids PASSED
tests/test_reader.py::TestAggregateCosts::test_root_total_includes_children PASSED
tests/test_reader.py::TestAggregateCosts::test_leaf_total_equals_own_cost PASSED
tests/test_reader.py::TestBuildSessionTree::test_returns_list_of_roots PASSED
tests/test_reader.py::TestBuildSessionTree::test_root_has_children PASSED
tests/test_reader.py::TestBuildSessionTree::test_root_spans_parsed PASSED
tests/test_reader.py::TestBuildSessionTree::test_own_cost_nonzero PASSED
tests/test_reader.py::TestBuildSessionTree::test_total_cost_aggregated PASSED
tests/test_reader.py::TestBuildSessionTree::test_sorted_most_recent_first PASSED

XX passed in 0.XXs
```

Every test must be PASSED with zero failures and zero errors.

**Troubleshooting:**
- If `test_session_ids_are_correct` fails with an import error on `viewer.tests.conftest`, change that import to use the string constants directly: `expected = {"root-aabbccdd", "child1-11223344", "child2-55667788"}` (no import needed).
- If `test_total_cost_aggregated` fails due to floating point, check that `claude-sonnet-4-5` is in `STATIC_PRICING` with `input_cost_per_token = 3.00e-6` and `output_cost_per_token = 15.00e-6`.

**Step 2: Final commit**

```bash
cd /Users/ken/workspace/ms/token-cost
git add viewer/amplifier_app_cost_viewer/reader.py \
        viewer/tests/conftest.py \
        viewer/tests/test_reader.py
git commit -m "feat(viewer): reader.py tree building — discover, build_tree, aggregate, build_session_tree"
```

---

## Phase 1 complete

At this point the following are fully implemented and tested:

| File | What it does |
|---|---|
| `viewer/pyproject.toml` | Package metadata, entry point, pytest config |
| `viewer/amplifier_app_cost_viewer/__init__.py` | Package marker |
| `viewer/amplifier_app_cost_viewer/__main__.py` | `amplifier-cost-viewer` CLI entry point |
| `viewer/amplifier_app_cost_viewer/pricing.py` | Static pricing table (LiteLLM-attributed), `compute_cost()`, `get_model_color()`, `load_pricing()` |
| `viewer/amplifier_app_cost_viewer/reader.py` | `Span`, `SessionNode` dataclasses, `normalize_timestamps()`, `parse_spans()`, `discover_sessions()`, `build_tree()`, `aggregate_costs()`, `build_session_tree()` |
| `viewer/tests/conftest.py` | `amp_home` fixture (3-session fake `~/.amplifier`) |
| `viewer/tests/test_pricing.py` | 18 pricing tests |
| `viewer/tests/test_reader.py` | 35 reader tests |

**Phase 2** adds `server.py` (4 FastAPI routes), the static frontend (`index.html`, `app.js`, `style.css`), and `scripts/update_pricing.py`.
