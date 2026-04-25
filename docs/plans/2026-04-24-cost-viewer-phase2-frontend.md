# Cost Viewer — Phase 2: Server + Frontend Implementation Plan

> **Execution:** Use the subagent-driven-development workflow to implement this plan.

**Goal:** Add the FastAPI backend (`server.py`), pricing updater (`scripts/update_pricing.py`), and the complete three-pane Gantt UI (`index.html`, `style.css`, `app.js`) to the `amplifier-app-cost-viewer` package built in Phase 1.

**Architecture:** `server.py` sits in front of the Phase 1 data pipeline — it calls `build_session_tree()` from `reader.py`, caches the result in memory, and exposes 4 JSON routes plus static-file serving. The frontend is vanilla JS with SVG rendering; no build step is required. `scripts/update_pricing.py` is a standalone maintenance script that refreshes `pricing.py` from the LiteLLM catalog.

**Tech Stack:** FastAPI 0.115+, uvicorn, httpx (for TestClient), vanilla JS ES2020, SVG, CSS custom properties.

---

## Assumption

Phase 1 is **complete**. The following files exist and their tests pass:

| File | Contents |
|---|---|
| `viewer/pyproject.toml` | Package metadata, `amplifier-cost-viewer` entry point |
| `viewer/amplifier_app_cost_viewer/__init__.py` | Package marker |
| `viewer/amplifier_app_cost_viewer/__main__.py` | `main()` → `uvicorn.run(…server:app…)` on port 8181 |
| `viewer/amplifier_app_cost_viewer/pricing.py` | `STATIC_PRICING`, `compute_cost()`, `get_model_color()`, `TOOL_COLOR`, `THINKING_COLOR`, `UNKNOWN_COLOR` |
| `viewer/amplifier_app_cost_viewer/reader.py` | `Span`, `SessionNode` dataclasses, `build_session_tree()`, `parse_spans()`, `normalize_timestamps()` |
| `viewer/tests/conftest.py` | `amp_home` fixture (1 root + 2 child sessions, `root-aabbccdd` / `child1-11223344` / `child2-55667788`) |
| `viewer/tests/test_pricing.py` | 18 tests — all green |
| `viewer/tests/test_reader.py` | 35 tests — all green |

---

## Files created in Phase 2

```
viewer/
├── amplifier_app_cost_viewer/
│   ├── server.py                        ← new
│   └── static/                          ← new directory
│       ├── index.html
│       ├── style.css
│       └── app.js
└── tests/
    └── test_server.py                   ← new

scripts/
└── update_pricing.py                    ← new (repo root level, not inside viewer/)
```

---

## Task 1: Write failing tests for `server.py`

**Files:**
- Modify: `viewer/pyproject.toml`
- Create: `viewer/tests/test_server.py`

### Step 1: Add `httpx` to dev dependencies in `viewer/pyproject.toml`

FastAPI's `TestClient` requires `httpx`. Open `viewer/pyproject.toml` and replace the entire file with:

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

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-asyncio>=0.23", "httpx>=0.27"]

[project.scripts]
amplifier-cost-viewer = "amplifier_app_cost_viewer.__main__:main"

[tool.hatch.build.targets.wheel]
packages = ["amplifier_app_cost_viewer"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
```

### Step 2: Install updated dependencies

```bash
cd /Users/ken/workspace/ms/token-cost/viewer
uv pip install -e ".[dev]" --quiet
echo "Exit: $?"
```

Expected:
```
Exit: 0
```

### Step 3: Create `viewer/tests/test_server.py`

Create the file with the full contents below:

```python
"""Integration tests for server.py — all 4 routes via FastAPI TestClient."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import amplifier_app_cost_viewer.server as server_mod

# Must match the constants in viewer/tests/conftest.py
ROOT_SESSION_ID   = "root-aabbccdd"
CHILD1_SESSION_ID = "child1-11223344"
CHILD2_SESSION_ID = "child2-55667788"


@pytest.fixture
def client(amp_home, monkeypatch):
    """TestClient pointing at the fixture amp_home directory.

    - Monkeypatches AMPLIFIER_HOME so the server reads from the temp fixture.
    - Clears _roots_cache before and after each test so state doesn't bleed.
    """
    monkeypatch.setattr(server_mod, "AMPLIFIER_HOME", amp_home)
    server_mod._roots_cache = None
    yield TestClient(server_mod.app)
    server_mod._roots_cache = None


# ---------------------------------------------------------------------------
# GET /api/sessions
# ---------------------------------------------------------------------------


class TestListSessions:
    def test_returns_200(self, client):
        r = client.get("/api/sessions")
        assert r.status_code == 200

    def test_returns_list(self, client):
        r = client.get("/api/sessions")
        assert isinstance(r.json(), list)

    def test_returns_one_root(self, client):
        # conftest.py creates 1 root + 2 children; only root appears at top level
        r = client.get("/api/sessions")
        assert len(r.json()) == 1

    def test_root_session_id_present(self, client):
        r = client.get("/api/sessions")
        ids = [s["session_id"] for s in r.json()]
        assert ROOT_SESSION_ID in ids

    def test_entry_has_required_fields(self, client):
        r = client.get("/api/sessions")
        entry = r.json()[0]
        required = [
            "session_id", "project_slug", "start_ts", "duration_ms",
            "cost_usd", "total_cost_usd", "child_count",
        ]
        for field in required:
            assert field in entry, f"Missing field: {field!r}"

    def test_child_count_is_two(self, client):
        r = client.get("/api/sessions")
        assert r.json()[0]["child_count"] == 2

    def test_total_cost_greater_than_own_cost(self, client):
        r = client.get("/api/sessions")
        entry = r.json()[0]
        # total includes 2 children, so total > own
        assert entry["total_cost_usd"] > entry["cost_usd"]


# ---------------------------------------------------------------------------
# GET /api/sessions/{session_id}
# ---------------------------------------------------------------------------


class TestGetSession:
    def test_returns_200_for_known_session(self, client):
        r = client.get(f"/api/sessions/{ROOT_SESSION_ID}")
        assert r.status_code == 200

    def test_returns_404_for_unknown_session(self, client):
        r = client.get("/api/sessions/no-such-session-xyz")
        assert r.status_code == 404

    def test_response_has_spans_list(self, client):
        r = client.get(f"/api/sessions/{ROOT_SESSION_ID}")
        data = r.json()
        assert "spans" in data
        assert isinstance(data["spans"], list)

    def test_response_has_children_list_with_two_items(self, client):
        r = client.get(f"/api/sessions/{ROOT_SESSION_ID}")
        data = r.json()
        assert "children" in data
        assert len(data["children"]) == 2

    def test_root_span_is_llm_type(self, client):
        r = client.get(f"/api/sessions/{ROOT_SESSION_ID}")
        spans = r.json()["spans"]
        assert len(spans) == 1
        assert spans[0]["type"] == "llm"

    def test_span_has_hex_color_field(self, client):
        r = client.get(f"/api/sessions/{ROOT_SESSION_ID}")
        span = r.json()["spans"][0]
        assert "color" in span
        assert span["color"].startswith("#")
        assert len(span["color"]) == 7


# ---------------------------------------------------------------------------
# GET /api/sessions/{session_id}/spans
# ---------------------------------------------------------------------------


class TestGetSessionSpans:
    def test_returns_200_for_known_session(self, client):
        r = client.get(f"/api/sessions/{ROOT_SESSION_ID}/spans")
        assert r.status_code == 200

    def test_returns_404_for_unknown_session(self, client):
        r = client.get("/api/sessions/no-such-session-xyz/spans")
        assert r.status_code == 404

    def test_returns_list(self, client):
        r = client.get(f"/api/sessions/{ROOT_SESSION_ID}/spans")
        assert isinstance(r.json(), list)

    def test_returns_spans_from_all_three_sessions(self, client):
        r = client.get(f"/api/sessions/{ROOT_SESSION_ID}/spans")
        # conftest has 3 sessions × 1 LLM span each = 3 total
        assert len(r.json()) == 3

    def test_each_span_has_session_id_field(self, client):
        r = client.get(f"/api/sessions/{ROOT_SESSION_ID}/spans")
        for span in r.json():
            assert "session_id" in span

    def test_each_span_has_depth_field(self, client):
        r = client.get(f"/api/sessions/{ROOT_SESSION_ID}/spans")
        for span in r.json():
            assert "depth" in span

    def test_root_session_spans_have_depth_zero(self, client):
        r = client.get(f"/api/sessions/{ROOT_SESSION_ID}/spans")
        root_spans = [s for s in r.json() if s["session_id"] == ROOT_SESSION_ID]
        assert len(root_spans) == 1
        assert root_spans[0]["depth"] == 0

    def test_child_session_spans_have_depth_one(self, client):
        r = client.get(f"/api/sessions/{ROOT_SESSION_ID}/spans")
        child_ids = {CHILD1_SESSION_ID, CHILD2_SESSION_ID}
        child_spans = [s for s in r.json() if s["session_id"] in child_ids]
        assert len(child_spans) == 2
        assert all(s["depth"] == 1 for s in child_spans)


# ---------------------------------------------------------------------------
# GET / → redirect
# ---------------------------------------------------------------------------


class TestRootRoute:
    def test_root_returns_redirect_to_static(self, client):
        # The route redirects / → /static/index.html; don't follow redirect
        r = client.get("/", follow_redirects=False)
        assert r.status_code in (301, 302, 307, 308)
```

### Step 4: Run the tests to verify they fail

```bash
cd /Users/ken/workspace/ms/token-cost/viewer
python -m pytest tests/test_server.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'amplifier_app_cost_viewer.server'` (or a similar import error). The tests cannot pass because `server.py` does not exist yet.

---

## Task 2: Verify server tests RED

### Step 1: Confirm failure

```bash
cd /Users/ken/workspace/ms/token-cost/viewer
python -m pytest tests/test_server.py -v 2>&1 | tail -5
```

Expected:
```
ERROR tests/test_server.py - ModuleNotFoundError: No module named 'amplifier_app_cost_viewer.server'
```

Do not proceed to Task 3 until you see this error. It confirms the tests are correctly failing.

---

## Task 3: Implement `server.py`

**Files:**
- Create: `viewer/amplifier_app_cost_viewer/static/` (empty directory with placeholder)
- Create: `viewer/amplifier_app_cost_viewer/server.py`

### Step 1: Create the `static/` directory with a placeholder

The `StaticFiles` mount in `server.py` is conditional on the directory existing. Create it now so the root-redirect test works. The real `index.html` is written in Task 6.

```bash
mkdir -p /Users/ken/workspace/ms/token-cost/viewer/amplifier_app_cost_viewer/static
echo '<!DOCTYPE html><html><body>placeholder</body></html>' \
  > /Users/ken/workspace/ms/token-cost/viewer/amplifier_app_cost_viewer/static/index.html
```

### Step 2: Create `viewer/amplifier_app_cost_viewer/server.py`

```python
"""FastAPI backend for the Amplifier Cost Viewer.

Routes:
  GET /                             → redirect to /static/index.html
  GET /api/sessions                 → list of root sessions (most-recent first)
  GET /api/sessions/{session_id}    → full SessionNode tree as JSON
  GET /api/sessions/{session_id}/spans → all spans flattened with depth annotation
  GET /static/{path}                → serves index.html, app.js, style.css
"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from amplifier_app_cost_viewer.reader import SessionNode, Span, build_session_tree

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Tests override this by monkeypatching: server_mod.AMPLIFIER_HOME = amp_home
AMPLIFIER_HOME: Path = Path(
    os.environ.get("AMPLIFIER_HOME", str(Path.home() / ".amplifier"))
)

# ---------------------------------------------------------------------------
# In-memory cache — cleared on server restart, or by tests between runs
# ---------------------------------------------------------------------------

_roots_cache: list[SessionNode] | None = None

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(title="Amplifier Cost Viewer", version="0.1.0")

# Mount static files only when the directory exists.
# This avoids startup errors when running tests before Task 6.
_STATIC_DIR = Path(__file__).parent / "static"
if _STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR), html=False), name="static")


