"""JSONL file writer -- one file per day, append-only."""

from __future__ import annotations

import json
import pathlib
from datetime import datetime, timezone
from typing import Any


class JSONLWriter:
    """Appends observability records to a daily-rotating JSONL file."""

    def __init__(self, output_dir: str) -> None:
        self._output_dir = pathlib.Path(output_dir).expanduser().resolve()
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def write(self, record: dict[str, Any]) -> None:
        """Append one JSON record (with timestamp) to today's JSONL file."""
        now = datetime.now(timezone.utc)
        date_str = now.strftime("%Y-%m-%d")
        path = self._output_dir / f"{date_str}.jsonl"
        payload: dict[str, Any] = {"ts": now.isoformat(), **record}
        line = json.dumps(payload, separators=(",", ":"))
        with path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
