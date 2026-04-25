"""conftest.py — shared fixtures and helpers for test_reader.py tree-building tests."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ROOT_SESSION_ID = "root-aabbccdd"
ROOT2_SESSION_ID = "root2-eeffgghh"
CHILD1_SESSION_ID = "child1-11223344"
CHILD2_SESSION_ID = "child2-55667788"
PROJECT_SLUG = "test-project"
ROOT_START_ISO = "2026-04-24T10:00:00.000+00:00"
ROOT2_START_ISO = "2026-04-24T11:00:00.000+00:00"
CHILD1_START_ISO = "2026-04-24T10:00:05.000+00:00"
CHILD2_START_ISO = "2026-04-24T10:00:15.000+00:00"
COST_PER_SESSION = 0.003456  # 512 * 3e-6 + 128 * 15e-6


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _iso_plus(start_iso: str, offset_s: float) -> str:
    """Return ISO timestamp offset_s seconds after start_iso."""
    dt = datetime.fromisoformat(start_iso)
    dt2 = dt + timedelta(seconds=offset_s)
    total_ms = int(round(dt2.timestamp() * 1000))
    ms = total_ms % 1000
    return dt2.strftime("%Y-%m-%dT%H:%M:%S.") + f"{ms:03d}+00:00"


def _session_events_jsonl(
    session_id: str,
    start_iso: str,
    parent_id: str | None = None,
) -> str:
    """Generate events.jsonl content for a synthetic session.

    Produces four events:
      - session:start
      - provider:request (1 s after start)
      - llm:response     (6 s after start; 512 in / 128 out, claude-sonnet-4-5)
      - session:end      (30 s after start)
    """
    events = [
        {
            "event": "session:start",
            "ts": start_iso,
            "data": {"session_id": session_id},
        },
        {
            "event": "provider:request",
            "ts": _iso_plus(start_iso, 1),
            "data": {"provider": "anthropic"},
        },
        {
            "event": "llm:response",
            "ts": _iso_plus(start_iso, 6),
            "data": {
                "model": "claude-sonnet-4-5",
                "duration_ms": 5000,
                "usage": {
                    "input_tokens": 512,
                    "output_tokens": 128,
                    "cache_read_tokens": 0,
                    "cache_write_tokens": 0,
                },
            },
        },
        {
            "event": "session:end",
            "ts": _iso_plus(start_iso, 30),
            "data": {},
        },
    ]
    return "\n".join(json.dumps(e) for e in events)


def _session_metadata(
    session_id: str,
    parent_id: str | None,
    project_slug: str,
    created: str,
) -> str:
    """Generate metadata.json content for a synthetic session."""
    return json.dumps(
        {
            "session_id": session_id,
            "parent_id": parent_id,
            "project_slug": project_slug,
            "created": created,
        }
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def amp_home(tmp_path: Path) -> Path:
    """Create a fake ~/.amplifier with 4 sessions (2 roots + 2 children of root1).

    Layout:
        <tmp_path>/.amplifier/
            projects/
                test-project/
                    sessions/
                        root-aabbccdd/      ← root1 (older, has 2 children)
                            events.jsonl
                            metadata.json
                        child1-11223344/
                            events.jsonl
                            metadata.json
                        child2-55667788/
                            events.jsonl
                            metadata.json
                        root2-eeffgghh/     ← root2 (newer, no children)
                            events.jsonl
                            metadata.json
    """
    base = tmp_path / ".amplifier"
    sessions_dir = base / "projects" / PROJECT_SLUG / "sessions"
    sessions_dir.mkdir(parents=True)

    session_specs = [
        (ROOT_SESSION_ID, ROOT_START_ISO, None),
        (CHILD1_SESSION_ID, CHILD1_START_ISO, ROOT_SESSION_ID),
        (CHILD2_SESSION_ID, CHILD2_START_ISO, ROOT_SESSION_ID),
        (ROOT2_SESSION_ID, ROOT2_START_ISO, None),
    ]

    for session_id, start_iso, parent_id in session_specs:
        session_dir = sessions_dir / session_id
        session_dir.mkdir()
        (session_dir / "events.jsonl").write_text(
            _session_events_jsonl(session_id, start_iso, parent_id)
        )
        (session_dir / "metadata.json").write_text(
            _session_metadata(session_id, parent_id, PROJECT_SLUG, start_iso)
        )

    return base