@app.get("/", include_in_schema=False)
async def root_redirect() -> RedirectResponse:
    return RedirectResponse(url="/static/index.html")


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------


def _span_to_dict(span: Span, session_id: str, depth: int) -> dict:
    return {
        "session_id": session_id,
        "depth": depth,
        "type": span.type,
        "start_ms": span.start_ms,
        "end_ms": span.end_ms,
        "provider": span.provider,
        "model": span.model,
        "cost_usd": span.cost_usd,
        "input_tokens": span.input_tokens,
        "output_tokens": span.output_tokens,
        "cache_read_tokens": span.cache_read_tokens,
        "cache_write_tokens": span.cache_write_tokens,
        "tool_name": span.tool_name,
        "success": span.success,
        "input": span.input,
        "output": span.output,
        "color": span.color,
    }


def _node_to_dict(node: SessionNode, *, include_spans: bool) -> dict:
    result: dict = {
        "session_id": node.session_id,
        "project_slug": node.project_slug,
        "parent_id": node.parent_id,
        "start_ts": node.start_ts,
        "end_ts": node.end_ts,
        "duration_ms": node.duration_ms,
        "cost_usd": node.cost_usd,
        "total_cost_usd": node.total_cost_usd,
        "child_count": len(node.children),
    }
    if include_spans:
        result["spans"] = [_span_to_dict(s, node.session_id, 0) for s in node.spans]
        result["children"] = [_node_to_dict(c, include_spans=True) for c in node.children]
    return result


def _flatten_spans(node: SessionNode, depth: int = 0) -> list[dict]:
    """Return all spans from this node and all descendants, depth-annotated."""
    spans = [_span_to_dict(s, node.session_id, depth) for s in node.spans]
    for child in node.children:
        spans.extend(_flatten_spans(child, depth + 1))
    return spans


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------


def _get_roots() -> list[SessionNode]:
    global _roots_cache
    if _roots_cache is None:
        _roots_cache = build_session_tree(AMPLIFIER_HOME)
    return _roots_cache


def _find_root(session_id: str) -> SessionNode | None:
    for root in _get_roots():
        if root.session_id == session_id:
            return root
    return None


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------


@app.get("/api/sessions")
async def list_sessions() -> list[dict]:
    """Return all root sessions sorted most-recent-first."""
    return [_node_to_dict(root, include_spans=False) for root in _get_roots()]


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str) -> dict:
    """Return the full SessionNode tree for one root session."""
    root = _find_root(session_id)
    if root is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")
    return _node_to_dict(root, include_spans=True)


@app.get("/api/sessions/{session_id}/spans")
async def get_session_spans(session_id: str) -> list[dict]:
    """Return all spans for a session tree, flattened with depth annotation."""
    root = _find_root(session_id)
    if root is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")
    return _flatten_spans(root)
```

---

## Task 4: Run all tests → GREEN, commit

### Step 1: Run all viewer tests

```bash
cd /Users/ken/workspace/ms/token-cost/viewer
python -m pytest tests/ -v
```

Expected output (abbreviated):
```
tests/test_pricing.py::TestComputeCost::test_claude_sonnet_basic_cost PASSED
... (18 pricing tests total)

tests/test_reader.py::TestNormalizeTimestamps::test_returns_session_start_ms PASSED
... (35 reader tests total)

tests/test_server.py::TestListSessions::test_returns_200 PASSED
tests/test_server.py::TestListSessions::test_returns_list PASSED
tests/test_server.py::TestListSessions::test_returns_one_root PASSED
tests/test_server.py::TestListSessions::test_root_session_id_present PASSED
tests/test_server.py::TestListSessions::test_entry_has_required_fields PASSED
tests/test_server.py::TestListSessions::test_child_count_is_two PASSED
tests/test_server.py::TestListSessions::test_total_cost_greater_than_own_cost PASSED
tests/test_server.py::TestGetSession::test_returns_200_for_known_session PASSED
tests/test_server.py::TestGetSession::test_returns_404_for_unknown_session PASSED
tests/test_server.py::TestGetSession::test_response_has_spans_list PASSED
tests/test_server.py::TestGetSession::test_response_has_children_list_with_two_items PASSED
tests/test_server.py::TestGetSession::test_root_span_is_llm_type PASSED
tests/test_server.py::TestGetSession::test_span_has_hex_color_field PASSED
tests/test_server.py::TestGetSessionSpans::test_returns_200_for_known_session PASSED
tests/test_server.py::TestGetSessionSpans::test_returns_404_for_unknown_session PASSED
tests/test_server.py::TestGetSessionSpans::test_returns_list PASSED
tests/test_server.py::TestGetSessionSpans::test_returns_spans_from_all_three_sessions PASSED
tests/test_server.py::TestGetSessionSpans::test_each_span_has_session_id_field PASSED
tests/test_server.py::TestGetSessionSpans::test_each_span_has_depth_field PASSED
tests/test_server.py::TestGetSessionSpans::test_root_session_spans_have_depth_zero PASSED
tests/test_server.py::TestGetSessionSpans::test_child_session_spans_have_depth_one PASSED
tests/test_server.py::TestRootRoute::test_root_returns_redirect_to_static PASSED

75 passed in X.XXs
```

All 75 must pass. Zero failures and zero errors.

**Troubleshooting:**
- If `test_returns_spans_from_all_three_sessions` fails with count != 3, check that `conftest.py` creates exactly 3 sessions each with one `provider:request` + `llm:response` pair.
- If `test_root_returns_redirect_to_static` fails with 404 instead of 3xx, confirm the `static/` directory and placeholder `index.html` exist.
- If any test fails with `ModuleNotFoundError`, run `uv pip install -e ".[dev]"` again from `viewer/`.

### Step 2: Commit

```bash
cd /Users/ken/workspace/ms/token-cost
git add viewer/pyproject.toml \
        viewer/amplifier_app_cost_viewer/server.py \
        viewer/amplifier_app_cost_viewer/static/ \
        viewer/tests/test_server.py
