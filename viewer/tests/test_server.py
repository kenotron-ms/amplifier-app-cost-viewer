"""Integration tests for server.py API routes — 22 tests, all GREEN.

Tests cover the 4 FastAPI routes exposed by the Amplifier Cost Viewer backend:
  - GET /               → redirect to /static/index.html
  - GET /api/sessions   → list all root sessions with cost summary
  - GET /api/sessions/{id}       → full session tree
  - GET /api/sessions/{id}/spans → flattened spans with depth
"""

from __future__ import annotations

import json as _json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import amplifier_app_cost_viewer.server as _server  # RED: module does not exist yet
from amplifier_app_cost_viewer.server import app

# ---------------------------------------------------------------------------
# Session ID constants (mirror conftest.py)
# ---------------------------------------------------------------------------

ROOT_SESSION_ID = "root-aabbccdd"
CHILD1_SESSION_ID = "child1-11223344"
CHILD2_SESSION_ID = "child2-55667788"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client(amp_home: Path, monkeypatch) -> TestClient:
    """TestClient with AMPLIFIER_HOME patched to amp_home and caches cleared.

    Clears _roots_cache and _loaded_cache before and after each test to
    prevent cross-test contamination from the in-memory session tree cache.
    """
    monkeypatch.setattr(_server, "AMPLIFIER_HOME", amp_home)
    _server._roots_cache = None  # clear before test
    _server._loaded_cache = {}  # clear before test
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    _server._roots_cache = None  # clear after test
    _server._loaded_cache = {}  # clear after test


# ---------------------------------------------------------------------------
# TestListSessions — GET /api/sessions  (7 tests)
# ---------------------------------------------------------------------------


class TestListSessions:
    def test_returns_200(self, client: TestClient) -> None:
        """GET /api/sessions returns HTTP 200."""
        response = client.get("/api/sessions")
        assert response.status_code == 200

    def test_returns_pagination_envelope(self, client: TestClient) -> None:
        """Response body is a pagination envelope dict, not a bare list."""
        data = client.get("/api/sessions").json()
        assert isinstance(data, dict)
        assert "sessions" in data
        assert "total" in data
        assert "has_more" in data
        assert "next_offset" in data

    def test_returns_two_roots(self, client: TestClient) -> None:
        """Fixture has exactly 2 root sessions; total == 2."""
        data = client.get("/api/sessions").json()
        assert data["total"] == 2

    def test_root_session_id_present(self, client: TestClient) -> None:
        """Root session ID 'root-aabbccdd' appears somewhere in the sessions list."""
        data = client.get("/api/sessions").json()
        ids = [s["session_id"] for s in data["sessions"]]
        assert ROOT_SESSION_ID in ids

    def test_entry_has_required_fields(self, client: TestClient) -> None:
        """Each session entry contains all required summary fields."""
        data = client.get("/api/sessions").json()
        # Use ROOT_SESSION_ID entry which has known children
        sessions = {s["session_id"]: s for s in data["sessions"]}
        entry = sessions[ROOT_SESSION_ID]
        required = {
            "session_id",
            "project_slug",
            "start_ts",
            "duration_ms",
            "cost_usd",
            "total_cost_usd",
            "child_count",
        }
        assert required.issubset(entry.keys())

    def test_child_count_is_two(self, client: TestClient) -> None:
        """Root session has child_count == 2 (child1 + child2)."""
        data = client.get("/api/sessions").json()
        sessions = {s["session_id"]: s for s in data["sessions"]}
        assert sessions[ROOT_SESSION_ID]["child_count"] == 2

    def test_total_cost_greater_than_own_cost(self, client: TestClient) -> None:
        """total_cost_usd includes children costs so it exceeds the root's own cost_usd.

        Spans are lazy-loaded, so we must first fetch the session detail to
        trigger span loading, then re-check the list for aggregated costs.
        """
        # Trigger lazy loading for the root (also loads child spans)
        client.get(f"/api/sessions/{ROOT_SESSION_ID}")
        # Now the session list will reflect the loaded costs
        data = client.get("/api/sessions").json()
        sessions = {s["session_id"]: s for s in data["sessions"]}
        entry = sessions[ROOT_SESSION_ID]
        assert entry["total_cost_usd"] > entry["cost_usd"]


