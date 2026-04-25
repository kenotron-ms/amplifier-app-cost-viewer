"""FastAPI backend for the Amplifier App Cost Viewer — 4 routes with in-memory cache."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

import amplifier_app_cost_viewer.reader as _reader
from amplifier_app_cost_viewer.reader import (
    SessionNode,
    Span,
    aggregate_costs,
    build_session_tree,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

AMPLIFIER_HOME: Path = Path(
    os.environ.get("AMPLIFIER_HOME", str(Path.home() / ".amplifier"))
)

# ---------------------------------------------------------------------------
# In-memory caches
# ---------------------------------------------------------------------------

_roots_cache: list[SessionNode] | None = None
_loaded_cache: dict[str, SessionNode] = {}  # session_id → fully loaded root node

# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(title="Amplifier Cost Viewer", version="0.1.0")

# Conditionally mount static files when the directory exists
_static_dir = Path(__file__).parent / "static"
if _static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/")
def root() -> RedirectResponse:
    """Redirect to the static SPA root."""
    return RedirectResponse(url="/static/index.html")


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------


def _span_to_dict(span: Span, session_id: str, depth: int) -> dict[str, Any]:
    """Serialize a Span to a plain dict suitable for JSON responses."""
    return {
        "session_id": session_id,
        "depth": depth,
        "type": span.type,
        "start_ms": span.start_ms,
        "end_ms": span.end_ms,
        "provider": span.provider,
        "model": span.model,
        "cost_usd": span.cost_usd,
        "input_tokens": span.input_tokens,
        "output_tokens": span.output_tokens,
        "cache_read_tokens": span.cache_read_tokens,
        "cache_write_tokens": span.cache_write_tokens,
        "tool_name": span.tool_name,
        "success": span.success,
        "input": span.input,
        "output": span.output,
        "color": span.color,
    }


def _node_to_dict(node: SessionNode, include_spans: bool = False) -> dict[str, Any]:
    """Serialize a SessionNode to a plain dict.

    When include_spans=True also includes the node's spans list and a
    recursive children list.
    """
    d: dict[str, Any] = {
        "session_id": node.session_id,
        "project_slug": node.project_slug,
        "parent_id": node.parent_id,
        "name": node.name,
        "start_ts": node.start_ts,
        "end_ts": node.end_ts,
        "duration_ms": node.duration_ms,
        "cost_usd": node.cost_usd,
        "total_cost_usd": node.total_cost_usd,
        "child_count": len(node.children),
    }
    if include_spans:
        d["spans"] = [_span_to_dict(s, node.session_id, 0) for s in node.spans]
        d["children"] = [
            _node_to_dict(child, include_spans=True) for child in node.children
        ]
    return d


def _flatten_spans(node: SessionNode, depth: int = 0) -> list[dict[str, Any]]:
    """Return all spans from node and all descendants, annotated with depth."""
    result: list[dict[str, Any]] = [
        _span_to_dict(s, node.session_id, depth) for s in node.spans
    ]
    for child in node.children:
        result.extend(_flatten_spans(child, depth + 1))
    return result


# ---------------------------------------------------------------------------
# Cache management
# ---------------------------------------------------------------------------


def _get_roots(force: bool = False) -> list[SessionNode]:
    """Return cached root sessions, populating from disk on first call."""
    global _roots_cache
    if _roots_cache is None or force:
        _roots_cache = build_session_tree(AMPLIFIER_HOME)
    return _roots_cache


def _find_root(session_id: str) -> SessionNode | None:
    """Linear search over roots for the node with matching session_id."""
    for root in _get_roots():
        if root.session_id == session_id:
            return root
    return None


def _parse_all_spans_for_node(node: SessionNode, root_start_ms: int) -> None:
    """Recursively load spans for node and all descendants.

    Uses _reader.parse_spans / _reader.normalize_timestamps via module access
    so that test monkeypatching of reader_mod.parse_spans is respected.
    """
    if node.events_path and node.events_path.exists():
        try:
            session_start_ms = _reader.normalize_timestamps(node.events_path)
            node.spans = _reader.parse_spans(
                node.events_path, root_start_ms, session_start_ms
            )
            node.cost_usd = sum(s.cost_usd for s in node.spans)
        except (ValueError, OSError):
            pass
    for child in node.children:
        _parse_all_spans_for_node(child, root_start_ms)
    aggregate_costs(node)


def _load_session(session_id: str) -> SessionNode | None:
    """Return a fully span-loaded root node, using the cache where possible.

    1. Finds the root node for session_id.
    2. Returns cached loaded node if already in _loaded_cache.
    3. Otherwise calls parse_spans for the root and all descendants,
       stores the result in _loaded_cache, and returns it.
    """
    global _loaded_cache
    root = _find_root(session_id)
    if root is None:
        return None
    if root.session_id in _loaded_cache:
        return _loaded_cache[root.session_id]
    # Compute root_start_ms from the root's events file
    if root.events_path and root.events_path.exists():
        try:
            root_start_ms = _reader.normalize_timestamps(root.events_path)
        except (ValueError, OSError):
            root_start_ms = 0
    else:
        root_start_ms = 0
    _parse_all_spans_for_node(root, root_start_ms)
    _loaded_cache[root.session_id] = root
    return root


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------


@app.post("/api/refresh")
def refresh_sessions() -> dict:
    """Clear the in-memory session cache, forcing a rescan on next request."""
    global _roots_cache, _loaded_cache
    _roots_cache = None
    _loaded_cache = {}
    return {"ok": True}


@app.get("/api/sessions")
def list_sessions(
    limit: int = Query(default=25, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict:
    """Return paginated root sessions (parent_id is None) sorted by recency.

    Only sessions with no parent are shown — child/delegate sessions are
    intentionally excluded.
    """
    roots = _get_roots()
    true_roots = [r for r in roots if r.parent_id is None]
    total = len(true_roots)
    page = true_roots[offset : offset + limit]
    return {
        "sessions": [_node_to_dict(r, include_spans=False) for r in page],
        "total": total,
        "has_more": (offset + limit) < total,
        "next_offset": offset + limit,
    }


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str) -> dict:
    """Return the full session tree for session_id, including spans and children."""
    root = _load_session(session_id)
    if root is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return _node_to_dict(root, include_spans=True)


@app.get("/api/sessions/{session_id}/spans")
def get_session_spans(session_id: str) -> list[dict]:
    """Return flattened spans from session_id and all descendants, with depth."""
    root = _load_session(session_id)
    if root is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return _flatten_spans(root, depth=0)
