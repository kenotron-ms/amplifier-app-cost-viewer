#!/usr/bin/env python3
"""scripts/update_pricing.py — refresh STATIC_PRICING from the LiteLLM catalog.

Fetches model_prices_and_context_window.json from the LiteLLM GitHub repo,
extracts models for target providers, and rewrites the STATIC_PRICING block
in viewer/amplifier_app_cost_viewer/pricing.py.

Usage:
    python scripts/update_pricing.py
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
import urllib.request

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SOURCE_URL = (
    "https://raw.githubusercontent.com/BerriAI/litellm/main"
    "/model_prices_and_context_window.json"
)

# Canonical provider groups we want in STATIC_PRICING.
# Maps LiteLLM litellm_provider → our canonical group name.
# 'google' group captures Vertex AI language models (bare Gemini names).
PROVIDER_MAP: dict[str, str] = {
    "anthropic": "anthropic",
    "openai": "openai",
    "google": "google",
    "vertex_ai-language-models": "google",  # bare gemini-X.Y-Z names
}

TARGET_PROVIDERS: set[str] = {"anthropic", "openai", "google"}

CACHE_PATH = Path.home() / ".amplifier" / "pricing-cache.json"

# Path relative to this script's location: scripts/../viewer/...
PRICING_PY = (
    Path(__file__).parent / ".." / "viewer" / "amplifier_app_cost_viewer" / "pricing.py"
).resolve()

TIMEOUT = 15  # seconds

# Provider display order in the output block
PROVIDER_ORDER = ["anthropic", "openai", "google"]


# ---------------------------------------------------------------------------
# Network
# ---------------------------------------------------------------------------


def fetch_catalog() -> dict:
    """Fetch model prices JSON from LiteLLM GitHub."""
    req = urllib.request.Request(
        SOURCE_URL,
        headers={"User-Agent": "amplifier-update-pricing/1.0"},
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        raw = resp.read()
    return json.loads(raw.decode())


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------


def save_cache(data: dict) -> None:
    """Write the full catalog to ~/.amplifier/pricing-cache.json."""
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source": SOURCE_URL,
        "data": data,
    }
    CACHE_PATH.write_text(json.dumps(payload, indent=2))


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------


def extract_models(
    catalog: dict,
) -> dict[str, list[tuple[str, dict]]]:
    """Return models grouped by canonical provider name.

    Only includes models that:
    - have a litellm_provider mapping in PROVIDER_MAP
    - have both input_cost_per_token and output_cost_per_token
    """
    by_provider: dict[str, list[tuple[str, dict]]] = {p: [] for p in TARGET_PROVIDERS}

    for model_name, info in catalog.items():
        if not isinstance(info, dict):
            continue
        litellm_prov = info.get("litellm_provider", "")
        canonical = PROVIDER_MAP.get(litellm_prov)
        if canonical is None:
            continue

        input_cost = info.get("input_cost_per_token")
        output_cost = info.get("output_cost_per_token")
        if input_cost is None or output_cost is None:
            continue

        entry: dict = {
            "input_cost_per_token": input_cost,
            "output_cost_per_token": output_cost,
            "litellm_provider": canonical,
        }
        if "cache_read_input_token_cost" in info:
            entry["cache_read_input_token_cost"] = info["cache_read_input_token_cost"]
        if "cache_creation_input_token_cost" in info:
            entry["cache_creation_input_token_cost"] = info[
                "cache_creation_input_token_cost"
            ]

        by_provider[canonical].append((model_name, entry))

    # Sort each provider's list alphabetically by model name
    for provider in by_provider:
        by_provider[provider].sort(key=lambda x: x[0])

    return by_provider


# ---------------------------------------------------------------------------
# Code generation
# ---------------------------------------------------------------------------


def _fmt_float(value: float) -> str:
    """Format a float as a Python literal suitable for source code."""
    return repr(value)


def build_static_pricing_block(by_provider: dict[str, list[tuple[str, dict]]]) -> str:
    """Build the Python source block for STATIC_PRICING (including fmt markers)."""
    lines: list[str] = []
    lines.append("# fmt: off")
    lines.append("STATIC_PRICING: dict[str, dict] = {")

    for provider in PROVIDER_ORDER:
        models = by_provider.get(provider, [])
        if not models:
            continue
        lines.append(f"    # \u2500\u2500 {provider.capitalize()} \u2500\u2500")
        for model_name, entry in models:
            lines.append(f'    "{model_name}": {{')
            lines.append(
                f'        "input_cost_per_token": {_fmt_float(entry["input_cost_per_token"])},'
            )
            lines.append(
                f'        "output_cost_per_token": {_fmt_float(entry["output_cost_per_token"])},'
            )
            if "cache_read_input_token_cost" in entry:
                lines.append(
                    f'        "cache_read_input_token_cost": {_fmt_float(entry["cache_read_input_token_cost"])},'
                )
            if "cache_creation_input_token_cost" in entry:
                lines.append(
                    f'        "cache_creation_input_token_cost": {_fmt_float(entry["cache_creation_input_token_cost"])},'
                )
            lines.append(f'        "litellm_provider": "{provider}",')
            lines.append("    },")

    lines.append("}")
    lines.append("# fmt: on")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Rewrite pricing.py
# ---------------------------------------------------------------------------


def rewrite_pricing_py(new_block: str) -> None:
    """Replace the # fmt: off … # fmt: on section in pricing.py."""
    content = PRICING_PY.read_text()
    pattern = r"# fmt: off.*?# fmt: on"
    new_content, count = re.subn(pattern, new_block, content, flags=re.DOTALL)
    if count == 0:
        print(
            "ERROR: Could not find # fmt: off / # fmt: on markers in pricing.py",
            file=sys.stderr,
        )
        sys.exit(1)
    PRICING_PY.write_text(new_content)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    print(f"Fetching pricing catalog from:\n  {SOURCE_URL}")
    try:
        catalog = fetch_catalog()
    except Exception as exc:
        print(f"ERROR: Network unavailable or fetch failed: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Fetched {len(catalog)} entries. Caching to {CACHE_PATH} ...")
    save_cache(catalog)

    by_provider = extract_models(catalog)

    total = sum(len(v) for v in by_provider.values())
    new_block = build_static_pricing_block(by_provider)

    print(f"Rewriting {PRICING_PY} ...")
    rewrite_pricing_py(new_block)

    print(f"\nUpdated STATIC_PRICING with {total} models:")
    for provider in PROVIDER_ORDER:
        count = len(by_provider.get(provider, []))
        print(f"  {provider}: {count} models")


if __name__ == "__main__":
    main()