# ---------------------------------------------------------------------------
# TestGetSession — GET /api/sessions/{session_id}  (7 tests)
# ---------------------------------------------------------------------------


class TestGetSession:
    def test_returns_200_for_known_session(self, client: TestClient) -> None:
        """GET /api/sessions/{ROOT_SESSION_ID} returns HTTP 200."""
        response = client.get(f"/api/sessions/{ROOT_SESSION_ID}")
        assert response.status_code == 200

    def test_returns_404_for_unknown(self, client: TestClient) -> None:
        """GET /api/sessions/nonexistent-session returns HTTP 404."""
        response = client.get("/api/sessions/nonexistent-session-id")
        assert response.status_code == 404

    def test_response_has_spans_list(self, client: TestClient) -> None:
        """Response body includes a 'spans' key containing a list."""
        response = client.get(f"/api/sessions/{ROOT_SESSION_ID}")
        body = response.json()
        assert "spans" in body
        assert isinstance(body["spans"], list)

    def test_response_has_children_list_with_two_items(
        self, client: TestClient
    ) -> None:
        """Response body includes a 'children' key with exactly 2 child sessions."""
        response = client.get(f"/api/sessions/{ROOT_SESSION_ID}")
        body = response.json()
        assert "children" in body
        assert isinstance(body["children"], list)
        assert len(body["children"]) == 2

    def test_root_span_is_llm_type(self, client: TestClient) -> None:
        """At least one span in the root session has type == 'llm'."""
        response = client.get(f"/api/sessions/{ROOT_SESSION_ID}")
        spans = response.json()["spans"]
        llm_spans = [s for s in spans if s.get("type") == "llm"]
        assert len(llm_spans) >= 1

    def test_span_has_hex_color_field(self, client: TestClient) -> None:
        """Every span has a 'color' field that is a 7-character CSS hex string."""
        response = client.get(f"/api/sessions/{ROOT_SESSION_ID}")
        spans = response.json()["spans"]
        assert len(spans) > 0
        for span in spans:
            assert "color" in span
            assert span["color"].startswith("#")
            assert len(span["color"]) == 7

    def test_response_includes_correct_session_id(self, client: TestClient) -> None:
        """Response body 'session_id' matches the requested session_id."""
        response = client.get(f"/api/sessions/{ROOT_SESSION_ID}")
        body = response.json()
        assert body.get("session_id") == ROOT_SESSION_ID


# ---------------------------------------------------------------------------
# TestGetSessionSpans — GET /api/sessions/{session_id}/spans  (7 tests)
# ---------------------------------------------------------------------------


class TestGetSessionSpans:
    def test_returns_200_for_known_session(self, client: TestClient) -> None:
        """GET /api/sessions/{ROOT_SESSION_ID}/spans returns HTTP 200."""
        response = client.get(f"/api/sessions/{ROOT_SESSION_ID}/spans")
        assert response.status_code == 200

    def test_returns_404_for_unknown(self, client: TestClient) -> None:
        """GET /api/sessions/nonexistent/spans returns HTTP 404."""
        response = client.get("/api/sessions/nonexistent-session-id/spans")
        assert response.status_code == 404

    def test_returns_dict_with_spans_key(self, client: TestClient) -> None:
        """Response body is a dict with a 'spans' key containing a list."""
        response = client.get(f"/api/sessions/{ROOT_SESSION_ID}/spans")
        data = response.json()
        assert isinstance(data, dict), f"Expected dict, got {type(data).__name__}"
        assert "spans" in data, "Response must have 'spans' key"
        assert isinstance(data["spans"], list)

    def test_returns_spans_from_all_three_sessions_count_3(
        self, client: TestClient
    ) -> None:
        """Flat span list collects one span from each of the 3 sessions (root + 2 children)."""
        response = client.get(f"/api/sessions/{ROOT_SESSION_ID}/spans")
        spans = response.json()["spans"]
        # Fixture has 1 llm span per session × 3 sessions = 3 spans total
        assert len(spans) == 3

    def test_each_span_has_session_id_field(self, client: TestClient) -> None:
        """Every span in the flat list carries a 'session_id' field."""
        response = client.get(f"/api/sessions/{ROOT_SESSION_ID}/spans")
        spans = response.json()["spans"]
        for span in spans:
            assert "session_id" in span

    def test_each_span_has_depth_field(self, client: TestClient) -> None:
        """Every span in the flat list carries a 'depth' field."""
        response = client.get(f"/api/sessions/{ROOT_SESSION_ID}/spans")
        spans = response.json()["spans"]
        for span in spans:
            assert "depth" in span

    def test_root_spans_have_depth_zero_child_spans_have_depth_one(
        self, client: TestClient
    ) -> None:
        """Root session spans have depth == 0; child session spans have depth == 1."""
        response = client.get(f"/api/sessions/{ROOT_SESSION_ID}/spans")
        spans = response.json()["spans"]

        root_spans = [s for s in spans if s["session_id"] == ROOT_SESSION_ID]
        child_spans = [
            s
            for s in spans
            if s["session_id"] in {CHILD1_SESSION_ID, CHILD2_SESSION_ID}
        ]

        assert all(s["depth"] == 0 for s in root_spans)
        assert all(s["depth"] == 1 for s in child_spans)


