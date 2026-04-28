"""FastAPI backend for the Amplifier App Cost Viewer — 4 routes with in-memory cache."""

from __future__ import annotations

import os
import threading
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
_roots_lock = threading.Lock()  # prevents concurrent tree builds (prewarm + request)

# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(title="Amplifier Cost Viewer", version="0.1.0")


def _iter_nodes(root: SessionNode):
    """Yield every node in the session tree rooted at *root* (DFS pre-order)."""
    yield root
    for child in root.children:
        yield from _iter_nodes(child)


@app.on_event("startup")
async def _prewarm_cache() -> None:
    """Build the session cache in the background at startup.

    Prevents the first /api/sessions request from blocking while
    scanning thousands of session directories.
    """
    import asyncio

    asyncio.create_task(asyncio.to_thread(_get_roots))


@app.on_event("startup")
async def _auto_refresh_live_sessions() -> None:
    """Periodically invalidate the roots cache while any session is still live.

    Live sessions gain new child summaries as sub-agents complete. Without
    periodic refresh, the viewer shows stale token/cost counts until the user
    manually hits refresh.
    """
    import asyncio

    async def _refresh_loop() -> None:
        while True:
            await asyncio.sleep(60)
            global _roots_cache, _loaded_cache
            # Only refresh if there are live sessions (no end_ts)
            if _roots_cache is not None:
                has_live = any(
                    not node.end_ts
                    for root in _roots_cache
                    for node in _iter_nodes(root)
                )
                if has_live:
                    _roots_cache = None
                    _loaded_cache = {}

    asyncio.create_task(_refresh_loop())


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
        "total_input_tokens": node.total_input_tokens,
        "total_output_tokens": node.total_output_tokens,
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
    """Return cached root sessions, populating from disk on first call.

    Thread-safe: the lock prevents the prewarm background task and a
    concurrent request handler from both running build_session_tree at once.
    """
    global _roots_cache
    with _roots_lock:
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
            node.total_input_tokens = sum(s.input_tokens for s in node.spans)
            node.total_output_tokens = sum(s.output_tokens for s in node.spans)
        except (ValueError, OSError):
            pass
    for child in node.children:
        _parse_all_spans_for_node(child, root_start_ms)
    aggregate_costs(node)


def _find_node(root: SessionNode, session_id: str) -> SessionNode | None:
    """DFS search for a node by session_id."""
    if root.session_id == session_id:
        return root
    for child in root.children:
        result = _find_node(child, session_id)
        if result is not None:
            return result
    return None


def _get_root_start_ms(root: SessionNode) -> int:
    """Get Unix ms for the root session's start event."""
    if root.events_path and root.events_path.exists():
        try:
            return _reader.normalize_timestamps(root.events_path)
        except (ValueError, OSError):
            pass
    return 0


def _load_session(session_id: str, only_root: bool = False) -> SessionNode | None:
    """Return a span-loaded root node, using the cache where possible.

    When only_root=False (default):
      1. Returns cached fully-loaded node if present.
      2. Otherwise parses all spans recursively, caches, and returns.

    When only_root=True (fast path for first paint):
      1. Returns cached node if already fully loaded.
      2. Otherwise parses ONLY the root node's own spans (skipping children).
         The partial result is NOT cached, so a subsequent full load works correctly.
    """
    global _loaded_cache
    root = _find_root(session_id)
    if root is None:
        return None

    # If a full load is already cached, return it (serves both only_root cases)
    if root.session_id in _loaded_cache:
        return _loaded_cache[root.session_id]

    root_start_ms = _get_root_start_ms(root)

    if only_root:
        # Fast path: parse only the root node's own events file
        if root.events_path and root.events_path.exists():
            try:
                root.spans = _reader.parse_spans(
                    root.events_path, root_start_ms, root_start_ms
                )
                root.cost_usd = sum(s.cost_usd for s in root.spans)
                root.total_input_tokens = sum(s.input_tokens for s in root.spans)
                root.total_output_tokens = sum(s.output_tokens for s in root.spans)
            except (ValueError, OSError):
                pass
        # Do NOT cache — children are still unloaded
        return root

    # Full load: parse all spans recursively, then cache
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
    # Only include sessions with metadata.json (start_ts != "").
    # Stub nodes (events-only, no metadata) exist solely to anchor their
    # children in the tree and should never appear in the user-facing list.
    true_roots = [r for r in roots if r.parent_id is None and r.start_ts]
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
def get_spans(session_id: str, only_root: bool = False) -> dict:
    """Return spans for a session tree.

    If only_root=true, only parses the root node's events.jsonl (fast path for
    first paint).  Child spans can be loaded separately via the child-spans
    endpoint.  Returns a dict with 'spans', 'partial', and 'session_id' keys.
    """
    root = _load_session(session_id, only_root=only_root)
    if root is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if only_root:
        spans_out: list[dict[str, Any]] = [
            _span_to_dict(s, root.session_id, 0) for s in root.spans
        ]
    else:
        spans_out = _flatten_spans(root, depth=0)
    return {"spans": spans_out, "partial": only_root, "session_id": session_id}


@app.get("/api/sessions/{session_id}/child-spans/{child_session_id}")
def get_child_spans(session_id: str, child_session_id: str) -> dict:
    """Return spans for one specific child session within a parent tree.

    Used for lazy loading: when the user expands a sub-session, fetch only that
    one child's spans rather than the entire tree.
    """
    root = _find_root(session_id)
    if root is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")

    # Find the child node anywhere in the tree
    child = _find_node(root, child_session_id)
    if child is None:
        raise HTTPException(
            status_code=404,
            detail=f"Child {child_session_id!r} not found in tree",
        )

    # Parse spans for this child (and its children) if not already cached
    if child.session_id not in _loaded_cache:
        root_start_ms = _get_root_start_ms(root)
        _parse_all_spans_for_node(child, root_start_ms)
        _loaded_cache[child.session_id] = child

    # Children of root are at depth=1; their children at depth=2, etc.
    spans_out = _flatten_spans(child, depth=1)
    return {"spans": spans_out, "session_id": child_session_id}


@app.get("/api/pricing")
def get_pricing() -> dict:
    """Return the static pricing table with rates in USD per million tokens."""
    from amplifier_app_cost_viewer import pricing as _p

    rates = {
        model: {
            "input":       round(entry.get("input_cost_per_token", 0)            * 1_000_000, 6),
            "output":      round(entry.get("output_cost_per_token", 0)           * 1_000_000, 6),
            "cache_read":  round(entry.get("cache_read_input_token_cost", 0)     * 1_000_000, 6),
            "cache_write": round(entry.get("cache_creation_input_token_cost", 0) * 1_000_000, 6),
        }
        for model, entry in _p.STATIC_PRICING.items()
    }
    return {"rates": rates}