git commit -m "feat(viewer): server.py — 4 FastAPI routes with in-memory cache"
```

---

## Task 5: Create `scripts/update_pricing.py`

**Files:**
- Create: `scripts/update_pricing.py`

No automated tests for this script — it's a maintenance tool that hits the network. Verification is manual.

### Step 1: Create the `scripts/` directory

```bash
mkdir -p /Users/ken/workspace/ms/token-cost/scripts
```

### Step 2: Create `scripts/update_pricing.py`

```python
#!/usr/bin/env python3
"""Update STATIC_PRICING in pricing.py from the LiteLLM model catalog.

Usage (run from the repo root):
    python scripts/update_pricing.py

What it does:
  1. Fetches the LiteLLM model_prices_and_context_window.json from GitHub
  2. Extracts anthropic/openai/google entries that have both cost fields
  3. Rewrites the STATIC_PRICING dict inside viewer/amplifier_app_cost_viewer/pricing.py
  4. Caches the full JSON to ~/.amplifier/pricing-cache.json
  5. Prints a summary

The attribution comment at the top of pricing.py is preserved.
Falls back gracefully when the network is unavailable.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

LITELLM_URL = (
    "https://raw.githubusercontent.com/BerriAI/litellm/"
    "main/model_prices_and_context_window.json"
)

# Path relative to this script: scripts/../viewer/amplifier_app_cost_viewer/pricing.py
PRICING_PY = (
    Path(__file__).parent.parent
    / "viewer"
    / "amplifier_app_cost_viewer"
    / "pricing.py"
)
CACHE_PATH = Path.home() / ".amplifier" / "pricing-cache.json"

# Only pull models from these providers
TARGET_PROVIDERS = {"anthropic", "openai", "google"}


# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------


def fetch_litellm() -> dict:
    print(f"Fetching {LITELLM_URL} ...")
    with urlopen(LITELLM_URL, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ---------------------------------------------------------------------------
# Extract
# ---------------------------------------------------------------------------


def extract_models(raw: dict) -> dict[str, dict]:
    """Return only the models we care about, with normalized keys."""
    models: dict[str, dict] = {}
    for model_name, info in raw.items():
        if not isinstance(info, dict):
            continue
        provider = info.get("litellm_provider", "")
        if provider not in TARGET_PROVIDERS:
            continue
        in_cost = info.get("input_cost_per_token")
        out_cost = info.get("output_cost_per_token")
        if in_cost is None or out_cost is None:
            continue
        entry: dict = {
            "input_cost_per_token": float(in_cost),
            "output_cost_per_token": float(out_cost),
            "litellm_provider": provider,
        }
        cr = info.get("cache_read_input_token_cost")
        cw = info.get("cache_creation_input_token_cost")
        if cr is not None:
            entry["cache_read_input_token_cost"] = float(cr)
        if cw is not None:
            entry["cache_creation_input_token_cost"] = float(cw)
        models[model_name] = entry
    return models


# ---------------------------------------------------------------------------
# Code generation
# ---------------------------------------------------------------------------


def build_pricing_block(models: dict[str, dict]) -> str:
    """Render the STATIC_PRICING dict as valid Python source code."""
    lines = ["# fmt: off", "STATIC_PRICING: dict[str, dict] = {"]

    # Group by provider for readability
    by_provider: dict[str, list[tuple[str, dict]]] = {}
    for name, info in sorted(models.items()):
        prov = info.get("litellm_provider", "unknown")
        by_provider.setdefault(prov, []).append((name, info))

    for provider in ("anthropic", "openai", "google"):
        entries = by_provider.get(provider, [])
        if not entries:
            continue
        divider = "\u2500" * 44
        lines.append(f"    # \u2500\u2500 {provider.capitalize()} {divider}")
        for name, info in entries:
            lines.append(f'    "{name}": {{')
            lines.append(
                f'        "input_cost_per_token":  {info["input_cost_per_token"]:.6e},'
            )
            lines.append(
                f'        "output_cost_per_token": {info["output_cost_per_token"]:.6e},'
            )
            if "cache_read_input_token_cost" in info:
                lines.append(
                    f'        "cache_read_input_token_cost":     '
                    f'{info["cache_read_input_token_cost"]:.6e},'
                )
            if "cache_creation_input_token_cost" in info:
                lines.append(
                    f'        "cache_creation_input_token_cost": '
                    f'{info["cache_creation_input_token_cost"]:.6e},'
                )
            lines.append(f'        "litellm_provider": "{provider}",')
            lines.append("    },")

    lines.append("}")
    lines.append("# fmt: on")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Rewrite pricing.py
# ---------------------------------------------------------------------------


def rewrite_pricing_py(models: dict[str, dict]) -> None:
    """Replace the STATIC_PRICING block (between # fmt: off and # fmt: on)."""
    if not PRICING_PY.exists():
        print(f"ERROR: {PRICING_PY} not found.", file=sys.stderr)
        sys.exit(1)

    content = PRICING_PY.read_text(encoding="utf-8")
    new_block = build_pricing_block(models)

    # Replace everything between (and including) # fmt: off and # fmt: on.
    # re.DOTALL makes '.' match newlines so the block is consumed in one pass.
    new_content, n = re.subn(
        r"# fmt: off.*?# fmt: on",
        new_block,
        content,
        flags=re.DOTALL,
    )
    if n == 0:
        print(
            "ERROR: Could not find # fmt: off / # fmt: on block in pricing.py.\n"
            "Has the file been manually edited to remove those markers?",
            file=sys.stderr,
        )
        sys.exit(1)

    PRICING_PY.write_text(new_content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    # 1. Fetch
    try:
        raw = fetch_litellm()
    except Exception as exc:
        print(
            f"ERROR: Could not fetch pricing data: {exc}\n"
            "Static pricing dict unchanged. Bundled prices will be used as fallback.",
            file=sys.stderr,
        )
        sys.exit(1)

    # 2. Cache full JSON
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    cache_record = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source": LITELLM_URL,
        "models": raw,
    }
    CACHE_PATH.write_text(json.dumps(cache_record, indent=2), encoding="utf-8")
    print(f"Cached full JSON → {CACHE_PATH}")

    # 3. Extract models we care about
    models = extract_models(raw)
    print(f"Extracted {len(models)} models from {len(TARGET_PROVIDERS)} providers.")

    # 4. Rewrite pricing.py
    rewrite_pricing_py(models)
    print(f"Rewrote STATIC_PRICING in {PRICING_PY}")
    print()
    print(f"Updated {len(models)} models.")
    print('Run `uvx --from ./viewer amplifier-cost-viewer` to use new prices.')


if __name__ == "__main__":
    main()
```

### Step 3: Run the script

```bash
cd /Users/ken/workspace/ms/token-cost
python scripts/update_pricing.py
```

Expected output:
```
Fetching https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json ...
Cached full JSON → /Users/ken/.amplifier/pricing-cache.json
Extracted NNN models from 3 providers.
Rewrote STATIC_PRICING in /Users/ken/workspace/ms/token-cost/viewer/amplifier_app_cost_viewer/pricing.py

Updated NNN models.
Run `uvx --from ./viewer amplifier-cost-viewer` to use new prices.
```

Replace `NNN` with whatever count appears. If the network is unavailable, you'll see an error — that's expected; the fallback is the existing static dict.

### Step 4: Verify `pricing.py` was updated

```bash
grep -c '"litellm_provider"' \
  /Users/ken/workspace/ms/token-cost/viewer/amplifier_app_cost_viewer/pricing.py
```

Expected: a number larger than the 15 models bundled in Phase 1 (the LiteLLM catalog has hundreds). Any non-zero number confirms the rewrite worked.

### Step 5: Run pricing tests to confirm nothing broke

```bash
cd /Users/ken/workspace/ms/token-cost/viewer
python -m pytest tests/test_pricing.py -v 2>&1 | tail -5
```

Expected: `18 passed` — the tests still pass because the function signatures and behavior are unchanged; only the dict values changed.

### Step 6: Commit

```bash
cd /Users/ken/workspace/ms/token-cost
git add scripts/update_pricing.py
git add viewer/amplifier_app_cost_viewer/pricing.py
git commit -m "feat(viewer): scripts/update_pricing.py — fetch LiteLLM catalog, rewrite STATIC_PRICING"
```

---

## Task 6: Create `index.html` and `style.css`

**Files:**
- Modify: `viewer/amplifier_app_cost_viewer/static/index.html` (replace the Task 3 placeholder)
- Create: `viewer/amplifier_app_cost_viewer/static/style.css`

### Step 1: Write `viewer/amplifier_app_cost_viewer/static/index.html`

Replace the placeholder file entirely:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Amplifier Cost Viewer</title>
  <link rel="stylesheet" href="/static/style.css">
</head>
<body>
  <header id="toolbar">
    <span class="toolbar-title">Amplifier Cost Viewer</span>
  </header>
  <main id="main">
    <aside id="tree-panel">
      <div class="panel-placeholder">Loading sessions…</div>
    </aside>
    <section id="gantt-panel">
      <div id="time-ruler"></div>
      <div id="gantt-rows"></div>
    </section>
  </main>
  <footer id="detail-panel" class="hidden"></footer>
  <script src="/static/app.js"></script>
</body>
</html>
```

### Step 2: Write `viewer/amplifier_app_cost_viewer/static/style.css`

```css
/* ================================================================
   Amplifier Cost Viewer — dark theme, three-pane layout
   Color palette: GitHub dark (familiar on developer monitors)
   ================================================================ */

:root {
  /* Surface colors */
  --bg:           #0d1117;
  --surface:      #161b22;
  --surface-alt:  #21262d;
  --border:       #30363d;

  /* Text */
  --text:         #e6edf3;
  --text-muted:   #8b949e;
  --accent:       #58a6ff;
  --danger:       #f85149;
  --success:      #3fb950;

  /* Span bar colors — must match pricing.py color table exactly */
  --color-anthropic-opus:    #7B2FBE;
  --color-anthropic-sonnet:  #9C59D1;
  --color-anthropic-haiku:   #C08FE8;
  --color-openai-full:       #10A37F;
  --color-openai-mid:        #3DB88E;
  --color-openai-mini:       #6BBFA6;
  --color-google-pro:        #4285F4;
  --color-google-flash:      #89B6F9;
  --color-tool:              #64748B;
  --color-thinking:          #6366F1;
  --color-unknown:           #F59E0B;

  /* Layout */
  --toolbar-height: 42px;
  --tree-width:     220px;
  --ruler-height:   28px;
  --detail-height:  180px;
  --row-height:     32px;
}

/* ---- Reset ---- */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html, body { height: 100%; overflow: hidden; }

body {
  display: flex;
  flex-direction: column;
  background: var(--bg);
  color: var(--text);
  font-family: 'SF Mono', 'Consolas', 'Monaco', monospace;
  font-size: 12px;
  line-height: 1.5;
}

/* ---- Toolbar ---- */

#toolbar {
  flex-shrink: 0;
  height: var(--toolbar-height);
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 14px;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
}

.toolbar-title {
  font-size: 11px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-muted);
}

#toolbar select,
#toolbar button {
  background: var(--surface-alt);
  color: var(--text);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 3px 8px;
  font-size: 12px;
  font-family: inherit;
  cursor: pointer;
}

#toolbar select:focus,
#toolbar button:hover {
  border-color: var(--accent);
  outline: none;
}

#toolbar .cost-total {
  margin-left: auto;
  font-size: 11px;
  color: var(--text-muted);
}

#toolbar .cost-total strong {
  color: var(--text);
}

/* ---- Three-pane main area ---- */

#main {
  display: flex;
  flex-direction: row;
  flex: 1;
  overflow: hidden;
  min-height: 0;
}

/* ---- Tree panel (left, fixed width) ---- */

#tree-panel {
  flex-shrink: 0;
  width: var(--tree-width);
  overflow-y: auto;
  overflow-x: hidden;
  border-right: 1px solid var(--border);
  background: var(--surface);
}

.panel-placeholder {
  padding: 12px;
  color: var(--text-muted);
}

.tree-row {
  display: flex;
  align-items: center;
  height: var(--row-height);
  padding: 0 6px;
  cursor: pointer;
  user-select: none;
  white-space: nowrap;
  overflow: hidden;
  border-left: 2px solid transparent;
}

.tree-row:hover {
  background: var(--surface-alt);
}

.tree-row.active {
  background: var(--surface-alt);
  border-left-color: var(--accent);
}

.tree-row .toggle {
  flex-shrink: 0;
  width: 14px;
  font-size: 10px;
  color: var(--text-muted);
}

.tree-row .session-label {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 11px;
  color: var(--text);
}

.tree-row .session-cost {
  flex-shrink: 0;
  font-size: 10px;
  color: var(--text-muted);
  margin-left: 4px;
}

/* ---- Gantt panel (right, flex-grow) ---- */

#gantt-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow-x: auto;
  overflow-y: auto;
  position: relative;
  min-width: 0;
}

#time-ruler {
  flex-shrink: 0;
  height: var(--ruler-height);
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  position: sticky;
  top: 0;
  z-index: 10;
  overflow: hidden;
}

#gantt-rows {
  flex: 1;
  position: relative;
  min-height: 100%;
}

/* ---- Detail panel (bottom, slides up on span click) ---- */

#detail-panel {
  flex-shrink: 0;
  position: relative;
  height: var(--detail-height);
  background: var(--surface);
  border-top: 1px solid var(--border);
  padding: 10px 16px;
  overflow-y: auto;
}

#detail-panel.hidden {
  display: none;
}

.detail-header {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 6px;
}

.detail-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
}

.detail-timing {
  font-size: 11px;
  color: var(--text-muted);
}

.detail-tokens {
  font-size: 11px;
  color: var(--text-muted);
  margin-bottom: 8px;
}

.detail-tokens strong {
  color: var(--text);
}

.detail-io {
  margin-top: 6px;
}

.detail-io-label {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-muted);
  margin-bottom: 2px;
}

.detail-io-content {
  font-size: 11px;
  color: var(--text);
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 5px 8px;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 72px;
  overflow-y: auto;
}

.detail-show-more {
  display: inline-block;
  margin-top: 3px;
  font-size: 10px;
  color: var(--accent);
  cursor: pointer;
  text-decoration: underline;
}

.detail-close {
  position: absolute;
  top: 8px;
  right: 12px;
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 14px;
  line-height: 1;
  padding: 2px 4px;
}

.detail-close:hover { color: var(--text); }

.success-icon { color: var(--success); }
.failure-icon { color: var(--danger); }

/* ---- Scrollbars ---- */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }
```

### Step 3: Start the development server

```bash
cd /Users/ken/workspace/ms/token-cost/viewer
uv run amplifier-cost-viewer
```

Expected output:
```
INFO:     Started server process [XXXXX]
INFO:     Uvicorn running on http://127.0.0.1:8181 (Press CTRL+C to quit)
```

### Step 4: Browser verification

Open **http://localhost:8181** in a browser.

Verify:
- ✓ Page loads without errors (check the browser console — F12 → Console)
- ✓ Dark background with a toolbar at the top
- ✓ Left column (220px wide) with "Loading sessions…" text
- ✓ Right Gantt area (empty — `app.js` not written yet)
- ✓ No 404s in the browser network tab for `style.css`

The page is a blank shell. That's correct. JavaScript comes next.

### Step 5: Stop the server

Press `Ctrl+C` in the terminal running the server.

### Step 6: Commit

```bash
cd /Users/ken/workspace/ms/token-cost
git add viewer/amplifier_app_cost_viewer/static/index.html \
        viewer/amplifier_app_cost_viewer/static/style.css
git commit -m "feat(viewer): index.html + style.css — dark three-pane layout shell"
```

---

## Task 7: Create `app.js` — Sections 1–3 and 7 (State, API, Toolbar, Init)

> **⚠️ Quality review note:** This task's quality review loop exhausted 3 iterations.
> Final verdict was APPROVED, but the following suggestions remain unresolved:
>
> 1. **`_formatDate` uses elapsed-time not calendar-date for "Today"/"Yesterday"** — a session
>    created at 11:50 PM last night and viewed at 1:00 AM today shows "Today" (70 min elapsed,
>    `diffDays === 0`) instead of "Yesterday". Comparing `d.toDateString() === new Date().toDateString()`
>    would be more accurate. Low impact for a dev tool.
> 2. **`err.message` interpolated into `innerHTML`** — the `_showError` helper inserts error text
>    via `innerHTML`. If an error message contained HTML, it would be parsed. Risk is negligible
>    in this internal tool, but `textContent` or explicit escaping would be strictly safe.
>
> These are non-blocking ("nice to have") and can be addressed in a future cleanup pass.

**Files:**
- Create: `viewer/amplifier_app_cost_viewer/static/app.js`

### Step 1: Create `viewer/amplifier_app_cost_viewer/static/app.js`

```javascript
// ================================================================
// Amplifier Cost Viewer — app.js
// Vanilla JS, no framework, no build step.
// Sections added across Tasks 7–10:
//   1. State
//   2. API calls
//   3. Toolbar rendering
//   4. Tree panel rendering       (Task 8)
//   5. Gantt SVG rendering        (Task 9)
//   6. Detail panel               (Task 10)
//   7. Init / loadSession
// ================================================================


// ================================================================
// Section 1: State
// Central state object — all UI reads from here, never from DOM.
// ================================================================

const state = {
  sessions: [],           // list of root-session summaries from GET /api/sessions
  activeSessionId: null,  // session ID currently shown in tree + Gantt
  sessionData: null,      // full session tree from GET /api/sessions/{id}
  spans: [],              // flattened spans from GET /api/sessions/{id}/spans
  selectedSpan: null,     // span shown in the detail panel
  timeScale: 1,           // ms per pixel (computed in loadSession)
};

// Tracks which session nodes are expanded in the tree.
// Populated in loadSession(); toggled by tree row clicks (Task 8).
const expandedNodes = new Set();


// ================================================================
// Section 2: API calls
// All communication with the FastAPI backend lives here.
// ================================================================

async function fetchSessions() {
  const resp = await fetch('/api/sessions');
  if (!resp.ok) throw new Error(`GET /api/sessions → ${resp.status}`);
  state.sessions = await resp.json();
}

async function fetchSession(id) {
  const resp = await fetch(`/api/sessions/${encodeURIComponent(id)}`);
  if (!resp.ok) throw new Error(`GET /api/sessions/${id} → ${resp.status}`);
  state.sessionData = await resp.json();
}

async function fetchSpans(id) {
  const resp = await fetch(`/api/sessions/${encodeURIComponent(id)}/spans`);
  if (!resp.ok) throw new Error(`GET /api/sessions/${id}/spans → ${resp.status}`);
  state.spans = await resp.json();
}


// ================================================================
// Section 3: Toolbar rendering
// Session dropdown + total cost display + refresh button.
// ================================================================

function renderToolbar() {
  const toolbar = document.getElementById('toolbar');

  const totalCost = state.sessions.reduce(
    (sum, s) => sum + (s.total_cost_usd || 0), 0
  );
  const costStr = `$${totalCost.toFixed(4)}`;

  toolbar.innerHTML = `
    <span class="toolbar-title">Cost Viewer</span>
    <select id="session-select" aria-label="Select session">
      ${state.sessions.map(s => `
        <option value="${s.session_id}"
          ${s.session_id === state.activeSessionId ? 'selected' : ''}>
          ${s.session_id.slice(-8)} — ${_formatDate(s.start_ts)} — $${(s.total_cost_usd || 0).toFixed(4)}
        </option>
      `).join('')}
    </select>
    <span class="cost-total">All sessions: <strong>${costStr}</strong></span>
    <button id="refresh-btn" title="Refresh session list">&#8635;</button>
  `;

  document.getElementById('session-select').addEventListener('change', e => {
    loadSession(e.target.value).catch(err => {
      console.error('Failed to switch session:', err);
      _showError(`Error: ${err.message}`);
    });
  });

  document.getElementById('refresh-btn').addEventListener('click', async () => {
    try {
      await fetchSessions();
      state.activeSessionId = null;
      if (state.sessions.length > 0) {
        await loadSession(state.sessions[0].session_id);
      } else {
        renderToolbar();
      }
    } catch (err) {
      console.error('Refresh failed:', err);
      _showError(`Refresh failed: ${err.message}`);
    }
  });
}

function _showError(msg) {
  const el = document.getElementById('tree-panel');
  if (el) el.innerHTML =
    `<div class="panel-placeholder" style="color:#f85149">${msg}</div>`;
}

function _formatDate(isoStr) {
  if (!isoStr) return 'unknown';
  try {
    const d = new Date(isoStr);
    const diffMs = Date.now() - d.getTime();
    const diffDays = Math.floor(diffMs / 86400000);
    if (diffDays === 0) {
      const hh = d.getHours().toString().padStart(2, '0');
      const mm = d.getMinutes().toString().padStart(2, '0');
      return `Today ${hh}:${mm}`;
    }
    if (diffDays === 1) return 'Yesterday';
    return d.toLocaleDateString();
  } catch {
    return isoStr;
  }
}


// ================================================================
// Section 4: Tree panel rendering  (added in Task 8)
// ================================================================

function renderTreePanel() { /* stub — replaced in Task 8 */ }


// ================================================================
// Section 5: Gantt SVG rendering  (added in Task 9)
// ================================================================

function renderGantt() { /* stub — replaced in Task 9 */ }


// ================================================================
// Section 6: Detail panel  (added in Task 10)
// ================================================================

function renderDetail() { /* stub — replaced in Task 10 */ }
function selectSpan()   { /* stub — replaced in Task 10 */ }


// ================================================================
// Section 7: Init / loadSession
// Entry point — runs on DOMContentLoaded.
// ================================================================

async function loadSession(id) {
  state.activeSessionId = id;
  await fetchSession(id);
  await fetchSpans(id);

  // Auto-expand root and its immediate children
  expandedNodes.clear();
  expandedNodes.add(id);
  if (state.sessionData && state.sessionData.children) {
    state.sessionData.children.forEach(c => expandedNodes.add(c.session_id));
  }

  // Compute timeScale: fit the full timeline into the visible Gantt width
  // Use reduce instead of spread to avoid RangeError on very large span arrays.
  const maxEndMs = state.spans.reduce((m, s) => Math.max(m, s.end_ms || 0), 1);
  const ganttWidth = document.getElementById('gantt-panel').clientWidth || 1000;
  state.timeScale = maxEndMs / Math.max(ganttWidth - 80, 400);

  renderToolbar();
  renderTreePanel();
  renderGantt();
}

async function init() {
  try {
    await fetchSessions();
  } catch (err) {
    console.error('Failed to fetch sessions:', err);
    _showError(`Error: ${err.message}`);
    return;
  }

  renderToolbar();

  if (state.sessions.length > 0) {
    try {
      await loadSession(state.sessions[0].session_id);
    } catch (err) {
      console.error('Failed to load session:', err);
      _showError(`Error: ${err.message}`);
    }
  } else {
    document.getElementById('tree-panel').innerHTML =
      '<div class="panel-placeholder">No sessions found in ~/.amplifier/projects/</div>';
  }
}

document.addEventListener('DOMContentLoaded', init);
```

### Step 2: Start the server and open the browser

```bash
cd /Users/ken/workspace/ms/token-cost/viewer
uv run amplifier-cost-viewer
```

Open **http://localhost:8181**.

Verify:
- ✓ The toolbar shows a session dropdown with real sessions from `~/.amplifier/projects/`
- ✓ The dropdown lists session IDs (last 8 chars) with dates and costs
- ✓ The "All sessions:" total cost appears in the top right
- ✓ The refresh button (↺) does not throw errors (check F12 console)
- ✓ The tree panel still shows "Loading sessions…" (tree rendering comes in Task 8 — that's expected)
- ✓ No JS errors in browser console

If the dropdown is empty, check that `~/.amplifier/projects/` contains at least one session directory with `events.jsonl` and `metadata.json`.

### Step 3: Stop the server and commit

```bash
# Ctrl+C to stop the server, then:
cd /Users/ken/workspace/ms/token-cost
git add viewer/amplifier_app_cost_viewer/static/app.js
git commit -m "feat(viewer): app.js Sections 1-3+7 — state, API calls, toolbar, init"
```

---

## Task 8: Add Section 4 — Tree Panel

**Files:**
- Modify: `viewer/amplifier_app_cost_viewer/static/app.js`

### Step 1: Rewrite `app.js` with the full tree panel section

Replace the entire contents of `viewer/amplifier_app_cost_viewer/static/app.js`:

```javascript
// ================================================================
// Amplifier Cost Viewer — app.js
// ================================================================


// ================================================================
// Section 1: State
// ================================================================

const state = {
  sessions: [],
  activeSessionId: null,
  sessionData: null,
  spans: [],
  selectedSpan: null,
  timeScale: 1,
};

const expandedNodes = new Set();


// ================================================================
// Section 2: API calls
// ================================================================

async function fetchSessions() {
  const resp = await fetch('/api/sessions');
  if (!resp.ok) throw new Error(`GET /api/sessions → ${resp.status}`);
  state.sessions = await resp.json();
}

async function fetchSession(id) {
  const resp = await fetch(`/api/sessions/${encodeURIComponent(id)}`);
  if (!resp.ok) throw new Error(`GET /api/sessions/${id} → ${resp.status}`);
  state.sessionData = await resp.json();
}

async function fetchSpans(id) {
  const resp = await fetch(`/api/sessions/${encodeURIComponent(id)}/spans`);
  if (!resp.ok) throw new Error(`GET /api/sessions/${id}/spans → ${resp.status}`);
  state.spans = await resp.json();
}


// ================================================================
// Section 3: Toolbar rendering
// ================================================================

function renderToolbar() {
  const toolbar = document.getElementById('toolbar');
  const totalCost = state.sessions.reduce(
    (sum, s) => sum + (s.total_cost_usd || 0), 0
  );

  toolbar.innerHTML = `
    <span class="toolbar-title">Cost Viewer</span>
    <select id="session-select" aria-label="Select session">
      ${state.sessions.map(s => `
        <option value="${s.session_id}"
          ${s.session_id === state.activeSessionId ? 'selected' : ''}>
          ${s.session_id.slice(-8)} — ${_formatDate(s.start_ts)} — $${(s.total_cost_usd || 0).toFixed(4)}
        </option>
      `).join('')}
    </select>
    <span class="cost-total">All sessions: <strong>$${totalCost.toFixed(4)}</strong></span>
    <button id="refresh-btn" title="Refresh session list">&#8635;</button>
  `;

  document.getElementById('session-select').addEventListener('change', e => {
    loadSession(e.target.value);
  });
  document.getElementById('refresh-btn').addEventListener('click', async () => {
    state.sessions = [];
    state.activeSessionId = null;
    await fetchSessions();
    if (state.sessions.length > 0) await loadSession(state.sessions[0].session_id);
    else renderToolbar();
  });
}

function _formatDate(isoStr) {
  if (!isoStr) return 'unknown';
  try {
    const d = new Date(isoStr);
    const diffDays = Math.floor((Date.now() - d.getTime()) / 86400000);
    if (diffDays === 0) {
      return `Today ${d.getHours().toString().padStart(2,'0')}:${d.getMinutes().toString().padStart(2,'0')}`;
    }
    if (diffDays === 1) return 'Yesterday';
    return d.toLocaleDateString();
  } catch { return isoStr; }
}


// ================================================================
// Section 4: Tree panel rendering
// Expandable/collapsible delegation tree with per-node costs.
// Clicking a row scrolls the Gantt to that session's row.
// ================================================================

function renderTreePanel() {
  const panel = document.getElementById('tree-panel');
  panel.innerHTML = '';
  if (!state.sessionData) {
    panel.innerHTML = '<div class="panel-placeholder">No session loaded.</div>';
    return;
  }
  _renderTreeNode(panel, state.sessionData, 0);
}

function _renderTreeNode(container, node, depth) {
  const hasChildren = node.children && node.children.length > 0;
  const isExpanded  = expandedNodes.has(node.session_id);

  const row = document.createElement('div');
  row.className = 'tree-row' + (node.session_id === state.activeSessionId ? ' active' : '');
  row.dataset.sessionId = node.session_id;

  const costStr = (node.total_cost_usd || 0) > 0
    ? `$${node.total_cost_usd.toFixed(4)}`
    : '';

  // Label: last-8 of session ID, plus agent name if present in data
  const shortId = node.session_id.slice(-8);
  const agentName = node.agent_name || '';
  const label = agentName ? `${shortId} · ${agentName}` : shortId;

  row.innerHTML = `
    <span style="display:inline-block;width:${depth * 12}px;flex-shrink:0"></span>
    <span class="toggle">${hasChildren ? (isExpanded ? '▾' : '▸') : '\u00a0'}</span>
    <span class="session-label" title="${node.session_id}">${label}</span>
    <span class="session-cost">${costStr}</span>
  `;

  row.addEventListener('click', () => {
    // Toggle expand/collapse
    if (hasChildren) {
      if (expandedNodes.has(node.session_id)) {
        expandedNodes.delete(node.session_id);
      } else {
        expandedNodes.add(node.session_id);
      }
      renderTreePanel();
    }
    // Scroll the Gantt to this session's row
    _scrollGanttToSession(node.session_id);
  });

  container.appendChild(row);

  // Render children if expanded
  if (hasChildren && isExpanded) {
    node.children.forEach(child => _renderTreeNode(container, child, depth + 1));
  }
}

function _scrollGanttToSession(sessionId) {
  // Find the <g data-session-id="..."> element in the Gantt SVG and scroll to it
  const ganttEl = document.querySelector(
    `#gantt-rows g[data-session-id="${sessionId}"]`
  );
  if (ganttEl) {
    ganttEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }
}