# ---------------------------------------------------------------------------
# TestRootRoute — GET /  (1 test)
# ---------------------------------------------------------------------------


class TestRootRoute:
    def test_root_returns_redirect_to_static(self, client: TestClient) -> None:
        """GET / redirects to the static file root with a 3xx status code."""
        response = client.get("/", follow_redirects=False)
        assert response.status_code in {301, 302, 307, 308}


# ---------------------------------------------------------------------------
# TestSessionFilter — /api/sessions only returns true root sessions  (2 tests)
# ---------------------------------------------------------------------------


@pytest.fixture
def amp_home_with_orphan(tmp_path: Path) -> Path:
    """Create a fake ~/.amplifier with only an orphaned session.

    The orphaned session has parent_id set to a UUID that does NOT exist on
    disk — this is the Amplifier-format pattern where child sessions reference
    a root session that isn't stored locally.

    With the current (unfixed) build_tree, orphaned sessions are incorrectly
    treated as roots and appear in the dropdown.  After the fix, they must not.
    """
    base = tmp_path / ".amplifier"
    sessions_dir = base / "projects" / "test-project" / "sessions"
    sessions_dir.mkdir(parents=True)

    orphan_id = "0000000000000000-deadbeef_superpowers-implementer"
    session_dir = sessions_dir / orphan_id
    session_dir.mkdir()

    (session_dir / "metadata.json").write_text(
        _json.dumps(
            {
                "session_id": orphan_id,
                "parent_id": "a860b568-034d-4edf-8c90-ab4be8843a47",  # not on disk
                "project_slug": "test-project",
                "created": "2026-04-25T10:00:00.000+00:00",
            }
        )
    )
    # Minimal events file so the session is picked up by discover_sessions
    (session_dir / "events.jsonl").write_text(
        _json.dumps(
            {
                "event": "session:start",
                "ts": "2026-04-25T10:00:00.000+00:00",
                "data": {},
            }
        )
        + "\n"
    )

    return base


class TestSessionFilter:
    """Orphaned sessions (parent_id set but parent not on disk) must not appear
    in GET /api/sessions — only true root sessions (parent_id is None) are listed.
    """

    def test_orphaned_session_excluded_from_list(
        self, amp_home_with_orphan: Path, monkeypatch
    ) -> None:
        """Sessions with a parent_id set must not appear in /api/sessions even
        when their parent session does not exist on disk.
        """
        monkeypatch.setattr(_server, "AMPLIFIER_HOME", amp_home_with_orphan)
        _server._roots_cache = None
        try:
            with TestClient(app, raise_server_exceptions=True) as c:
                response = c.get("/api/sessions")
            assert response.status_code == 200
            data = response.json()
            sessions = data["sessions"]
            assert sessions == [], (
                "Orphaned session (parent_id set, parent not on disk) must not "
                f"appear in /api/sessions; got {sessions}"
            )
        finally:
            _server._roots_cache = None

    def test_true_root_session_appears_in_list(self, client: TestClient) -> None:
        """A session with parent_id=None (true root) must appear in /api/sessions."""
        response = client.get("/api/sessions")
        assert response.status_code == 200
        data = response.json()
        ids = [s["session_id"] for s in data["sessions"]]
        assert ROOT_SESSION_ID in ids, (
            f"True root session {ROOT_SESSION_ID!r} must appear in list; got {ids}"
        )


# ---------------------------------------------------------------------------
# TestSessionNameField — name field in API response
# ---------------------------------------------------------------------------


