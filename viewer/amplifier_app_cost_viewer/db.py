"""SQLite reader for the Rust scanner's summaries.db.

Provides read-only access to pre-computed session cost summaries produced
by the ``amplifier-cost-scan`` binary.  Opens in WAL read-only mode so the
Python viewer never interferes with the scanner's incremental writes.

Schema (from scanner/src/db.rs):
    session_summaries (
        session_id    TEXT    PRIMARY KEY,
        cost_usd      REAL,
        input_tokens  INTEGER,
        output_tokens INTEGER,
        cache_read    INTEGER,
        cache_write   INTEGER,
        last_offset   INTEGER,
        is_complete   INTEGER,
        updated_at    REAL
    )
"""

from __future__ import annotations

import sqlite3
from pathlib import Path


def load_all(db_path: Path) -> dict[str, dict]:
    """Return all rows from ``session_summaries`` keyed by ``session_id``.

    Returns an empty dict when:
    - The DB file does not exist (scanner hasn't run yet).
    - Any SQLite or OS error occurs (e.g. file locked, permissions).

    Opens the DB via the SQLite URI API in read-only mode (``?mode=ro``) so
    the WAL writer lock held by the scanner is never contested.
    """
    if not db_path.exists():
        return {}

    try:
        uri = f"file:{db_path}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=2.0)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                "SELECT session_id, cost_usd, input_tokens, output_tokens,"
                "       cache_read, cache_write, is_complete"
                "  FROM session_summaries"
            ).fetchall()
            return {
                row["session_id"]: {
                    "cost_usd": float(row["cost_usd"]),
                    "input_tokens": int(row["input_tokens"]),
                    "output_tokens": int(row["output_tokens"]),
                    "cache_read": int(row["cache_read"]),
                    "cache_write": int(row["cache_write"]),
                    "is_complete": bool(row["is_complete"]),
                }
                for row in rows
            }
        finally:
            conn.close()
    except (sqlite3.Error, OSError):
        return {}