// ================================================================
// Section 5: Gantt SVG rendering  (added in Task 9)
// ================================================================

function renderGantt() { /* stub — replaced in Task 9 */ }


// ================================================================
// Section 6: Detail panel  (added in Task 10)
// ================================================================

function renderDetail() { /* stub — replaced in Task 10 */ }
function selectSpan()   { /* stub — replaced in Task 10 */ }


// ================================================================
// Section 7: Init / loadSession
// ================================================================

async function loadSession(id) {
  state.activeSessionId = id;
  await fetchSession(id);
  await fetchSpans(id);

  expandedNodes.clear();
  expandedNodes.add(id);
  if (state.sessionData && state.sessionData.children) {
    state.sessionData.children.forEach(c => expandedNodes.add(c.session_id));
  }

  const maxEndMs = Math.max(...state.spans.map(s => s.end_ms || 0), 1);
  const ganttWidth = document.getElementById('gantt-panel').clientWidth || 1000;
  state.timeScale = maxEndMs / Math.max(ganttWidth - 80, 400);

  renderToolbar();
  renderTreePanel();
  renderGantt();
}

async function init() {
  try {
    await fetchSessions();
  } catch (err) {
    console.error('Failed to fetch sessions:', err);
    document.getElementById('tree-panel').innerHTML =
      `<div class="panel-placeholder" style="color:#f85149">Error: ${err.message}</div>`;
    return;
  }
  renderToolbar();
  if (state.sessions.length > 0) {
    await loadSession(state.sessions[0].session_id);
  } else {
    document.getElementById('tree-panel').innerHTML =
      '<div class="panel-placeholder">No sessions found in ~/.amplifier/projects/</div>';
  }
}