def test_session_name_in_list(client: TestClient, amp_home: Path) -> None:
    """GET /api/sessions includes name field (may be None) in each entry."""
    resp = client.get("/api/sessions")
    assert resp.status_code == 200
    data = resp.json()
    for s in data["sessions"]:
        assert "name" in s, f"'name' key must be present in session summary, got {s}"


# ---------------------------------------------------------------------------
# TestListSessionsPagination — pagination envelope (3 tests)
# ---------------------------------------------------------------------------


class TestListSessionsPagination:
    def test_list_sessions_default_limit(
        self, client: TestClient, amp_home: Path
    ) -> None:
        """GET /api/sessions returns envelope with pagination fields."""
        resp = client.get("/api/sessions")
        assert resp.status_code == 200
        data = resp.json()
        assert "sessions" in data
        assert "total" in data
        assert "has_more" in data
        assert "next_offset" in data

    def test_list_sessions_pagination(self, client: TestClient, amp_home: Path) -> None:
        """offset and limit params control which sessions are returned.

        amp_home fixture has 2 root sessions — verify offset slices correctly.
        """
        resp_p1 = client.get("/api/sessions?limit=1&offset=0")
        resp_p2 = client.get("/api/sessions?limit=1&offset=1")
        assert resp_p1.status_code == 200
        assert resp_p2.status_code == 200
        p1 = resp_p1.json()
        p2 = resp_p2.json()
        # Different sessions on each page
        assert p1["sessions"][0]["session_id"] != p2["sessions"][0]["session_id"]
        # has_more correct
        assert p1["has_more"] is True  # 2 total, 1 per page
        assert p2["has_more"] is False

    def test_list_sessions_total_consistent(
        self, client: TestClient, amp_home: Path
    ) -> None:
        """total field reflects the full count, not the page size."""
        resp = client.get("/api/sessions?limit=1&offset=0")
        data = resp.json()
        assert data["total"] >= 1
        assert len(data["sessions"]) == 1


# ---------------------------------------------------------------------------
# TestLazySpanLoading — spans must NOT load on session list  (2 tests)
# ---------------------------------------------------------------------------


def test_sessions_list_does_not_load_spans(
    client: TestClient, amp_home: Path, monkeypatch
) -> None:
    """GET /api/sessions must NOT trigger parse_spans for any session."""
    import amplifier_app_cost_viewer.reader as reader_mod

    calls: list = []
    original = reader_mod.parse_spans

    def spy(*args, **kwargs):
        calls.append(args)
        return original(*args, **kwargs)

    monkeypatch.setattr(reader_mod, "parse_spans", spy)

    # Clear cache so scan runs fresh
    import amplifier_app_cost_viewer.server as server_mod

    server_mod._roots_cache = None
    resp = client.get("/api/sessions")
    assert resp.status_code == 200
    assert len(calls) == 0, (
        f"parse_spans called {len(calls)} times during session list — "
        "span loading must be lazy (only triggered by /api/sessions/{id})"
    )


def test_refresh_endpoint_clears_cache(client: TestClient, amp_home: Path) -> None:
    """POST /api/refresh returns 200 with ok=True and clears _roots_cache."""
    import amplifier_app_cost_viewer.server as server_mod

    # Populate cache first via list call
    client.get("/api/sessions")
    assert server_mod._roots_cache is not None, (
        "cache must be populated after GET /api/sessions"
    )

    # Refresh should clear the cache
    response = client.post("/api/refresh")
    assert response.status_code == 200
    data = response.json()
    assert data.get("ok") is True
    assert server_mod._roots_cache is None, (
        "cache must be cleared after POST /api/refresh"
    )
    assert server_mod._loaded_cache == {}, (
        "_loaded_cache must be cleared after POST /api/refresh"
    )


