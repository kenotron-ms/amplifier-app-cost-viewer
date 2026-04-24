"""Tests for JSONLWriter."""

from __future__ import annotations

import json

import pytest

from amplifier_module_hook_observability.jsonl_writer import JSONLWriter


@pytest.fixture
def writer(tmp_path):
    return JSONLWriter(str(tmp_path))


class TestJSONLWriter:
    def test_write_creates_file(self, writer, tmp_path):
        writer.write({"type": "provider_call", "session_id": "sess-1"})
        assert (tmp_path / "sess-1.jsonl").exists()

    def test_write_appends_records(self, writer, tmp_path):
        writer.write({"type": "provider_call", "session_id": "sess-1", "n": 1})
        writer.write({"type": "provider_call", "session_id": "sess-1", "n": 2})
        lines = (tmp_path / "sess-1.jsonl").read_text().strip().splitlines()
        assert len(lines) == 2
        assert json.loads(lines[0])["n"] == 1
        assert json.loads(lines[1])["n"] == 2

    def test_write_includes_timestamp(self, writer, tmp_path):
        writer.write({"type": "provider_call", "session_id": "sess-1"})
        record = json.loads((tmp_path / "sess-1.jsonl").read_text())
        assert "ts" in record
        # ISO 8601 format: date T time + timezone indicator
        ts = record["ts"]
        assert "T" in ts
        assert ts.endswith("Z") or "+00:00" in ts

    def test_write_unknown_session_fallback(self, writer, tmp_path):
        writer.write({"type": "session_summary"})
        assert (tmp_path / "unknown-session.jsonl").exists()

    def test_write_passes_through_extra_fields(self, writer, tmp_path):
        writer.write(
            {
                "type": "session_summary",
                "session_id": "sess-1",
                "parent_session_id": "parent-123",
                "total_cost_usd": 0.042,
            }
        )
        record = json.loads((tmp_path / "sess-1.jsonl").read_text())
        assert record["parent_session_id"] == "parent-123"
        assert record["total_cost_usd"] == 0.042

    def test_write_multiple_sessions_separate_files(self, writer, tmp_path):
        writer.write({"type": "provider_call", "session_id": "sess-a"})
        writer.write({"type": "provider_call", "session_id": "sess-b"})
        assert (tmp_path / "sess-a.jsonl").exists()
        assert (tmp_path / "sess-b.jsonl").exists()
        assert (
            not (tmp_path / "sess-a.jsonl").read_text()
            == (tmp_path / "sess-b.jsonl").read_text()
        )

    def test_output_dir_created_if_missing(self, tmp_path):
        new_dir = tmp_path / "deep" / "nested"
        w = JSONLWriter(str(new_dir))
        w.write({"type": "test", "session_id": "x"})
        assert new_dir.exists()