document.addEventListener('DOMContentLoaded', init);
```

### Step 2: Start the server and verify in the browser

```bash
cd /Users/ken/workspace/ms/token-cost/viewer
uv run amplifier-cost-viewer
```

Open **http://localhost:8181**.

Verify:
- ✓ Left panel shows the delegation tree with session IDs
- ✓ Root session has an expand triangle (▸ or ▾)
- ✓ Clicking the root row toggles its children in/out
- ✓ Cost amounts appear next to each node
- ✓ Clicking a child row highlights it (`.active` class → left blue border)
- ✓ No JS errors in console

### Step 3: Stop server and commit

```bash
cd /Users/ken/workspace/ms/token-cost
git add viewer/amplifier_app_cost_viewer/static/app.js
git commit -m "feat(viewer): app.js Section 4 — expandable delegation tree panel"
```

---

## Task 9: Add Section 5 — Gantt SVG

**Files:**
- Modify: `viewer/amplifier_app_cost_viewer/static/app.js`

### Step 1: Rewrite `app.js` with the full Gantt section

Replace the entire contents of `viewer/amplifier_app_cost_viewer/static/app.js`:

```javascript
// ================================================================
// Amplifier Cost Viewer — app.js
// ================================================================


// ================================================================
// Section 1: State
// ================================================================

const state = {
  sessions: [],
  activeSessionId: null,
  sessionData: null,
  spans: [],
  selectedSpan: null,
  timeScale: 1,
};

const expandedNodes = new Set();


// ================================================================
// Section 2: API calls
// ================================================================

async function fetchSessions() {
  const resp = await fetch('/api/sessions');
  if (!resp.ok) throw new Error(`GET /api/sessions → ${resp.status}`);
  state.sessions = await resp.json();
}

async function fetchSession(id) {
  const resp = await fetch(`/api/sessions/${encodeURIComponent(id)}`);
  if (!resp.ok) throw new Error(`GET /api/sessions/${id} → ${resp.status}`);
  state.sessionData = await resp.json();
}

async function fetchSpans(id) {
  const resp = await fetch(`/api/sessions/${encodeURIComponent(id)}/spans`);
  if (!resp.ok) throw new Error(`GET /api/sessions/${id}/spans → ${resp.status}`);
  state.spans = await resp.json();
}


// ================================================================
// Section 3: Toolbar rendering
// ================================================================

function renderToolbar() {
  const toolbar = document.getElementById('toolbar');
  const totalCost = state.sessions.reduce(
    (sum, s) => sum + (s.total_cost_usd || 0), 0
  );

  toolbar.innerHTML = `
    <span class="toolbar-title">Cost Viewer</span>
    <select id="session-select" aria-label="Select session">
      ${state.sessions.map(s => `
        <option value="${s.session_id}"
          ${s.session_id === state.activeSessionId ? 'selected' : ''}>
          ${s.session_id.slice(-8)} — ${_formatDate(s.start_ts)} — $${(s.total_cost_usd || 0).toFixed(4)}
        </option>
      `).join('')}
    </select>
    <span class="cost-total">All sessions: <strong>$${totalCost.toFixed(4)}</strong></span>
    <button id="refresh-btn" title="Refresh session list">&#8635;</button>
  `;

  document.getElementById('session-select').addEventListener('change', e => {
    loadSession(e.target.value);
  });
  document.getElementById('refresh-btn').addEventListener('click', async () => {
    state.sessions = [];
    state.activeSessionId = null;
    await fetchSessions();
    if (state.sessions.length > 0) await loadSession(state.sessions[0].session_id);
    else renderToolbar();
  });
}

function _formatDate(isoStr) {
  if (!isoStr) return 'unknown';
  try {
    const d = new Date(isoStr);
    const diffDays = Math.floor((Date.now() - d.getTime()) / 86400000);
    if (diffDays === 0) {
      return `Today ${d.getHours().toString().padStart(2,'0')}:${d.getMinutes().toString().padStart(2,'0')}`;
    }
    if (diffDays === 1) return 'Yesterday';
    return d.toLocaleDateString();
  } catch { return isoStr; }
}


// ================================================================
// Section 4: Tree panel rendering
// ================================================================

function renderTreePanel() {
  const panel = document.getElementById('tree-panel');
  panel.innerHTML = '';
  if (!state.sessionData) {
    panel.innerHTML = '<div class="panel-placeholder">No session loaded.</div>';
    return;
  }
  _renderTreeNode(panel, state.sessionData, 0);
}

