"""TDD RED tests for performance fixes:
1. Streaming _read_events with skip of large/useless events
2. only_root parameter on spans endpoint
3. child-spans endpoint
4. Progressive loading in app.js
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Tests: Fix 1 — _read_events streaming with event skipping
# ---------------------------------------------------------------------------


def test_read_events_skips_llm_request(tmp_path):
    """_read_events must skip llm:request lines without JSON-parsing them."""
    from amplifier_app_cost_viewer.reader import _read_events

    ef = tmp_path / "events.jsonl"
    ef.write_text(
        '{"event":"session:start","ts":"2026-01-01T00:00:00Z"}\n'
        '{"event":"llm:request","ts":"2026-01-01T00:00:01Z"}\n'
        '{"event":"provider:request","ts":"2026-01-01T00:00:02Z","data":{"model":"claude"}}\n'
    )
    events = _read_events(ef)
    event_names = [e.get("event") for e in events]
    assert "llm:request" not in event_names
    assert "session:start" in event_names
    assert "provider:request" in event_names


def test_read_events_skips_session_resume(tmp_path):
    """_read_events must skip session:resume lines."""
    from amplifier_app_cost_viewer.reader import _read_events

    ef = tmp_path / "events.jsonl"
    ef.write_text(
        '{"event":"session:resume","ts":"2026-01-01T00:00:00Z"}\n'
        '{"event":"provider:request","ts":"2026-01-01T00:00:01Z"}\n'
    )
    events = _read_events(ef)
    assert not any(e.get("event") == "session:resume" for e in events)
    assert any(e.get("event") == "provider:request" for e in events)


def test_read_events_skips_context_snapshot(tmp_path):
    """_read_events must skip context:snapshot lines."""
    from amplifier_app_cost_viewer.reader import _read_events

    ef = tmp_path / "events.jsonl"
    ef.write_text(
        '{"event":"session:start","ts":"2026-01-01T00:00:00Z"}\n'
        '{"event":"context:snapshot","ts":"2026-01-01T00:00:01Z","data":{"huge":"payload"}}\n'
        '{"event":"llm:response","ts":"2026-01-01T00:00:02Z","data":{}}\n'
    )
    events = _read_events(ef)
    event_names = [e.get("event") for e in events]
    assert "context:snapshot" not in event_names
    assert "session:start" in event_names
    assert "llm:response" in event_names


def test_read_events_streams_not_loads_whole_file(tmp_path):
    """_read_events must open file with open() not read_text() (streaming)."""
    from amplifier_app_cost_viewer import reader
    import inspect as _inspect

    source = _inspect.getsource(reader._read_events)
    # Should NOT use read_text() (which loads entire file)
    assert "read_text()" not in source, (
        "_read_events must NOT use .read_text() — it must stream line by line"
    )
    # Should use open() for streaming
    assert "open(" in source, (
        "_read_events must use file open() for streaming line-by-line reads"
    )


def test_skip_events_frozenset_exists():
    """_SKIP_EVENTS frozenset must be defined in reader module."""
    from amplifier_app_cost_viewer import reader

    assert hasattr(reader, "_SKIP_EVENTS"), (
        "reader.py must define a _SKIP_EVENTS frozenset of byte strings to skip"
    )
    skip = reader._SKIP_EVENTS
    assert isinstance(skip, frozenset), "_SKIP_EVENTS must be a frozenset"
    # Check expected skip patterns are present
    assert b'"llm:request"' in skip, "_SKIP_EVENTS must include b'\"llm:request\"'"
    assert b'"session:resume"' in skip, (
        "_SKIP_EVENTS must include b'\"session:resume\"'"
    )


# ---------------------------------------------------------------------------
# Tests: Fix 2 — only_root parameter on spans endpoint
# ---------------------------------------------------------------------------


def test_spans_endpoint_supports_only_root():
    """GET /api/sessions/{id}/spans?only_root=true must be a valid parameter."""
    import amplifier_app_cost_viewer.server as srv

    sig = inspect.signature(srv.get_spans)
    assert "only_root" in sig.parameters, "get_spans must have an 'only_root' parameter"


def test_spans_endpoint_returns_dict(amp_home, monkeypatch):
    """GET /api/sessions/{id}/spans returns a dict with 'spans' key."""
    from fastapi.testclient import TestClient
    import amplifier_app_cost_viewer.server as _server
    from amplifier_app_cost_viewer.server import app

    monkeypatch.setattr(_server, "AMPLIFIER_HOME", amp_home)
    _server._roots_cache = None
    _server._loaded_cache = {}
    with TestClient(app, raise_server_exceptions=True) as c:
        resp = c.get("/api/sessions/root-aabbccdd/spans")
    _server._roots_cache = None
    _server._loaded_cache = {}

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict), (
        f"GET /spans must return a dict, got {type(data).__name__}"
    )
    assert "spans" in data, "Response dict must have 'spans' key"
    assert isinstance(data["spans"], list), "'spans' value must be a list"


def test_spans_endpoint_partial_flag_present(amp_home, monkeypatch):
    """Response dict must include 'partial' key."""
    from fastapi.testclient import TestClient
    import amplifier_app_cost_viewer.server as _server
    from amplifier_app_cost_viewer.server import app

    monkeypatch.setattr(_server, "AMPLIFIER_HOME", amp_home)
    _server._roots_cache = None
    _server._loaded_cache = {}
    with TestClient(app, raise_server_exceptions=True) as c:
        resp = c.get("/api/sessions/root-aabbccdd/spans")
    _server._roots_cache = None
    _server._loaded_cache = {}

    data = resp.json()
    assert "partial" in data, "Response dict must have 'partial' key"


def test_spans_endpoint_only_root_returns_fewer_spans(amp_home, monkeypatch):
    """?only_root=true returns fewer spans than the full load."""
    from fastapi.testclient import TestClient
    import amplifier_app_cost_viewer.server as _server
    from amplifier_app_cost_viewer.server import app

    monkeypatch.setattr(_server, "AMPLIFIER_HOME", amp_home)
    _server._roots_cache = None
    _server._loaded_cache = {}
    with TestClient(app, raise_server_exceptions=True) as c:
        full = c.get("/api/sessions/root-aabbccdd/spans")
        _server._loaded_cache = {}  # clear so full load can happen again
        partial = c.get("/api/sessions/root-aabbccdd/spans?only_root=true")
    _server._roots_cache = None
    _server._loaded_cache = {}

    full_spans = full.json()["spans"]
    partial_spans = partial.json()["spans"]
    # Full has 3 spans (root + 2 children), partial has 1 (root only)
    assert len(partial_spans) < len(full_spans), (
        "only_root=true must return fewer spans than a full load"
    )
    assert partial.json()["partial"] is True, "partial flag must be True for only_root"


# ---------------------------------------------------------------------------
# Tests: Fix 2b — child-spans endpoint
# ---------------------------------------------------------------------------


def test_child_spans_endpoint_exists():
    """GET /api/sessions/{id}/child-spans/{child_id} must be a registered route."""
    from amplifier_app_cost_viewer.server import app

    routes = [getattr(r, "path", "") for r in app.routes]
    assert any("child-spans" in p for p in routes), (
        f"No 'child-spans' route found. Routes: {routes}"
    )


def test_child_spans_returns_spans_for_child(amp_home, monkeypatch):
    """GET /api/sessions/{root_id}/child-spans/{child_id} returns child spans."""
    from fastapi.testclient import TestClient
    import amplifier_app_cost_viewer.server as _server
    from amplifier_app_cost_viewer.server import app

    monkeypatch.setattr(_server, "AMPLIFIER_HOME", amp_home)
    _server._roots_cache = None
    _server._loaded_cache = {}
    with TestClient(app, raise_server_exceptions=True) as c:
        resp = c.get("/api/sessions/root-aabbccdd/child-spans/child1-11223344")
    _server._roots_cache = None
    _server._loaded_cache = {}

    assert resp.status_code == 200
    data = resp.json()
    assert "spans" in data
    assert len(data["spans"]) > 0, "Child spans must include at least 1 span"


def test_child_spans_404_for_unknown_child(amp_home, monkeypatch):
    """GET .../child-spans/nonexistent returns 404."""
    from fastapi.testclient import TestClient
    import amplifier_app_cost_viewer.server as _server
    from amplifier_app_cost_viewer.server import app

    monkeypatch.setattr(_server, "AMPLIFIER_HOME", amp_home)
    _server._roots_cache = None
    _server._loaded_cache = {}
    with TestClient(app, raise_server_exceptions=True) as c:
        resp = c.get("/api/sessions/root-aabbccdd/child-spans/nonexistent-child")
    _server._roots_cache = None
    _server._loaded_cache = {}
    assert resp.status_code == 404


def test_find_node_helper_exists():
    """server.py must define _find_node(root, session_id) helper."""
    import amplifier_app_cost_viewer.server as srv

    assert hasattr(srv, "_find_node"), "server.py must define _find_node helper"
    sig = inspect.signature(srv._find_node)
    params = list(sig.parameters.keys())
    assert len(params) >= 2, "_find_node must accept at least (root, session_id)"


# ---------------------------------------------------------------------------
# Tests: Fix 3 — app.js progressive loading
# ---------------------------------------------------------------------------


STATIC = Path(__file__).parent.parent / "amplifier_app_cost_viewer" / "static"
APP_JS = STATIC / "app.js"


@pytest.fixture
def app_js_code() -> str:
    return APP_JS.read_text()


def test_progressive_loading_function_exists(app_js_code: str) -> None:
    """app.js must have progressive child span loading function."""
    assert "_loadChildSpansProgressively" in app_js_code, (
        "app.js must define _loadChildSpansProgressively for background child loading"
    )


def test_fetch_spans_supports_only_root(app_js_code: str) -> None:
    """fetchSpans must support only_root parameter."""
    assert "only_root" in app_js_code or "onlyRoot" in app_js_code, (
        "fetchSpans must support an only_root (or onlyRoot) parameter"
    )


def test_load_session_uses_only_root_initially(app_js_code: str) -> None:
    """loadSession must call fetchSpans with only_root=true (or onlyRoot=true)."""
    assert (
        "only_root=true" in app_js_code
        or "onlyRoot = true" in app_js_code
        or "true" in app_js_code
    ), "loadSession must initially fetch spans with only_root=true for fast first paint"
    # More specific: fetchSpans called with true argument
    assert (
        "fetchSpans(id, true)" in app_js_code or "fetchSpans(id,true)" in app_js_code
    ), "loadSession must call fetchSpans(id, true) to load only root spans initially"


def test_child_spans_url_used_in_app_js(app_js_code: str) -> None:
    """app.js must reference the child-spans API endpoint."""
    assert "child-spans" in app_js_code, (
        "app.js must call /api/sessions/{id}/child-spans/{child_id} for lazy loading"
    )


def test_fetch_spans_reads_data_spans_key(app_js_code: str) -> None:
    """fetchSpans must read data.spans (dict response format)."""
    assert "data.spans" in app_js_code, (
        "fetchSpans must read data.spans from the response dict (not treat response as array)"
    )
