"""Tests for reader.py — written FIRST before file exists (TDD RED).

Imports TOOL_COLOR, THINKING_COLOR, normalize_timestamps, parse_spans from
amplifier_app_cost_viewer.reader.  All tests are RED until reader.py
is implemented.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from amplifier_app_cost_viewer.reader import (
    THINKING_COLOR,
    TOOL_COLOR,
    Span,
    normalize_timestamps,
    parse_spans,
)

# ---------------------------------------------------------------------------
# Synthetic test data
# ---------------------------------------------------------------------------

# Base time: 2026-04-24T10:00:00 UTC
_BASE_DT = datetime(2026, 4, 24, 10, 0, 0, tzinfo=timezone.utc)
_BASE_MS = int(_BASE_DT.timestamp() * 1000)


def _ms_to_iso(offset_ms: int) -> str:
    """Convert a ms offset from base time to ISO 8601 UTC string."""
    total_ms = _BASE_MS + offset_ms
    dt = datetime.fromtimestamp(total_ms / 1000, tz=timezone.utc)
    millis = total_ms % 1000
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{millis:03d}Z"


SYNTHETIC_EVENTS = "\n".join(
    [
        json.dumps(
            {
                "event": "session:start",
                "ts": _ms_to_iso(0),
                "data": {"session_id": "test-session"},
            }
        ),
        json.dumps(
            {
                "event": "provider:request",
                "ts": _ms_to_iso(2000),
                "data": {"provider": "anthropic"},
            }
        ),
        json.dumps(
            {
                "event": "thinking:delta",
                "ts": _ms_to_iso(3000),
                "data": {},
            }
        ),
        json.dumps(
            {
                "event": "thinking:final",
                "ts": _ms_to_iso(5000),
                "data": {},
            }
        ),
        json.dumps(
            {
                "event": "llm:response",
                "ts": _ms_to_iso(10700),
                "data": {
                    "duration_ms": 8700,
                    "model": "claude-sonnet-4-5",
                    "usage": {
                        "input_tokens": 512,
                        "output_tokens": 128,
                        "cache_read_tokens": 0,
                        "cache_write_tokens": 0,
                    },
                },
            }
        ),
        json.dumps(
            {
                "event": "tool:pre",
                "ts": _ms_to_iso(10900),
                "data": {
                    "tool_call_id": "call_abc123",
                    "tool_name": "bash",
                    "command": "ls -la",
                },
            }
        ),
        json.dumps(
            {
                "event": "tool:post",
                "ts": _ms_to_iso(11242),
                "data": {
                    "tool_call_id": "call_abc123",
                    "success": True,
                },
            }
        ),
        json.dumps(
            {
                "event": "session:end",
                "ts": _ms_to_iso(30000),
                "data": {},
            }
        ),
    ]
)

EVENTS_UNPAIRED_TOOL = "\n".join(
    [
        json.dumps(
            {
                "event": "session:start",
                "ts": _ms_to_iso(0),
                "data": {"session_id": "test-session"},
            }
        ),
        json.dumps(
            {
                "event": "tool:pre",
                "ts": _ms_to_iso(1000),
                "data": {
                    "tool_call_id": "call_orphan",
                    "tool_name": "bash",
                    "command": "echo hi",
                },
            }
        ),
        json.dumps(
            {
                "event": "session:end",
                "ts": _ms_to_iso(5000),
                "data": {},
            }
        ),
    ]
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_events(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "events.jsonl"
    p.write_text(content)
    return p


def _get_spans(tmp_path: Path, content: str = SYNTHETIC_EVENTS) -> list[Span]:
    p = _write_events(tmp_path, content)
    session_start_ms = normalize_timestamps(p)
    return parse_spans(p, session_start_ms)


# ---------------------------------------------------------------------------
# TestNormalizeTimestamps (2 tests)
# ---------------------------------------------------------------------------


class TestNormalizeTimestamps:
    def test_returns_session_start_ms(self, tmp_path: Path):
        """normalize_timestamps returns Unix ms matching 2026-04-24T10:00:00 UTC."""
        p = _write_events(tmp_path, SYNTHETIC_EVENTS)
        result = normalize_timestamps(p)
        assert result == _BASE_MS

    def test_returns_int(self, tmp_path: Path):
        """normalize_timestamps returns an int, not a float."""
        p = _write_events(tmp_path, SYNTHETIC_EVENTS)
        result = normalize_timestamps(p)
        assert isinstance(result, int)


# ---------------------------------------------------------------------------
# TestParseSpansLlm (5 tests)
# ---------------------------------------------------------------------------


class TestParseSpansLlm:
    def test_llm_span_created(self, tmp_path: Path):
        """Exactly 1 LLM span is created from the synthetic events."""
        spans = _get_spans(tmp_path)
        llm_spans = [s for s in spans if s["type"] == "llm"]
        assert len(llm_spans) == 1

    def test_llm_span_start_offset(self, tmp_path: Path):
        """LLM span starts at provider:request (2000ms) and ends at llm:response (10700ms)."""
        spans = _get_spans(tmp_path)
        llm = next(s for s in spans if s["type"] == "llm")
        assert llm["start_ms"] == 2000
        assert llm["end_ms"] == 10700

    def test_llm_span_tokens(self, tmp_path: Path):
        """LLM span captures input=512, output=128, provider=anthropic, model=claude-sonnet-4-5."""
        spans = _get_spans(tmp_path)
        llm = next(s for s in spans if s["type"] == "llm")
        assert llm["input_tokens"] == 512
        assert llm["output_tokens"] == 128
        assert llm["provider"] == "anthropic"
        assert llm["model"] == "claude-sonnet-4-5"

    def test_llm_span_cost_nonzero(self, tmp_path: Path):
        """LLM span cost_usd ≈ 0.003456 (512*3e-6 + 128*15e-6)."""
        spans = _get_spans(tmp_path)
        llm = next(s for s in spans if s["type"] == "llm")
        expected = 512 * 3e-6 + 128 * 15e-6  # = 0.003456
        assert abs(llm["cost_usd"] - expected) < 1e-6

    def test_llm_span_color_is_hex(self, tmp_path: Path):
        """LLM span color is a valid 7-character CSS hex string."""
        spans = _get_spans(tmp_path)
        llm = next(s for s in spans if s["type"] == "llm")
        assert llm["color"].startswith("#")
        assert len(llm["color"]) == 7


# ---------------------------------------------------------------------------
# TestParseSpansTool (4 tests)
# ---------------------------------------------------------------------------


class TestParseSpansTool:
    def test_tool_span_created(self, tmp_path: Path):
        """Exactly 1 tool span is created from the paired tool:pre/tool:post."""
        spans = _get_spans(tmp_path)
        tool_spans = [s for s in spans if s["type"] == "tool"]
        assert len(tool_spans) == 1

    def test_tool_span_matched_by_tool_call_id(self, tmp_path: Path):
        """Tool span is matched by tool_call_id: start=10900, end=11242, name=bash, success=True."""
        spans = _get_spans(tmp_path)
        tool = next(s for s in spans if s["type"] == "tool")
        assert tool["start_ms"] == 10900
        assert tool["end_ms"] == 11242
        assert tool["tool_name"] == "bash"
        assert tool["success"] is True

    def test_tool_span_color_is_slate(self, tmp_path: Path):
        """Tool span color equals the TOOL_COLOR sentinel constant."""
        spans = _get_spans(tmp_path)
        tool = next(s for s in spans if s["type"] == "tool")
        assert tool["color"] == TOOL_COLOR

    def test_unpaired_tool_pre_silently_dropped(self, tmp_path: Path):
        """An orphaned tool:pre with no matching tool:post produces 0 tool spans."""
        spans = _get_spans(tmp_path, EVENTS_UNPAIRED_TOOL)
        tool_spans = [s for s in spans if s["type"] == "tool"]
        assert len(tool_spans) == 0


# ---------------------------------------------------------------------------
# TestParseSpansThinking (3 tests)
# ---------------------------------------------------------------------------


class TestParseSpansThinking:
    def test_thinking_span_created(self, tmp_path: Path):
        """Exactly 1 thinking span is created from the thinking:delta/thinking:final pair."""
        spans = _get_spans(tmp_path)
        thinking_spans = [s for s in spans if s["type"] == "thinking"]
        assert len(thinking_spans) == 1

    def test_thinking_span_offsets(self, tmp_path: Path):
        """Thinking span starts at thinking:delta (3000ms) and ends at thinking:final (5000ms)."""
        spans = _get_spans(tmp_path)
        thinking = next(s for s in spans if s["type"] == "thinking")
        assert thinking["start_ms"] == 3000
        assert thinking["end_ms"] == 5000

    def test_thinking_span_color_is_indigo(self, tmp_path: Path):
        """Thinking span color equals the THINKING_COLOR sentinel constant."""
        spans = _get_spans(tmp_path)
        thinking = next(s for s in spans if s["type"] == "thinking")
        assert thinking["color"] == THINKING_COLOR


# ---------------------------------------------------------------------------
# TestParseSpansOrder (2 tests)
# ---------------------------------------------------------------------------


class TestParseSpansOrder:
    def test_spans_sorted_by_start_ms(self, tmp_path: Path):
        """All 3 spans are returned in ascending start_ms order."""
        spans = _get_spans(tmp_path)
        start_ms_values = [s["start_ms"] for s in spans]
        assert start_ms_values == sorted(start_ms_values)

    def test_span_types_in_order(self, tmp_path: Path):
        """Spans sorted by start_ms produce types ['llm', 'thinking', 'tool']."""
        spans = _get_spans(tmp_path)
        types = [s["type"] for s in spans]
        assert types == ["llm", "thinking", "tool"]


# ---------------------------------------------------------------------------
# Session tree building tests (task-10 TDD RED)
# These tests import stub functions that raise NotImplementedError.
# ---------------------------------------------------------------------------

from amplifier_app_cost_viewer.reader import (  # noqa: E402
    SessionNode,
    aggregate_costs,
    build_session_tree,
    build_tree,
    discover_sessions,
)
from amplifier_app_cost_viewer.reader import _parse_all_spans  # noqa: E402  (private, test-only)


# ---------------------------------------------------------------------------
# TestDiscoverSessions (7 tests)
# ---------------------------------------------------------------------------


class TestDiscoverSessions:
    def test_finds_all_four_sessions(self, amp_home: Path):
        """discover_sessions returns a dict with 4 entries (2 roots + 2 children)."""
        sessions = discover_sessions(amp_home)
        assert len(sessions) == 4

    def test_session_ids_are_correct(self, amp_home: Path):
        """discover_sessions dict keys match all four session IDs."""
        sessions = discover_sessions(amp_home)
        expected = {
            "root-aabbccdd",
            "root2-eeffgghh",
            "child1-11223344",
            "child2-55667788",
        }
        assert set(sessions.keys()) == expected

    def test_root_has_no_parent_id(self, amp_home: Path):
        """Root session node has parent_id == None."""
        sessions = discover_sessions(amp_home)
        root = sessions["root-aabbccdd"]
        assert root.parent_id is None

    def test_children_have_correct_parent_id(self, amp_home: Path):
        """Both child sessions point to the root session ID as parent_id."""
        sessions = discover_sessions(amp_home)
        assert sessions["child1-11223344"].parent_id == "root-aabbccdd"
        assert sessions["child2-55667788"].parent_id == "root-aabbccdd"

    def test_session_node_has_project_slug(self, amp_home: Path):
        """Root session node carries the correct project_slug."""
        sessions = discover_sessions(amp_home)
        assert sessions["root-aabbccdd"].project_slug == "test-project"

    def test_empty_projects_dir_returns_empty(self, tmp_path: Path):
        """When projects/ dir exists but is empty, discover_sessions returns {}."""
        empty_home = tmp_path / ".amplifier"
        (empty_home / "projects").mkdir(parents=True)
        sessions = discover_sessions(empty_home)
        assert sessions == {}

    def test_session_node_has_events_path(self, amp_home: Path):
        """Root session node has a non-None events_path that exists on disk."""
        sessions = discover_sessions(amp_home)
        node = sessions["root-aabbccdd"]
        assert node.events_path is not None
        assert node.events_path.exists()


# ---------------------------------------------------------------------------
# TestBuildTree (4 tests)
# ---------------------------------------------------------------------------


class TestBuildTree:
    def test_returns_two_roots(self, amp_home: Path):
        """build_tree with 2 roots + 2 children returns a list of length 2."""
        sessions = discover_sessions(amp_home)
        roots = build_tree(sessions)
        assert len(roots) == 2

    def test_root_has_two_children(self, amp_home: Path):
        """root-aabbccdd node has exactly 2 children after build_tree."""
        sessions = discover_sessions(amp_home)
        roots = build_tree(sessions)
        root_with_children = next(r for r in roots if len(r.children) == 2)
        assert len(root_with_children.children) == 2

    def test_root_session_ids_present(self, amp_home: Path):
        """Both root session IDs ('root-aabbccdd' and 'root2-eeffgghh') appear in roots."""
        sessions = discover_sessions(amp_home)
        roots = build_tree(sessions)
        root_ids = {r.session_id for r in roots}
        assert "root-aabbccdd" in root_ids
        assert "root2-eeffgghh" in root_ids

    def test_children_session_ids(self, amp_home: Path):
        """root-aabbccdd children session_ids match the two child IDs."""
        sessions = discover_sessions(amp_home)
        roots = build_tree(sessions)
        root_with_children = next(r for r in roots if r.session_id == "root-aabbccdd")
        child_ids = {c.session_id for c in root_with_children.children}
        assert child_ids == {"child1-11223344", "child2-55667788"}


# ---------------------------------------------------------------------------
# TestAggregateCosts (2 tests)
# ---------------------------------------------------------------------------


class TestAggregateCosts:
    def test_root_total_includes_children(self):
        """aggregate_costs sets root.total_cost_usd = own + sum of children."""
        child1 = SessionNode(
            session_id="c1",
            project_slug="p",
            parent_id="root",
            start_ts="2026-01-01T00:00:00+00:00",
            end_ts=None,
            duration_ms=0,
            cost_usd=0.5,
            total_cost_usd=0.5,
            spans=[],
            children=[],
        )
        child2 = SessionNode(
            session_id="c2",
            project_slug="p",
            parent_id="root",
            start_ts="2026-01-01T00:00:01+00:00",
            end_ts=None,
            duration_ms=0,
            cost_usd=0.5,
            total_cost_usd=0.5,
            spans=[],
            children=[],
        )
        root = SessionNode(
            session_id="root",
            project_slug="p",
            parent_id=None,
            start_ts="2026-01-01T00:00:00+00:00",
            end_ts=None,
            duration_ms=0,
            cost_usd=1.0,
            total_cost_usd=1.0,
            spans=[],
            children=[child1, child2],
        )
        aggregate_costs(root)
        assert root.total_cost_usd == 2.0

    def test_leaf_total_equals_own_cost(self):
        """aggregate_costs on a leaf sets total_cost_usd == cost_usd."""
        leaf = SessionNode(
            session_id="leaf",
            project_slug="p",
            parent_id=None,
            start_ts="2026-01-01T00:00:00+00:00",
            end_ts=None,
            duration_ms=0,
            cost_usd=0.42,
            total_cost_usd=0.0,
            spans=[],
            children=[],
        )
        aggregate_costs(leaf)
        assert leaf.total_cost_usd == leaf.cost_usd


# ---------------------------------------------------------------------------
# TestBuildSessionTree (6 tests)
# ---------------------------------------------------------------------------


class TestBuildSessionTree:
    def test_returns_list_of_roots(self, amp_home: Path):
        """build_session_tree returns a list with exactly 2 roots (root + root2)."""
        result = build_session_tree(amp_home)
        assert isinstance(result, list)
        assert len(result) == 2

    def test_root_has_children(self, amp_home: Path):
        """root-aabbccdd node returned by build_session_tree has 2 children."""
        roots = build_session_tree(amp_home)
        # root-aabbccdd (older) has 2 children; root2-eeffgghh (newer) has 0
        root_with_children = next(r for r in roots if len(r.children) == 2)
        assert len(root_with_children.children) == 2

    def test_root_spans_empty_before_load(self, amp_home: Path):
        """build_session_tree is metadata-only — spans are empty until lazy-loaded."""
        roots = build_session_tree(amp_home)
        for root in roots:
            assert root.spans == [], (
                f"{root.session_id} should have empty spans after build_session_tree "
                "(spans are loaded lazily on demand)"
            )

    def test_root_spans_parsed_after_explicit_load(self, amp_home: Path):
        """Each root session node has exactly 1 LLM span after explicit span loading."""
        roots = build_session_tree(amp_home)
        for root in roots:
            # Load spans explicitly (simulating lazy loading)
            assert root.events_path is not None, (
                f"{root.session_id} must have events_path"
            )
            root_start_ms = normalize_timestamps(root.events_path)
            _parse_all_spans(root, root_start_ms)
            llm_spans = [s for s in root.spans if s.type == "llm"]
            assert len(llm_spans) == 1, f"{root.session_id} should have 1 LLM span"

    def test_own_cost_nonzero(self, amp_home: Path):
        """Each root node cost_usd (own cost) is > 0 after explicit span loading."""
        roots = build_session_tree(amp_home)
        for root in roots:
            assert root.events_path is not None, (
                f"{root.session_id} must have events_path"
            )
            root_start_ms = normalize_timestamps(root.events_path)
            _parse_all_spans(root, root_start_ms)
            assert root.cost_usd > 0, f"{root.session_id} should have non-zero cost"

    def test_total_cost_aggregated(self, amp_home: Path):
        """root-aabbccdd total_cost_usd == 3 sessions × $0.003456 = $0.010368.

        Requires explicit span loading (lazy) followed by aggregate_costs.
        """
        roots = build_session_tree(amp_home)
        # Find the root with children (root-aabbccdd has 2 children, root2 has none)
        root_with_children = next(r for r in roots if len(r.children) == 2)
        assert root_with_children.events_path is not None
        root_start_ms = normalize_timestamps(root_with_children.events_path)
        _parse_all_spans(root_with_children, root_start_ms)
        aggregate_costs(root_with_children)
        expected = 3 * 0.003456  # = 0.010368
        assert abs(root_with_children.total_cost_usd - expected) < 1e-6

    def test_sorted_most_recent_first(self, amp_home: Path):
        """build_session_tree returns roots sorted most-recent first."""
        # Add an older root session (1 day before the fixture root)
        OLD_ROOT_ID = "older-root-00112233"
        OLD_ROOT_ISO = "2026-04-23T10:00:00.000+00:00"
        session_dir = amp_home / "projects" / "test-project" / "sessions" / OLD_ROOT_ID
        session_dir.mkdir(parents=True)
        old_events = "\n".join(
            [
                json.dumps(
                    {
                        "event": "session:start",
                        "ts": OLD_ROOT_ISO,
                        "data": {"session_id": OLD_ROOT_ID},
                    }
                ),
                json.dumps({"event": "session:end", "ts": OLD_ROOT_ISO, "data": {}}),
            ]
        )
        (session_dir / "events.jsonl").write_text(old_events)
        (session_dir / "metadata.json").write_text(
            json.dumps(
                {
                    "session_id": OLD_ROOT_ID,
                    "parent_id": None,
                    "project_slug": "test-project",
                    "created": OLD_ROOT_ISO,
                }
            )
        )

        roots = build_session_tree(amp_home)
        # Three roots now: root2 (2026-04-24T11:00), root1 (2026-04-24T10:00), older (2026-04-23)
        assert len(roots) >= 3
        # Most recent root (root2-eeffgghh at 11:00) should be first
        assert roots[0].session_id == "root2-eeffgghh"
        # Oldest root must be last
        assert roots[-1].session_id == OLD_ROOT_ID


# ---------------------------------------------------------------------------
# TestDiscoverSessionsRealMetadataFormat (2 tests)
# ---------------------------------------------------------------------------


class TestDiscoverSessionsRealMetadataFormat:
    """Test that discover_sessions handles real Amplifier metadata format.

    Real sessions store project_slug in config.project_slug (or not at all
    at the top level), unlike the synthetic test fixtures which put it at
    the top level.
    """

    def test_real_root_metadata_format_is_discovered(self, tmp_path: Path):
        """Real root sessions (no top-level project_slug) are discovered."""
        import json as _json
        from amplifier_app_cost_viewer.reader import discover_sessions

        # Create a session with real Amplifier metadata format
        # (no top-level project_slug; config.project_slug only)
        project = "real-project"
        session_id = "real-root-aabbccdd"
        amp_home = tmp_path / ".amplifier"
        session_dir = amp_home / "projects" / project / "sessions" / session_id
        session_dir.mkdir(parents=True)

        # Real root format: project_slug NOT at top level
        metadata = {
            "session_id": session_id,
            "parent_id": None,
            "created": "2026-04-24T10:00:00.000+00:00",
            "bundle": "foundation",
            "model": "claude-sonnet-4-5",
            "turn_count": 5,
            "working_dir": "/home/user/project",
            "name": "My session",
        }
        (session_dir / "metadata.json").write_text(_json.dumps(metadata))

        events = "\n".join(
            [
                _json.dumps(
                    {
                        "event": "session:start",
                        "ts": "2026-04-24T10:00:00.000+00:00",
                        "data": {"session_id": session_id},
                    }
                ),
                _json.dumps(
                    {
                        "event": "session:end",
                        "ts": "2026-04-24T10:00:30.000+00:00",
                        "data": {},
                    }
                ),
            ]
        )
        (session_dir / "events.jsonl").write_text(events)

        sessions = discover_sessions(amp_home)
        assert session_id in sessions, (
            "Real-format metadata (no top-level project_slug) should be discovered"
        )

    def test_real_root_metadata_derives_project_slug_from_directory(
        self, tmp_path: Path
    ):
        """When project_slug is absent, it is derived from the project dir name."""
        import json as _json
        from amplifier_app_cost_viewer.reader import discover_sessions

        project = "derived-project-slug"
        session_id = "derived-root-12345678"
        amp_home = tmp_path / ".amplifier"
        session_dir = amp_home / "projects" / project / "sessions" / session_id
        session_dir.mkdir(parents=True)

        # No project_slug anywhere in metadata
        metadata = {
            "session_id": session_id,
            "parent_id": None,
            "created": "2026-04-24T10:00:00.000+00:00",
        }
        (session_dir / "metadata.json").write_text(_json.dumps(metadata))

        events = "\n".join(
            [
                _json.dumps(
                    {
                        "event": "session:start",
                        "ts": "2026-04-24T10:00:00.000+00:00",
                        "data": {"session_id": session_id},
                    }
                ),
                _json.dumps(
                    {
                        "event": "session:end",
                        "ts": "2026-04-24T10:00:30.000+00:00",
                        "data": {},
                    }
                ),
            ]
        )
        (session_dir / "events.jsonl").write_text(events)

        sessions = discover_sessions(amp_home)
        assert session_id in sessions
        assert sessions[session_id].project_slug == project


# ---------------------------------------------------------------------------
# TestEventsOnlyStubSessions (task-fix TDD RED)
# ---------------------------------------------------------------------------


def test_events_only_session_becomes_stub(tmp_path):
    """Sessions with events.jsonl but no metadata.json become stub nodes."""
    amp_home = tmp_path / ".amplifier"
    # Create parent session (events only, no metadata)
    parent_dir = amp_home / "projects" / "test-proj" / "sessions" / "parent-uuid-123"
    parent_dir.mkdir(parents=True)
    (parent_dir / "events.jsonl").write_text(
        '{"ts":"2026-01-01T00:00:00Z","event":"session:start","session_id":"parent-uuid-123"}\n'
    )
    # Create child session WITH metadata pointing to parent
    child_dir = amp_home / "projects" / "test-proj" / "sessions" / "child-abc"
    child_dir.mkdir(parents=True)
    (child_dir / "metadata.json").write_text(
        json.dumps(
            {
                "session_id": "child-abc",
                "parent_id": "parent-uuid-123",
                "created": "2026-01-01T00:01:00Z",
            }
        )
    )
    (child_dir / "events.jsonl").write_text(
        '{"ts":"2026-01-01T00:01:00Z","event":"session:fork","session_id":"child-abc","data":{"parent_id":"parent-uuid-123"}}\n'
    )
    sessions = discover_sessions(amp_home)
    assert "parent-uuid-123" in sessions, "events-only parent must be in sessions dict"
    assert "child-abc" in sessions
    roots = build_tree(sessions)
    root_ids = [r.session_id for r in roots]
    assert "parent-uuid-123" in root_ids, "parent should be root"
    assert "child-abc" not in root_ids, "child should NOT be root"
    # Verify child is linked to parent
    parent_node = next(r for r in roots if r.session_id == "parent-uuid-123")
    assert len(parent_node.children) == 1
    assert parent_node.children[0].session_id == "child-abc"


def test_both_parent_id_keys_accepted(tmp_path):
    """parent_session_id (old format) and parent_id (new format) both work."""
    amp_home = tmp_path / ".amplifier"
    # Old format: parent_session_id
    s_dir = amp_home / "projects" / "p" / "sessions" / "child-old"
    s_dir.mkdir(parents=True)
    (s_dir / "metadata.json").write_text(
        json.dumps(
            {
                "session_id": "child-old",
                "parent_session_id": "root-abc",
                "created": "2026-01-01T00:00:00Z",
            }
        )
    )
    (s_dir / "events.jsonl").write_text(
        '{"ts":"2026-01-01T00:00:00Z","event":"session:start","session_id":"child-old"}\n'
    )
    sessions = discover_sessions(amp_home)
    assert sessions["child-old"].parent_id == "root-abc"


def test_observability_costs_loaded(tmp_path):
    """Pre-computed costs from observability JSONL enrich the session list."""
    amp_home = tmp_path / ".amplifier"
    s_dir = amp_home / "projects" / "p" / "sessions" / "sess-abc"
    s_dir.mkdir(parents=True)
    (s_dir / "metadata.json").write_text(
        json.dumps({"session_id": "sess-abc", "created": "2026-01-01T00:00:00Z"})
    )
    (s_dir / "events.jsonl").write_text(
        '{"ts":"2026-01-01T00:00:00Z","event":"session:start","session_id":"sess-abc"}\n'
    )
    obs_dir = amp_home / "observability"
    obs_dir.mkdir()
    (obs_dir / "sess-abc.jsonl").write_text(
        json.dumps(
            {
                "type": "session_summary",
                "session_id": "sess-abc",
                "total_cost_usd": 1.2345,
            }
        )
        + "\n"
    )
    roots = build_session_tree(amp_home)
    node = next(r for r in roots if r.session_id == "sess-abc")
    assert abs(node.total_cost_usd - 1.2345) < 0.0001


# ---------------------------------------------------------------------------
# Performance fix tests (perf-fix TDD RED)
# ---------------------------------------------------------------------------


def test_normalize_timestamps_stops_at_first_event(tmp_path):
    """normalize_timestamps reads only until session:start — does not read entire file."""
    events_path = tmp_path / "events.jsonl"
    # session:start is first, followed by many events
    lines = [
        json.dumps(
            {"ts": "2026-01-01T00:00:00Z", "event": "session:start", "session_id": "x"}
        ),
    ]
    # Add 1000 more lines to prove we don't need to read them
    lines += [
        json.dumps({"ts": "2026-01-01T00:00:01Z", "event": "other"})
        for _ in range(1000)
    ]
    events_path.write_text("\n".join(lines))

    # Should return the timestamp from line 1 correctly
    ms = normalize_timestamps(events_path)
    assert ms == int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)


def test_read_metadata_partial_extracts_fields(tmp_path):
    """_read_metadata_partial extracts fields from truncated large metadata."""
    import json as _json

    from amplifier_app_cost_viewer.reader import _read_metadata_partial

    # Simulate a large metadata.json: small fields first, then huge config
    metadata_path = tmp_path / "metadata.json"
    obj = {
        "session_id": "abc-123",
        "parent_id": None,
        "created": "2026-01-01T00:00:00Z",
        "name": "Test Session",
        "project_slug": "my-project",
        "config": {"x": "a" * 5000},  # Makes file > 4096 bytes
    }
    metadata_path.write_text(_json.dumps(obj))

    result = _read_metadata_partial(metadata_path)
    assert result["session_id"] == "abc-123"
    assert result["name"] == "Test Session"
    assert result["created"] == "2026-01-01T00:00:00Z"


def test_aggregate_costs_rolls_up_tokens():
    """aggregate_costs must propagate input/output tokens from children to parent."""
    from amplifier_app_cost_viewer.reader import SessionNode, aggregate_costs

    def _node(sid, parent_id=None):
        return SessionNode(
            session_id=sid,
            project_slug="x",
            parent_id=parent_id,
            start_ts="",
            end_ts=None,
            duration_ms=0,
            cost_usd=0.0,
            total_cost_usd=0.0,
            spans=[],
            children=[],
        )

    parent = _node("p")
    child1 = _node("c1", parent_id="p")
    child2 = _node("c2", parent_id="p")
    child1.total_input_tokens = 1000
    child1.total_output_tokens = 200
    child2.total_input_tokens = 500
    child2.total_output_tokens = 100
    parent.children = [child1, child2]
    aggregate_costs(parent)
    assert parent.total_input_tokens == 1500
    assert parent.total_output_tokens == 300


def test_name_in_session_node(tmp_path):
    """SessionNode.name is populated from metadata.json."""
    amp_home = tmp_path / ".amplifier"
    s_dir = amp_home / "projects" / "proj" / "sessions" / "uuid-named"
    s_dir.mkdir(parents=True)
    (s_dir / "metadata.json").write_text(
        json.dumps(
            {
                "session_id": "uuid-named",
                "created": "2026-01-01T00:00:00Z",
                "name": "My Test Session",
            }
        )
    )
    (s_dir / "events.jsonl").write_text(
        '{"ts":"2026-01-01T00:00:00Z","event":"session:start","session_id":"uuid-named"}\n'
    )
    sessions = discover_sessions(amp_home)
    assert sessions["uuid-named"].name == "My Test Session"