function _renderTreeNode(container, node, depth) {
  const hasChildren = node.children && node.children.length > 0;
  const isExpanded  = expandedNodes.has(node.session_id);

  const row = document.createElement('div');
  row.className = 'tree-row' + (node.session_id === state.activeSessionId ? ' active' : '');
  row.dataset.sessionId = node.session_id;

  const costStr = (node.total_cost_usd || 0) > 0
    ? `$${node.total_cost_usd.toFixed(4)}` : '';
  const shortId   = node.session_id.slice(-8);
  const agentName = node.agent_name || '';
  const label     = agentName ? `${shortId} · ${agentName}` : shortId;

  row.innerHTML = `
    <span style="display:inline-block;width:${depth * 12}px;flex-shrink:0"></span>
    <span class="toggle">${hasChildren ? (isExpanded ? '▾' : '▸') : '\u00a0'}</span>
    <span class="session-label" title="${node.session_id}">${label}</span>
    <span class="session-cost">${costStr}</span>
  `;

  row.addEventListener('click', () => {
    if (hasChildren) {
      if (expandedNodes.has(node.session_id)) expandedNodes.delete(node.session_id);
      else expandedNodes.add(node.session_id);
      renderTreePanel();
    }
    _scrollGanttToSession(node.session_id);
  });

  container.appendChild(row);
  if (hasChildren && isExpanded) {
    node.children.forEach(child => _renderTreeNode(container, child, depth + 1));
  }
}

function _scrollGanttToSession(sessionId) {
  const el = document.querySelector(`#gantt-rows g[data-session-id="${sessionId}"]`);
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}


// ================================================================
// Section 5: Gantt SVG rendering
// One SVG element spans the whole Gantt area.
// One <g> row per session (DFS order from the tree).
// One <rect> per span, x = start_ms / timeScale.
// ================================================================

const ROW_HEIGHT  = 32;   // px — height of each session lane
const SPAN_H      = 20;   // px — height of a span bar
const SPAN_Y_OFF  = 6;    // px — vertical centering within row
const MIN_BAR_W   = 2;    // px — minimum visible bar width

function renderGantt() {
  const ganttRows = document.getElementById('gantt-rows');
  const ruler     = document.getElementById('time-ruler');
  ganttRows.innerHTML = '';
  ruler.innerHTML = '';

  if (!state.spans || state.spans.length === 0) {
    ganttRows.innerHTML = '<div class="panel-placeholder">No spans to display.</div>';
    return;
  }

  const maxEndMs     = Math.max(...state.spans.map(s => s.end_ms || 0), 1);
  const panelWidth   = document.getElementById('gantt-panel').clientWidth || 1000;
  const svgWidth     = Math.max(panelWidth - 4, maxEndMs / state.timeScale + 80);

  // Build the ordered list of sessions via DFS (matches tree panel order)
  const sessionOrder = _flattenSessionOrder(state.sessionData, []);
  const svgHeight    = sessionOrder.length * ROW_HEIGHT;

  // ---- Main Gantt SVG ----
  const svg = _svgEl('svg', { width: svgWidth, height: svgHeight });
  svg.style.display = 'block';

  // Alternating row backgrounds
  sessionOrder.forEach((sid, i) => {
    const bg = _svgEl('rect', {
      x: 0, y: i * ROW_HEIGHT,
      width: svgWidth, height: ROW_HEIGHT,
      fill: i % 2 === 0 ? '#161b22' : '#0d1117',
    });
    svg.appendChild(bg);
  });

  // Group spans by session
  const bySession = {};
  state.spans.forEach(span => {
    if (!bySession[span.session_id]) bySession[span.session_id] = [];
    bySession[span.session_id].push(span);
  });

  // Render one <g> per session row
  sessionOrder.forEach((sid, rowIdx) => {
    const g = _svgEl('g', { 'data-session-id': sid });
    g.setAttribute('transform', `translate(0,${rowIdx * ROW_HEIGHT})`);

    (bySession[sid] || []).forEach(span => {
      const x = span.start_ms / state.timeScale;
      const w = Math.max((span.end_ms - span.start_ms) / state.timeScale, MIN_BAR_W);

      const rect = _svgEl('rect', {
        x, y: SPAN_Y_OFF,
        width: w, height: SPAN_H,
        rx: 3,
        fill: span.color || '#64748B',
        opacity: '0.85',
      });
      rect.style.cursor = 'pointer';

      // SVG tooltip
      const title = document.createElementNS('http://www.w3.org/2000/svg', 'title');
      title.textContent = _spanTooltip(span);
      rect.appendChild(title);

      rect.addEventListener('click', e => { e.stopPropagation(); selectSpan(span); });
      rect.addEventListener('mouseenter', () => rect.setAttribute('opacity', '1'));
      rect.addEventListener('mouseleave', () => rect.setAttribute('opacity', '0.85'));

      g.appendChild(rect);
    });

    svg.appendChild(g);
  });

  // Background SVG click → orchestrator gap detail
  svg.addEventListener('click', e => {
    if (e.target.tagName !== 'rect' || e.target.getAttribute('opacity') === null) {
      const svgRect = svg.getBoundingClientRect();
      const clickMs = (e.clientX - svgRect.left) * state.timeScale;
      _showGap(clickMs);
    }
  });

  ganttRows.appendChild(svg);

  // ---- Time ruler ----
  _renderRuler(ruler, maxEndMs, svgWidth);
}

function _flattenSessionOrder(node, result) {
  if (!node) return result;
  result.push(node.session_id);
  if (node.children) node.children.forEach(c => _flattenSessionOrder(c, result));
  return result;
}

function _renderRuler(container, maxEndMs, svgWidth) {
  const svg = _svgEl('svg', { width: svgWidth, height: 28 });
  svg.style.display = 'block';

  // Pick a sensible tick interval based on total duration
  const totalS = maxEndMs / 1000;
  const tickMs =
    totalS <= 30   ? 5000  :   // 5s ticks for short sessions
    totalS <= 300  ? 30000 :   // 30s ticks up to 5 min
    totalS <= 1800 ? 60000 :   // 1m ticks up to 30 min
                     300000;   // 5m ticks for long sessions

  for (let t = 0; t <= maxEndMs; t += tickMs) {
    const x = t / state.timeScale;

    const line = _svgEl('line', {
      x1: x, x2: x, y1: 14, y2: 28,
      stroke: '#30363d', 'stroke-width': 1,
    });
    svg.appendChild(line);

    const text = _svgEl('text', {
      x: x + 3, y: 11,
      fill: '#8b949e',
      'font-size': 10,
      'font-family': 'monospace',
    });
    text.textContent = _formatMs(t);
    svg.appendChild(text);
  }

  container.appendChild(svg);
}

// Helper: create an SVG element with multiple attributes at once
function _svgEl(tag, attrs) {
  const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const [k, v] of Object.entries(attrs || {})) el.setAttribute(k, v);
  return el;
}

// Human-readable millisecond duration (e.g. "1.4s", "2m05s")
function _formatMs(ms) {
  if (ms < 1000)  return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  const m = Math.floor(ms / 60000);
  const s = Math.floor((ms % 60000) / 1000);
  return `${m}m${s.toString().padStart(2, '0')}s`;
}

function _spanTooltip(span) {
  if (span.type === 'llm') {
    return [
      `${span.provider}/${span.model}`,
      `${_formatMs(span.start_ms)} → ${_formatMs(span.end_ms)}`,
      `in:${span.input_tokens}  out:${span.output_tokens}  $${(span.cost_usd || 0).toFixed(6)}`,
    ].join('\n');
  }
  if (span.type === 'tool') {
    return [
      `${span.tool_name}  ${span.success ? '✓' : '✗'}`,
      `${_formatMs(span.start_ms)} → ${_formatMs(span.end_ms)}`,
    ].join('\n');
  }
  return `thinking\n${_formatMs(span.start_ms)} → ${_formatMs(span.end_ms)}`;
}

function _showGap(clickMs) {
  // Find the span that ends just before this click and the one that starts after
  const before = [...state.spans]
    .filter(s => s.end_ms <= clickMs)
    .sort((a, b) => b.end_ms - a.end_ms)[0];
  const after = [...state.spans]
    .filter(s => s.start_ms >= clickMs)
    .sort((a, b) => a.start_ms - b.start_ms)[0];

  if (!before || !after || after.start_ms <= before.end_ms) return;

  renderDetail({
    type: 'gap',
    start_ms: before.end_ms,
    end_ms: after.start_ms,
    before_label: before.type === 'tool' ? `${before.type}(${before.tool_name})` : before.type,
    after_label:  after.type  === 'tool' ? `${after.type}(${after.tool_name})`   : after.type,
  });
}


// ================================================================
// Section 6: Detail panel  (added in Task 10)
// ================================================================

function renderDetail() { /* stub — replaced in Task 10 */ }
function selectSpan(span) { renderDetail(span); }


// ================================================================
// Section 7: Init / loadSession
// ================================================================

async function loadSession(id) {
  state.activeSessionId = id;
  await fetchSession(id);
  await fetchSpans(id);

  expandedNodes.clear();
  expandedNodes.add(id);
  if (state.sessionData && state.sessionData.children) {
    state.sessionData.children.forEach(c => expandedNodes.add(c.session_id));
  }

  const maxEndMs  = Math.max(...state.spans.map(s => s.end_ms || 0), 1);
  const ganttWidth = document.getElementById('gantt-panel').clientWidth || 1000;
  state.timeScale  = maxEndMs / Math.max(ganttWidth - 80, 400);

  renderToolbar();
  renderTreePanel();
  renderGantt();
}

async function init() {
  try {
    await fetchSessions();
  } catch (err) {
    console.error('Failed to fetch sessions:', err);
    document.getElementById('tree-panel').innerHTML =
      `<div class="panel-placeholder" style="color:#f85149">Error: ${err.message}</div>`;
    return;
  }
  renderToolbar();
  if (state.sessions.length > 0) {
    await loadSession(state.sessions[0].session_id);
  } else {
    document.getElementById('tree-panel').innerHTML =
      '<div class="panel-placeholder">No sessions found in ~/.amplifier/projects/</div>';
  }
}

document.addEventListener('DOMContentLoaded', init);
```

### Step 2: Start the server and verify in the browser

```bash
cd /Users/ken/workspace/ms/token-cost/viewer
uv run amplifier-cost-viewer
```

Open **http://localhost:8181**.

Verify:
- ✓ Colored span bars appear in the Gantt area (purple/teal/blue rectangles)
- ✓ LLM spans have provider-matching colors (Anthropic = purple family, OpenAI = teal, Google = blue)
- ✓ Tool spans are slate gray (`#64748B`)
- ✓ Thinking spans are indigo (`#6366F1`) if any exist in your sessions
- ✓ Time ruler at the top shows tick labels (e.g. `0ms`, `5.0s`, `10.0s` …)
- ✓ Spans are positioned horizontally at the correct time offsets
- ✓ Hovering a span makes it brighter
- ✓ SVG tooltips appear on hover (span type, time range, cost)
- ✓ No JS errors in console

### Step 3: Stop server and commit

```bash
cd /Users/ken/workspace/ms/token-cost
git add viewer/amplifier_app_cost_viewer/static/app.js
git commit -m "feat(viewer): app.js Section 5 — SVG Gantt with time ruler and colored span bars"
```

