"""Reader module: event log parsing, span extraction, and session building."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from amplifier_app_cost_viewer.pricing import (
    THINKING_COLOR,
    TOOL_COLOR,
    UNKNOWN_COLOR,
    compute_cost,
    get_model_color,
)

__all__ = [
    "Span",
    "SessionNode",
    "normalize_timestamps",
    "parse_spans",
    "discover_sessions",
    "build_tree",
    "aggregate_costs",
    "build_session_tree",
    "THINKING_COLOR",
    "TOOL_COLOR",
    "UNKNOWN_COLOR",
]


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class Span:
    """A single observable event interval extracted from an event log."""

    type: str  # 'llm' | 'tool' | 'thinking'
    start_ms: int
    end_ms: int
    provider: str | None
    model: str | None
    cost_usd: float
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_write_tokens: int
    tool_name: str | None
    success: bool | None
    input: Any | None
    output: Any | None
    color: str

    def __getitem__(self, key: str) -> Any:
        """Allow dict-style field access: span["type"]."""
        return getattr(self, key)


@dataclass
class SessionNode:
    """A single Amplifier session with its spans and child sessions."""

    session_id: str
    project_slug: str
    parent_id: str | None
    start_ts: str
    end_ts: str | None
    duration_ms: int
    cost_usd: float
    total_cost_usd: float
    spans: list[Span]
    children: list[SessionNode]
    events_path: Path | None = field(default=None, compare=False, repr=False)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _ts_to_ms(ts_str: str) -> int:
    """Parse ISO 8601 timestamp string to Unix milliseconds."""
    dt = datetime.fromisoformat(ts_str)
    return int(dt.timestamp() * 1000)


def _offset_ms(ts_str: str, root_start_ms: int) -> int:
    """Return millisecond offset of ts_str relative to root_start_ms."""
    return _ts_to_ms(ts_str) - root_start_ms


def _read_events(events_path: Path) -> list[dict]:
    """Read all valid JSON lines from events_path.

    Skips blank lines and lines with invalid JSON.  Catches OSError so callers
    get an empty list when the file is missing or unreadable.
    """
    events: list[dict] = []
    try:
        for line in events_path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    except OSError:
        pass
    return events


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def normalize_timestamps(events_path: Path) -> int:
    """Return Unix milliseconds of the first ``session:start`` event.

    Raises:
        ValueError: if no ``session:start`` event is found.
    """
    events = _read_events(events_path)
    for event in events:
        if event.get("event") == "session:start":
            return _ts_to_ms(event["ts"])
    raise ValueError(f"No session:start event found in {events_path}")


def parse_spans(
    events_path: Path,
    root_start_ms: int,
    session_start_ms: int | None = None,
) -> list[Span]:
    """Parse an event log into a sorted list of :class:`Span` objects.

    Pairing rules:

    - **LLM**: ``provider:request`` → ``llm:response`` (sequential zip).
      Provider comes from the request event; model and usage come from the
      response event.  Cost is computed via :func:`compute_cost`; color via
      :func:`get_model_color`.

    - **Tool**: ``tool:pre`` → ``tool:post`` matched by ``data.tool_call_id``.
      Unpaired ``tool:pre`` events are silently dropped.

    - **Thinking**: first ``thinking:delta`` → first ``thinking:final``
      (sequential zip).

    Args:
        events_path: Path to the JSONL event log.
        root_start_ms: Unix ms used as the time origin for offset calculation.
        session_start_ms: Session start time (defaults to *root_start_ms*
            when not supplied).

    Returns:
        List of :class:`Span` objects sorted ascending by ``start_ms``.
    """
    if session_start_ms is None:
        session_start_ms = root_start_ms

    events = _read_events(events_path)
    spans: list[Span] = []

    # ------------------------------------------------------------------
    # LLM spans: provider:request → llm:response (sequential zip)
    # ------------------------------------------------------------------
    provider_requests = [e for e in events if e.get("event") == "provider:request"]
    llm_responses = [e for e in events if e.get("event") == "llm:response"]

    for req, resp in zip(provider_requests, llm_responses):
        req_data = req.get("data", {})
        resp_data = resp.get("data", {})
        usage = resp_data.get("usage", {})

        provider = req_data.get("provider")
        model = resp_data.get("model", "")
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        cache_read_tokens = usage.get("cache_read_tokens", 0)
        cache_write_tokens = usage.get("cache_write_tokens", 0)

        cost = compute_cost(
            model,
            input_tokens,
            output_tokens,
            cache_read_tokens,
            cache_write_tokens,
        )
        color = get_model_color(model, provider or "")

        spans.append(
            Span(
                type="llm",
                start_ms=_offset_ms(req["ts"], root_start_ms),
                end_ms=_offset_ms(resp["ts"], root_start_ms),
                provider=provider,
                model=model,
                cost_usd=cost,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cache_read_tokens=cache_read_tokens,
                cache_write_tokens=cache_write_tokens,
                tool_name=None,
                success=None,
                input=req_data,
                output=resp_data,
                color=color,
            )
        )

    # ------------------------------------------------------------------
    # Tool spans: tool:pre → tool:post matched by tool_call_id
    # ------------------------------------------------------------------
    tool_pre_by_id: dict[str, dict] = {}

    for event in events:
        ev = event.get("event")
        if ev == "tool:pre":
            tool_call_id = event.get("data", {}).get("tool_call_id")
            if tool_call_id is not None:
                tool_pre_by_id[tool_call_id] = event
        elif ev == "tool:post":
            post_data = event.get("data", {})
            tool_call_id = post_data.get("tool_call_id")
            if tool_call_id is None or tool_call_id not in tool_pre_by_id:
                # No matching pre — silently drop
                continue

            pre_event = tool_pre_by_id[tool_call_id]
            pre_data = pre_event.get("data", {})

            spans.append(
                Span(
                    type="tool",
                    start_ms=_offset_ms(pre_event["ts"], root_start_ms),
                    end_ms=_offset_ms(event["ts"], root_start_ms),
                    provider=None,
                    model=None,
                    cost_usd=0.0,
                    input_tokens=0,
                    output_tokens=0,
                    cache_read_tokens=0,
                    cache_write_tokens=0,
                    tool_name=pre_data.get("tool_name"),
                    success=post_data.get("success"),
                    input=pre_data,
                    output=post_data,
                    color=TOOL_COLOR,
                )
            )

    # ------------------------------------------------------------------
    # Thinking spans: thinking:delta → thinking:final (sequential zip)
    # ------------------------------------------------------------------
    thinking_deltas = [e for e in events if e.get("event") == "thinking:delta"]
    thinking_finals = [e for e in events if e.get("event") == "thinking:final"]

    for delta, final in zip(thinking_deltas, thinking_finals):
        spans.append(
            Span(
                type="thinking",
                start_ms=_offset_ms(delta["ts"], root_start_ms),
                end_ms=_offset_ms(final["ts"], root_start_ms),
                provider=None,
                model=None,
                cost_usd=0.0,
                input_tokens=0,
                output_tokens=0,
                cache_read_tokens=0,
                cache_write_tokens=0,
                tool_name=None,
                success=None,
                input=delta.get("data"),
                output=final.get("data"),
                color=THINKING_COLOR,
            )
        )

    return sorted(spans, key=lambda s: s.start_ms)


# ---------------------------------------------------------------------------
# Stub functions — implemented in Task 12
# ---------------------------------------------------------------------------


def discover_sessions(amp_home: Path) -> dict[str, "SessionNode"]:
    """Discover all sessions under amp_home/projects/*/sessions/.

    Returns a flat dict mapping session_id → SessionNode.
    """
    raise NotImplementedError


def build_tree(sessions: dict[str, "SessionNode"]) -> list["SessionNode"]:
    """Arrange flat sessions dict into a forest (list of root SessionNodes)."""
    raise NotImplementedError


def aggregate_costs(node: "SessionNode") -> None:
    """Recursively set total_cost_usd = cost_usd + sum of children totals."""
    raise NotImplementedError


def build_session_tree(amp_home: Path) -> list["SessionNode"]:
    """Discover sessions, build tree, parse spans, aggregate costs.

    Returns root SessionNodes sorted most-recent first.
    """
    raise NotImplementedError
