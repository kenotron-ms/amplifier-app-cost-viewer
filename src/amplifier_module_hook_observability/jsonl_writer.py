"""JSONL file writer -- one file per session."""

from __future__ import annotations

import json
import pathlib
from datetime import datetime, timezone
from typing import Any

_FALLBACK = "unknown-session"


class JSONLWriter:
    """Appends observability records to a per-session JSONL file.

    File name: <output_dir>/<session_id>.jsonl
    All records for a session are co-located, making it trivial to
    correlate the log with a specific Amplifier session ID.
    """

    def __init__(self, output_dir: str) -> None:
        self._output_dir = pathlib.Path(output_dir).expanduser().resolve()
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def write(self, record: dict[str, Any]) -> None:
        """Append one JSON record (with timestamp) to this session's JSONL file."""
        sid = record.get("session_id") or _FALLBACK
        path = self._output_dir / f"{sid}.jsonl"
        payload: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            **record,
        }
        line = json.dumps(payload, separators=(",", ":"))
        with path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
