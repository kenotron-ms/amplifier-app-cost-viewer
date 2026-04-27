"""Tests for live session indicator (Fix 1) and auto-refresh cache (Fix 2).

RED phase: all tests fail before implementation.
"""

from __future__ import annotations

from pathlib import Path

import pytest

STATIC = Path(__file__).parent.parent / "amplifier_app_cost_viewer" / "static"
APP_JS = STATIC / "app.js"
SERVER_PY = Path(__file__).parent.parent / "amplifier_app_cost_viewer" / "server.py"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def app_js_code() -> str:
    return APP_JS.read_text()


@pytest.fixture
def server_module_code() -> str:
    return SERVER_PY.read_text()


# ---------------------------------------------------------------------------
# Fix 1: Live session indicator
# ---------------------------------------------------------------------------


def test_live_dot_indicator_in_toolbar(app_js_code: str) -> None:
    """Toolbar must show live indicator for sessions without end_ts."""
    assert "end_ts" in app_js_code, "app.js must reference s.end_ts to detect live sessions"
    assert "isLive" in app_js_code, "app.js must compute isLive from end_ts"


def test_live_dot_indicator_symbol_in_toolbar(app_js_code: str) -> None:
    """Toolbar must render ● for live sessions."""
    assert "●" in app_js_code, "app.js must include ● live indicator character"


def test_live_dot_span_in_body(app_js_code: str) -> None:
    """AcvBody label must include live-dot span for live sessions."""
    assert "live-dot" in app_js_code, (
        "app.js must define a 'live-dot' CSS class and render a <span class='live-dot'> "
        "on root label rows for sessions with no end_ts"
    )


def test_live_dot_css_defined(app_js_code: str) -> None:
    """app.js must define .live-dot CSS with green color."""
    assert ".live-dot" in app_js_code, "app.js must define .live-dot CSS rule"
    assert "#3fb950" in app_js_code, "live-dot must use #3fb950 green color"


# ---------------------------------------------------------------------------
# Fix 2: Auto-refresh cache every 60 seconds for live sessions
# ---------------------------------------------------------------------------


def test_auto_refresh_startup_event(server_module_code: str) -> None:
    """server.py must have auto-refresh background task for live sessions."""
    assert (
        "_auto_refresh_live_sessions" in server_module_code
        or "refresh_loop" in server_module_code
    ), "server.py must define _auto_refresh_live_sessions startup event or _refresh_loop"


def test_iter_nodes_helper(server_module_code: str) -> None:
    """server.py must have _iter_nodes helper."""
    assert "_iter_nodes" in server_module_code, (
        "server.py must define _iter_nodes(root) helper that yields all nodes in the tree"
    )


def test_auto_refresh_checks_live_sessions(server_module_code: str) -> None:
    """Auto-refresh must check for live sessions (no end_ts) before invalidating."""
    assert "end_ts" in server_module_code, (
        "server.py auto-refresh must check node.end_ts to detect live sessions"
    )


def test_auto_refresh_60_second_interval(server_module_code: str) -> None:
    """Auto-refresh must sleep for 60 seconds between polls."""
    assert "60" in server_module_code, (
        "server.py auto-refresh must use asyncio.sleep(60) between cache invalidations"
    )


def test_end_ts_populated_from_metadata(tmp_path: Path) -> None:
    """discover_sessions must populate end_ts from metadata when available."""
    import json

    from amplifier_app_cost_viewer.reader import discover_sessions

    # Build a minimal amp_home with a session that has end_ts in metadata
    sessions_dir = tmp_path / "projects" / "p" / "sessions" / "sid-0001"
    sessions_dir.mkdir(parents=True)
    (sessions_dir / "events.jsonl").write_text(
        json.dumps({"event": "session:start", "ts": "2026-01-01T00:00:00.000+00:00", "data": {}})
        + "\n"
    )
    (sessions_dir / "metadata.json").write_text(
        json.dumps(
            {
                "session_id": "sid-0001",
                "parent_id": None,
                "project_slug": "p",
                "created": "2026-01-01T00:00:00.000+00:00",
                "end_ts": "2026-01-01T01:00:00.000+00:00",
            }
        )
    )

    sessions = discover_sessions(tmp_path)
    assert "sid-0001" in sessions
    assert sessions["sid-0001"].end_ts == "2026-01-01T01:00:00.000+00:00", (
        "discover_sessions must populate node.end_ts from metadata end_ts field"
    )
