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
    """TestClient with AMPLIFIER_HOME patched to amp_home and _roots_cache cleared.

    Clears _roots_cache before and after each test to prevent cross-test
    contamination from the in-memory session tree cache.
    """
    monkeypatch.setattr(_server, "AMPLIFIER_HOME", amp_home)
    _server._roots_cache = None  # clear before test
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    _server._roots_cache = None  # clear after test


# ---------------------------------------------------------------------------
# TestListSessions — GET /api/sessions  (7 tests)
# ---------------------------------------------------------------------------


class TestListSessions:
    def test_returns_200(self, client: TestClient) -> None:
        """GET /api/sessions returns HTTP 200."""
        response = client.get("/api/sessions")
        assert response.status_code == 200

    def test_returns_list(self, client: TestClient) -> None:
        """Response body is a JSON array."""
        response = client.get("/api/sessions")
        assert isinstance(response.json(), list)

    def test_returns_one_root(self, client: TestClient) -> None:
        """Fixture has exactly 1 root session; list length is 1."""
        response = client.get("/api/sessions")
        assert len(response.json()) == 1

    def test_root_session_id_present(self, client: TestClient) -> None:
        """Root session ID 'root-aabbccdd' appears in the first list entry."""
        response = client.get("/api/sessions")
        entry = response.json()[0]
        assert entry["session_id"] == ROOT_SESSION_ID

    def test_entry_has_required_fields(self, client: TestClient) -> None:
        """Each list entry contains all required summary fields."""
        response = client.get("/api/sessions")
        entry = response.json()[0]
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
        response = client.get("/api/sessions")
        entry = response.json()[0]
        assert entry["child_count"] == 2

    def test_total_cost_greater_than_own_cost(self, client: TestClient) -> None:
        """total_cost_usd includes children costs so it exceeds the root's own cost_usd."""
        response = client.get("/api/sessions")
        entry = response.json()[0]
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

    def test_returns_list(self, client: TestClient) -> None:
        """Response body is a JSON array."""
        response = client.get(f"/api/sessions/{ROOT_SESSION_ID}/spans")
        assert isinstance(response.json(), list)

    def test_returns_spans_from_all_three_sessions_count_3(
        self, client: TestClient
    ) -> None:
        """Flat span list collects one span from each of the 3 sessions (root + 2 children)."""
        response = client.get(f"/api/sessions/{ROOT_SESSION_ID}/spans")
        spans = response.json()
        # Fixture has 1 llm span per session × 3 sessions = 3 spans total
        assert len(spans) == 3

    def test_each_span_has_session_id_field(self, client: TestClient) -> None:
        """Every span in the flat list carries a 'session_id' field."""
        response = client.get(f"/api/sessions/{ROOT_SESSION_ID}/spans")
        spans = response.json()
        for span in spans:
            assert "session_id" in span

    def test_each_span_has_depth_field(self, client: TestClient) -> None:
        """Every span in the flat list carries a 'depth' field."""
        response = client.get(f"/api/sessions/{ROOT_SESSION_ID}/spans")
        spans = response.json()
        for span in spans:
            assert "depth" in span

    def test_root_spans_have_depth_zero_child_spans_have_depth_one(
        self, client: TestClient
    ) -> None:
        """Root session spans have depth == 0; child session spans have depth == 1."""
        response = client.get(f"/api/sessions/{ROOT_SESSION_ID}/spans")
        spans = response.json()

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
            sessions = response.json()
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
        sessions = response.json()
        ids = [s["session_id"] for s in sessions]
        assert ROOT_SESSION_ID in ids, (
            f"True root session {ROOT_SESSION_ID!r} must appear in list; got {ids}"
        )
