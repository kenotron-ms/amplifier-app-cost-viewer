"""FastAPI backend for the Amplifier App Cost Viewer — 4 routes with in-memory cache."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from amplifier_app_cost_viewer.reader import SessionNode, Span, build_session_tree

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

AMPLIFIER_HOME: Path = Path(
    os.environ.get("AMPLIFIER_HOME", str(Path.home() / ".amplifier"))
)

# ---------------------------------------------------------------------------
# In-memory cache
# ---------------------------------------------------------------------------

_roots_cache: list[SessionNode] | None = None

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


def _get_roots() -> list[SessionNode]:
    """Return cached root sessions, populating from disk on first call."""
    global _roots_cache
    if _roots_cache is None:
        _roots_cache = build_session_tree(AMPLIFIER_HOME)
    return _roots_cache


def _find_root(session_id: str) -> SessionNode | None:
    """Linear search over roots for the node with matching session_id."""
    for root in _get_roots():
        if root.session_id == session_id:
            return root
    return None


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------


@app.get("/api/sessions")
def list_sessions() -> list[dict]:
    """Return true root sessions (parent_id is None) as a summary list (no spans).

    Only sessions with no parent are shown.  Sessions whose parent_id is set
    but whose parent does not exist on disk are intentionally excluded — these
    are Amplifier child sessions (e.g. delegated sub-agents) whose root context
    is not stored locally and would show as empty/misleading entries.
    """
    roots = _get_roots()
    return [
        _node_to_dict(root, include_spans=False)
        for root in roots
        if root.parent_id is None
    ]


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str) -> dict:
    """Return the full session tree for session_id, including spans and children."""
    root = _find_root(session_id)
    if root is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return _node_to_dict(root, include_spans=True)


@app.get("/api/sessions/{session_id}/spans")
def get_session_spans(session_id: str) -> list[dict]:
    """Return flattened spans from session_id and all descendants, with depth."""
    root = _find_root(session_id)
    if root is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return _flatten_spans(root, depth=0)