---

## Task 10: Add Section 6 — Detail Panel

**Files:**
- Modify: `viewer/amplifier_app_cost_viewer/static/app.js`

### Step 1: Rewrite `app.js` with the full detail panel section

Replace the entire contents of `viewer/amplifier_app_cost_viewer/static/app.js`:

```javascript
// ================================================================
// Amplifier Cost Viewer — app.js
// ================================================================


// ================================================================
// Section 1: State
// ================================================================

const state = {
  sessions: [],
  activeSessionId: null,
  sessionData: null,
  spans: [],
  selectedSpan: null,
  timeScale: 1,
};

const expandedNodes = new Set();


// ================================================================
// Section 2: API calls
// ================================================================

async function fetchSessions() {
  const resp = await fetch('/api/sessions');
  if (!resp.ok) throw new Error(`GET /api/sessions → ${resp.status}`);
  state.sessions = await resp.json();
}

async function fetchSession(id) {
  const resp = await fetch(`/api/sessions/${encodeURIComponent(id)}`);
  if (!resp.ok) throw new Error(`GET /api/sessions/${id} → ${resp.status}`);
  state.sessionData = await resp.json();
}

async function fetchSpans(id) {
  const resp = await fetch(`/api/sessions/${encodeURIComponent(id)}/spans`);
  if (!resp.ok) throw new Error(`GET /api/sessions/${id}/spans → ${resp.status}`);
  state.spans = await resp.json();
}


// ================================================================
// Section 3: Toolbar rendering
// ================================================================

function renderToolbar() {
  const toolbar = document.getElementById('toolbar');
  const totalCost = state.sessions.reduce(
    (sum, s) => sum + (s.total_cost_usd || 0), 0
  );

  toolbar.innerHTML = `
    <span class="toolbar-title">Cost Viewer</span>
    <select id="session-select" aria-label="Select session">
      ${state.sessions.map(s => `
        <option value="${s.session_id}"
          ${s.session_id === state.activeSessionId ? 'selected' : ''}>
          ${s.session_id.slice(-8)} — ${_formatDate(s.start_ts)} — $${(s.total_cost_usd || 0).toFixed(4)}
        </option>
      `).join('')}
    </select>
    <span class="cost-total">All sessions: <strong>$${totalCost.toFixed(4)}</strong></span>
    <button id="refresh-btn" title="Refresh">&#8635;</button>
  `;

  document.getElementById('session-select').addEventListener('change', e => {
    loadSession(e.target.value);
  });
  document.getElementById('refresh-btn').addEventListener('click', async () => {
    state.sessions = [];
    state.activeSessionId = null;
    await fetchSessions();
    if (state.sessions.length > 0) await loadSession(state.sessions[0].session_id);
    else renderToolbar();
  });
}

function _formatDate(isoStr) {
  if (!isoStr) return 'unknown';
  try {
    const d = new Date(isoStr);
    const diffDays = Math.floor((Date.now() - d.getTime()) / 86400000);
    if (diffDays === 0) {
      return `Today ${d.getHours().toString().padStart(2,'0')}:${d.getMinutes().toString().padStart(2,'0')}`;
    }
    if (diffDays === 1) return 'Yesterday';
    return d.toLocaleDateString();
  } catch { return isoStr; }
}


// ================================================================
// Section 4: Tree panel rendering
// ================================================================

function renderTreePanel() {
  const panel = document.getElementById('tree-panel');
  panel.innerHTML = '';
  if (!state.sessionData) {
    panel.innerHTML = '<div class="panel-placeholder">No session loaded.</div>';
    return;
  }
  _renderTreeNode(panel, state.sessionData, 0);
}

function _renderTreeNode(container, node, depth) {
  const hasChildren = node.children && node.children.length > 0;
  const isExpanded  = expandedNodes.has(node.session_id);

  const row = document.createElement('div');
  row.className = 'tree-row' + (node.session_id === state.activeSessionId ? ' active' : '');
  row.dataset.sessionId = node.session_id;

  const costStr   = (node.total_cost_usd || 0) > 0 ? `$${node.total_cost_usd.toFixed(4)}` : '';
  const shortId   = node.session_id.slice(-8);
  const agentName = node.agent_name || '';
  const label     = agentName ? `${shortId} · ${agentName}` : shortId;

  row.innerHTML = `
    <span style="display:inline-block;width:${depth * 12}px;flex-shrink:0"></span>
    <span class="toggle">${hasChildren ? (isExpanded ? '▾' : '▸') : '\u00a0'}</span>
    <span class="session-label" title="${node.session_id}">${label}</span>
    <span class="session-cost">${costStr}</span>
  `;

  row.addEventListener('click', () => {
    if (hasChildren) {
      if (expandedNodes.has(node.session_id)) expandedNodes.delete(node.session_id);
      else expandedNodes.add(node.session_id);
      renderTreePanel();
    }
    _scrollGanttToSession(node.session_id);
  });

  container.appendChild(row);
  if (hasChildren && isExpanded) {
    node.children.forEach(c => _renderTreeNode(container, c, depth + 1));
  }
}

function _scrollGanttToSession(sessionId) {
  const el = document.querySelector(`#gantt-rows g[data-session-id="${sessionId}"]`);
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}


// ================================================================
// Section 5: Gantt SVG rendering
// ================================================================

const ROW_HEIGHT = 32;
const SPAN_H     = 20;
const SPAN_Y_OFF = 6;
const MIN_BAR_W  = 2;

function renderGantt() {
  const ganttRows = document.getElementById('gantt-rows');
  const ruler     = document.getElementById('time-ruler');
  ganttRows.innerHTML = '';
  ruler.innerHTML = '';

  if (!state.spans || state.spans.length === 0) {
    ganttRows.innerHTML = '<div class="panel-placeholder">No spans to display.</div>';
    return;
  }

  const maxEndMs   = Math.max(...state.spans.map(s => s.end_ms || 0), 1);
  const panelWidth = document.getElementById('gantt-panel').clientWidth || 1000;
  const svgWidth   = Math.max(panelWidth - 4, maxEndMs / state.timeScale + 80);

  const sessionOrder = _flattenSessionOrder(state.sessionData, []);
  const svgHeight    = sessionOrder.length * ROW_HEIGHT;

  const svg = _svgEl('svg', { width: svgWidth, height: svgHeight });
  svg.style.display = 'block';

  sessionOrder.forEach((sid, i) => {
    svg.appendChild(_svgEl('rect', {
      x: 0, y: i * ROW_HEIGHT,
      width: svgWidth, height: ROW_HEIGHT,
      fill: i % 2 === 0 ? '#161b22' : '#0d1117',
    }));
  });

  const bySession = {};
  state.spans.forEach(span => {
    if (!bySession[span.session_id]) bySession[span.session_id] = [];
    bySession[span.session_id].push(span);
  });

  sessionOrder.forEach((sid, rowIdx) => {
    const g = _svgEl('g', { 'data-session-id': sid });
    g.setAttribute('transform', `translate(0,${rowIdx * ROW_HEIGHT})`);

    (bySession[sid] || []).forEach(span => {
      const x = span.start_ms / state.timeScale;
      const w = Math.max((span.end_ms - span.start_ms) / state.timeScale, MIN_BAR_W);

      const rect = _svgEl('rect', {
        x, y: SPAN_Y_OFF, width: w, height: SPAN_H,
        rx: 3, fill: span.color || '#64748B', opacity: '0.85',
      });
      rect.style.cursor = 'pointer';

      const title = document.createElementNS('http://www.w3.org/2000/svg', 'title');
      title.textContent = _spanTooltip(span);
      rect.appendChild(title);

      rect.addEventListener('click', e => { e.stopPropagation(); selectSpan(span); });
      rect.addEventListener('mouseenter', () => rect.setAttribute('opacity', '1'));
      rect.addEventListener('mouseleave', () => rect.setAttribute('opacity', '0.85'));

      g.appendChild(rect);
    });
    svg.appendChild(g);
  });

  svg.addEventListener('click', e => {
    if (e.target.tagName !== 'rect') {
      const svgRect = svg.getBoundingClientRect();
      _showGap((e.clientX - svgRect.left) * state.timeScale);
    }
  });

  ganttRows.appendChild(svg);
  _renderRuler(ruler, maxEndMs, svgWidth);
}

function _flattenSessionOrder(node, result) {
  if (!node) return result;
  result.push(node.session_id);
  if (node.children) node.children.forEach(c => _flattenSessionOrder(c, result));
  return result;
}

function _renderRuler(container, maxEndMs, svgWidth) {
  const svg    = _svgEl('svg', { width: svgWidth, height: 28 });
  svg.style.display = 'block';
  const totalS = maxEndMs / 1000;
  const tickMs = totalS <= 30 ? 5000 : totalS <= 300 ? 30000 : totalS <= 1800 ? 60000 : 300000;

  for (let t = 0; t <= maxEndMs; t += tickMs) {
    const x = t / state.timeScale;
    svg.appendChild(_svgEl('line', { x1:x, x2:x, y1:14, y2:28, stroke:'#30363d', 'stroke-width':1 }));
    const text = _svgEl('text', { x: x+3, y:11, fill:'#8b949e', 'font-size':10, 'font-family':'monospace' });
    text.textContent = _formatMs(t);
    svg.appendChild(text);
  }
  container.appendChild(svg);
}

function _svgEl(tag, attrs) {
  const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const [k, v] of Object.entries(attrs || {})) el.setAttribute(k, v);
  return el;
}

function _formatMs(ms) {
  if (ms < 1000)  return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  const m = Math.floor(ms / 60000);
  const s = Math.floor((ms % 60000) / 1000);
  return `${m}m${s.toString().padStart(2,'0')}s`;
}

function _spanTooltip(span) {
  if (span.type === 'llm') {
    return `${span.provider}/${span.model}\n${_formatMs(span.start_ms)} → ${_formatMs(span.end_ms)}\nin:${span.input_tokens}  out:${span.output_tokens}  $${(span.cost_usd||0).toFixed(6)}`;
  }
  if (span.type === 'tool') {
    return `${span.tool_name}  ${span.success ? '✓' : '✗'}\n${_formatMs(span.start_ms)} → ${_formatMs(span.end_ms)}`;
  }
  return `thinking\n${_formatMs(span.start_ms)} → ${_formatMs(span.end_ms)}`;
}

function _showGap(clickMs) {
  const before = [...state.spans].filter(s => s.end_ms <= clickMs).sort((a,b) => b.end_ms - a.end_ms)[0];
  const after  = [...state.spans].filter(s => s.start_ms >= clickMs).sort((a,b) => a.start_ms - b.start_ms)[0];
  if (!before || !after || after.start_ms <= before.end_ms) return;
  renderDetail({
    type: 'gap',
    start_ms: before.end_ms,
    end_ms:   after.start_ms,
    before_label: before.type === 'tool' ? `tool(${before.tool_name})` : before.type,
    after_label:  after.type  === 'tool' ? `tool(${after.tool_name})`  : after.type,
  });
}


