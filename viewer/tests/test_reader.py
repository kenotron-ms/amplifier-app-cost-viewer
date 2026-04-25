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


def _get_spans(tmp_path: Path, content: str = SYNTHETIC_EVENTS) -> list[dict]:
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