def test_session_list_includes_token_counts_from_observability(
    tmp_path: Path, monkeypatch
) -> None:
    """GET /api/sessions includes total_input_tokens and total_output_tokens
    when observability JSONL is present with a session_summary record."""
    import json as _json_mod

    # Create amp_home with a session and observability data
    base = tmp_path / ".amplifier"
    sessions_dir = base / "projects" / "obs-project" / "sessions"
    sessions_dir.mkdir(parents=True)

    session_id = "obs-session-aabbccdd"
    session_dir = sessions_dir / session_id
    session_dir.mkdir()

    (session_dir / "metadata.json").write_text(
        _json_mod.dumps(
            {
                "session_id": session_id,
                "parent_id": None,
                "project_slug": "obs-project",
                "created": "2026-04-25T10:00:00.000+00:00",
            }
        )
    )
    (session_dir / "events.jsonl").write_text(
        _json_mod.dumps(
            {
                "event": "session:start",
                "ts": "2026-04-25T10:00:00.000+00:00",
                "data": {},
            }
        )
        + "\n"
    )

    # Create observability JSONL with session_summary containing token counts
    obs_dir = base / "observability"
    obs_dir.mkdir(parents=True)
    (obs_dir / f"{session_id}.jsonl").write_text(
        _json_mod.dumps(
            {
                "type": "session_summary",
                "total_cost_usd": 0.05,
                "total_input_tokens": 1000,
                "total_output_tokens": 250,
            }
        )
        + "\n"
    )

    monkeypatch.setattr(_server, "AMPLIFIER_HOME", base)
    _server._roots_cache = None
    _server._loaded_cache = {}

    with TestClient(app, raise_server_exceptions=True) as c:
        response = c.get("/api/sessions")

    _server._roots_cache = None
    _server._loaded_cache = {}

    assert response.status_code == 200
    data = response.json()
    sessions = {s["session_id"]: s for s in data["sessions"]}
    assert session_id in sessions, f"Expected {session_id} in {list(sessions.keys())}"
    entry = sessions[session_id]
    assert "total_input_tokens" in entry, (
        f"'total_input_tokens' must be present in session list entry; got keys: {list(entry.keys())}"
    )
    assert "total_output_tokens" in entry, (
        f"'total_output_tokens' must be present in session list entry; got keys: {list(entry.keys())}"
    )
    assert entry["total_input_tokens"] == 1000
    assert entry["total_output_tokens"] == 250


def test_session_detail_token_counts_nonzero(client: TestClient) -> None:
    """GET /api/sessions/{id} returns total_input_tokens and total_output_tokens > 0.

    _parse_all_spans_for_node must populate token fields from span data.
    Fixture has 512 input / 128 output tokens per session (from conftest.py).
    """
    response = client.get(f"/api/sessions/{ROOT_SESSION_ID}")
    assert response.status_code == 200
    body = response.json()
    assert "total_input_tokens" in body, (
        "total_input_tokens must be present in session detail"
    )
    assert "total_output_tokens" in body, (
        "total_output_tokens must be present in session detail"
    )
    assert body["total_input_tokens"] > 0, (
        f"total_input_tokens must be > 0 after span loading, got {body['total_input_tokens']}"
    )
    assert body["total_output_tokens"] > 0, (
        f"total_output_tokens must be > 0 after span loading, got {body['total_output_tokens']}"
    )


def test_prewarm_handler_in_server():
    """server.py has a startup prewarm handler."""
    server_path = Path("amplifier_app_cost_viewer/server.py")
    content = server_path.read_text()
    assert "_prewarm_cache" in content or "prewarm" in content.lower()
    assert "on_event" in content or "startup" in content


def test_spans_loaded_on_session_detail(
    client: TestClient, amp_home: Path, monkeypatch
) -> None:
    """GET /api/sessions/{id}/spans triggers parse_spans (lazy load)."""
    import amplifier_app_cost_viewer.reader as reader_mod

    calls: list = []
    original = reader_mod.parse_spans

    def spy(*args, **kwargs):
        calls.append(args)
        return original(*args, **kwargs)

    monkeypatch.setattr(reader_mod, "parse_spans", spy)

    import amplifier_app_cost_viewer.server as server_mod

    server_mod._roots_cache = None
    # _loaded_cache may not exist yet (pre-fix); setattr works on modules
    server_mod._loaded_cache = {}

    sessions = client.get("/api/sessions").json()["sessions"]
    # Clear any calls that happened during the session LIST (should be 0 post-fix,
    # but reset here so we only assert calls triggered by the spans endpoint)
    calls.clear()

    sid = sessions[0]["session_id"]
    client.get(f"/api/sessions/{sid}/spans")
    assert len(calls) > 0, (
        "parse_spans should be called when fetching /api/sessions/{id}/spans "
        "(lazy span loading is not working)"
    )