// ================================================================
// Section 6: Detail panel
// Slides up from the bottom when a span is clicked.
// Three render variants: LLM, tool, gap.  "show more" for long I/O.
// ================================================================

const IO_TRUNCATE = 500;  // chars before "show more" appears

function selectSpan(span) {
  state.selectedSpan = span;
  renderDetail(span);
}

function renderDetail(span) {
  const panel = document.getElementById('detail-panel');
  panel.classList.remove('hidden');

  if      (span.type === 'llm')     _detailLlm(panel, span);
  else if (span.type === 'tool')    _detailTool(panel, span);
  else if (span.type === 'thinking') _detailThinking(panel, span);
  else if (span.type === 'gap')     _detailGap(panel, span);

  // Wire up "show more" buttons
  panel.querySelectorAll('.detail-show-more').forEach(btn => {
    btn.addEventListener('click', () => {
      const content = btn.previousElementSibling;
      content.textContent = content.dataset.fullText;
      btn.remove();
    });
  });

  // Close button
  const closeBtn = panel.querySelector('.detail-close');
  if (closeBtn) closeBtn.addEventListener('click', _closeDetail);
}

function _detailLlm(panel, span) {
  const dur  = span.end_ms - span.start_ms;
  const cost = (span.cost_usd || 0).toFixed(6);
  const cr   = span.cache_read_tokens  > 0 ? `  cache_read: <strong>${span.cache_read_tokens.toLocaleString()}</strong>` : '';
  const cw   = span.cache_write_tokens > 0 ? `  cache_write: <strong>${span.cache_write_tokens.toLocaleString()}</strong>` : '';

  panel.innerHTML = `
    <div class="detail-header">
      <span class="detail-title">${_esc(span.provider || '?')} / ${_esc(span.model || '?')}</span>
      <span class="detail-timing">+${_formatMs(span.start_ms)} → +${_formatMs(span.end_ms)}  (${_formatMs(dur)})</span>
    </div>
    <div class="detail-tokens">
      in: <strong>${(span.input_tokens||0).toLocaleString()}</strong>
      &nbsp; out: <strong>${(span.output_tokens||0).toLocaleString()}</strong>
      ${cr}${cw}
      &nbsp;&nbsp; <strong>$${cost}</strong>
    </div>
    ${_ioBlock('INPUT',  span.input)}
    ${_ioBlock('OUTPUT', span.output)}
    <button class="detail-close">✕</button>
  `;
}

function _detailTool(panel, span) {
  const dur = span.end_ms - span.start_ms;
  const ok  = span.success
    ? '<span class="success-icon">✓</span>'
    : '<span class="failure-icon">✗</span>';

  panel.innerHTML = `
    <div class="detail-header">
      <span class="detail-title">${_esc(span.tool_name || 'tool')} ${ok}</span>
      <span class="detail-timing">+${_formatMs(span.start_ms)} → +${_formatMs(span.end_ms)}  (${_formatMs(dur)})</span>
    </div>
    ${_ioBlock('INPUT',  span.input)}
    ${_ioBlock('OUTPUT', span.output)}
    <button class="detail-close">✕</button>
  `;
}

function _detailThinking(panel, span) {
  const dur = span.end_ms - span.start_ms;
  panel.innerHTML = `
    <div class="detail-header">
      <span class="detail-title" style="color:#6366F1">thinking</span>
      <span class="detail-timing">+${_formatMs(span.start_ms)} → +${_formatMs(span.end_ms)}  (${_formatMs(dur)})</span>
    </div>
    <button class="detail-close">✕</button>
  `;
}

function _detailGap(panel, span) {
  const dur = span.end_ms - span.start_ms;
  panel.innerHTML = `
    <div class="detail-header">
      <span class="detail-title" style="color:#8b949e">orchestrator overhead</span>
      <span class="detail-timing">+${_formatMs(span.start_ms)} → +${_formatMs(span.end_ms)}  (${_formatMs(dur)})</span>
    </div>
    <div class="detail-tokens" style="color:var(--text-muted)">
      between ${_esc(span.before_label)} and ${_esc(span.after_label)}
    </div>
    <button class="detail-close">✕</button>
  `;
}

function _ioBlock(label, value) {
  if (value === null || value === undefined) return '';
  const text      = typeof value === 'string' ? value : JSON.stringify(value, null, 2);
  const truncated = text.length > IO_TRUNCATE;
  const display   = truncated ? text.slice(0, IO_TRUNCATE) + '…' : text;
  const moreBtn   = truncated
    ? `<span class="detail-show-more">show more (${text.length.toLocaleString()} chars)</span>`
    : '';
  return `
    <div class="detail-io">
      <div class="detail-io-label">${label}</div>
      <div class="detail-io-content" data-full-text="${_esc(text)}">${_esc(display)}</div>
      ${moreBtn}
    </div>
  `;
}

function _closeDetail() {
  document.getElementById('detail-panel').classList.add('hidden');
  state.selectedSpan = null;
}

function _esc(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}


// ================================================================
// Section 7: Init / loadSession
// ================================================================

async function loadSession(id) {
  state.activeSessionId = id;
  await fetchSession(id);
  await fetchSpans(id);

  expandedNodes.clear();
  expandedNodes.add(id);
  if (state.sessionData && state.sessionData.children) {
    state.sessionData.children.forEach(c => expandedNodes.add(c.session_id));
  }

  const maxEndMs   = Math.max(...state.spans.map(s => s.end_ms || 0), 1);
  const ganttWidth = document.getElementById('gantt-panel').clientWidth || 1000;
  state.timeScale  = maxEndMs / Math.max(ganttWidth - 80, 400);

  renderToolbar();
  renderTreePanel();
  renderGantt();
}

async function init() {
  try {
    await fetchSessions();
  } catch (err) {
    console.error('Failed to fetch sessions:', err);
    document.getElementById('tree-panel').innerHTML =
      `<div class="panel-placeholder" style="color:#f85149">Error: ${err.message}</div>`;
    return;
  }
  renderToolbar();
  if (state.sessions.length > 0) {
    await loadSession(state.sessions[0].session_id);
  } else {
    document.getElementById('tree-panel').innerHTML =
      '<div class="panel-placeholder">No sessions found in ~/.amplifier/projects/</div>';
  }
}

document.addEventListener('DOMContentLoaded', init);
```

### Step 2: Start the server and verify in the browser

```bash
cd /Users/ken/workspace/ms/token-cost/viewer
uv run amplifier-cost-viewer
```

Open **http://localhost:8181**.

Verify:
- ✓ Clicking any span bar opens the detail panel at the bottom
- ✓ LLM span shows: provider/model, time offsets, token counts, cost in USD
- ✓ Tool span shows: tool name, success/failure indicator, time offsets
- ✓ Tool span with `log_io=true` data shows INPUT and OUTPUT sections
- ✓ Long INPUT/OUTPUT text shows "show more (N chars)" link that expands inline
- ✓ Clicking a dark gap between spans shows "orchestrator overhead" with the gap duration
- ✓ The ✕ close button hides the detail panel
- ✓ No JS errors in console

### Step 3: Stop server and commit

```bash
cd /Users/ken/workspace/ms/token-cost
git add viewer/amplifier_app_cost_viewer/static/app.js
git commit -m "feat(viewer): app.js Section 6 — detail panel with LLM, tool, gap, and thinking variants"
```

---

## Task 11: End-to-End Browser Test + Final Commit

### Step 1: Load a real session from `~/.amplifier`

```bash
cd /Users/ken/workspace/ms/token-cost/viewer
uv run amplifier-cost-viewer
```

Open **http://localhost:8181**.

Work through this checklist with a real session from `~/.amplifier/projects/-Users-ken/sessions/`:

| Checkpoint | How to verify |
|---|---|
| Session list loads | Dropdown shows real session IDs with costs and dates |
| Delegation tree renders | Left panel shows root + child session rows indented |
| Expand/collapse works | Click triangle on root row — children show and hide |
| Gantt shows colored bars | LLM bars in purple/teal/blue, tools in gray |
| Time ruler is sensible | Ticks at 5s/30s/1m depending on session length |
| Clicking LLM span shows detail | Provider, model, token counts, dollar cost all present |
| Clicking tool span shows detail | Tool name, ✓/✗, timing |
| Clicking dark gap shows overhead | "orchestrator overhead" with gap duration |
| "show more" expands long I/O | Click link, full text appears |
| Refresh button works | Click ↺ — session list reloads without error |
| Switch session from dropdown | Different session loads, tree + Gantt update |

### Step 2: Run all viewer tests

```bash
cd /Users/ken/workspace/ms/token-cost/viewer
python -m pytest tests/ -v
```

Expected:
```
tests/test_pricing.py  — 18 passed
tests/test_reader.py   — 35 passed
tests/test_server.py   — 22 passed

75 passed in X.XXs
```

All 75 must pass. If any fail, fix before committing.

### Step 3: Final commit

```bash
cd /Users/ken/workspace/ms/token-cost
git add -A
git commit -m "feat: complete amplifier-cost-viewer Phase 2 frontend

- server.py: FastAPI app with 4 routes, in-memory session cache
- scripts/update_pricing.py: fetch LiteLLM catalog, rewrite pricing.py
- static/index.html: three-pane shell
- static/style.css: dark theme (GitHub palette), responsive layout
- static/app.js: session tree, SVG Gantt, detail panel — vanilla JS
- viewer/tests/test_server.py: 22 API integration tests

Phase 2 complete. Launch with: uvx --from ./viewer amplifier-cost-viewer"
```

---

## Phase 2 complete

At this point the full viewer is implemented:

| File | What it does |
|---|---|
| `viewer/amplifier_app_cost_viewer/server.py` | FastAPI app: `GET /api/sessions`, `GET /api/sessions/{id}`, `GET /api/sessions/{id}/spans`, static file serving. In-memory cache per root session. |
| `viewer/amplifier_app_cost_viewer/static/index.html` | Three-pane HTML shell: toolbar, tree panel, Gantt panel, detail footer. |
| `viewer/amplifier_app_cost_viewer/static/style.css` | Dark theme (GitHub palette), CSS custom properties, full three-pane layout. |
| `viewer/amplifier_app_cost_viewer/static/app.js` | Session tree, SVG Gantt renderer, time ruler, detail panel. All 7 sections. |
| `scripts/update_pricing.py` | Fetches LiteLLM JSON, rewrites `STATIC_PRICING` in `pricing.py`, caches to `~/.amplifier/pricing-cache.json`. |
| `viewer/tests/test_server.py` | 22 API integration tests covering all 4 routes. |

**Launch command:**
```bash
uvx --from ./viewer amplifier-cost-viewer
# → http://127.0.0.1:8181
```
