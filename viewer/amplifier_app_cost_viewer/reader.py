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
    name: str | None = None
    events_path: Path | None = field(default=None, compare=False, repr=False)
    total_input_tokens: int = 0
    total_output_tokens: int = 0


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


# KNOWN events that are large and never contribute to spans — skip them
_SKIP_EVENTS: frozenset[bytes] = frozenset(
    [
        b'"llm:request"',
        b'"session:resume"',
        b'"context:snapshot"',
    ]
)


def _read_events(events_path: Path) -> list[dict]:
    """Read events from a JSONL file, skipping large unused event types.

    Streams line-by-line so the entire file is never loaded into RAM.
    Lines containing known-useless event types (llm:request, session:resume,
    context:snapshot) are skipped BEFORE JSON parsing for maximum speed.
    """
    events: list[dict] = []
    try:
        with events_path.open("rb") as f:
            for raw in f:
                raw = raw.strip()
                if not raw:
                    continue
                # Cheap byte-level check before JSON parsing.
                # All skipped events are large and contribute nothing to spans.
                if any(skip in raw for skip in _SKIP_EVENTS):
                    continue
                try:
                    events.append(json.loads(raw))
                except json.JSONDecodeError:
                    continue
    except OSError:
        pass
    return events


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _read_metadata_partial(metadata_path: Path) -> dict:
    """Read only the first 4096 bytes of metadata.json to extract needed fields.

    metadata.json files are often 500KB+ because they contain the full agent
    config. We only need 5 scalar fields that always appear at the top.
    Reads ~4KB instead of ~533KB per file — 100x less I/O.
    """
    try:
        with metadata_path.open("rb") as f:
            chunk = f.read(4096).decode("utf-8", errors="replace")
        # Try to parse as complete JSON first (small files parse fine)
        # For large files, chunk will be truncated — json.loads will fail
        try:
            return json.loads(chunk)
        except json.JSONDecodeError:
            # File was truncated — extract needed fields via regex
            # This is safe because all needed fields appear before 'config'
            import re

            result: dict = {}
            for key in ("session_id", "parent_id", "created", "name", "project_slug"):
                m = re.search(
                    r'"' + key + r'"\s*:\s*("(?:[^"\\]|\\.)*"|null)',
                    chunk,
                )
                if m:
                    try:
                        result[key] = json.loads(m.group(1))
                    except json.JSONDecodeError:
                        pass
            return result
    except OSError:
        return {}


def _read_parent_from_events(events_path: Path) -> str | None:
    """Read parent_id from events.jsonl by scanning first 10 lines for session:fork.

    Returns the parent's session_id if found, None otherwise.  Reads at most
    10 lines so it is fast even for large files.
    """
    try:
        with events_path.open(encoding="utf-8") as f:
            for _ in range(10):
                line = f.readline()
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                    if event.get("event") == "session:fork":
                        data = event.get("data", {})
                        # Kernel emits parent_id in data for session:fork
                        return (
                            data.get("parent_id")
                            or data.get("parent_session_id")
                            or data.get("parent")
                        )
                except json.JSONDecodeError:
                    continue
    except OSError:
        pass
    return None


def normalize_timestamps(events_path: Path) -> int:
    """Return the Unix ms timestamp of the session:start event.

    Only reads until session:start is found — always the first event.
    Raises ValueError if no session:start found.
    """
    try:
        with events_path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                    if event.get("event") == "session:start":
                        return _ts_to_ms(event["ts"])
                except (json.JSONDecodeError, KeyError):
                    continue
    except OSError as e:
        raise ValueError(f"Cannot read {events_path}: {e}") from e
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

    # Pairing assumes strict request→response interleaving (sequential zip).
    # If counts diverge, the shorter list wins — unmatched events are silently
    # dropped.  This holds for the current Amplifier event schema; if the schema
    # adds a correlation ID to provider:request + llm:response in the future,
    # switch to ID-matched pairing for robustness.
    for req, resp in zip(provider_requests, llm_responses):
        req_data = req.get("data", {})
        resp_data = resp.get("data", {})
        usage = resp_data.get("usage", {})

        provider = req_data.get("provider")
        model = resp_data.get("model", "")
        # Support both long-form keys (input_tokens) and short-form keys (input)
        # — production Amplifier events use both formats.
        input_tokens = usage.get("input_tokens", usage.get("input", 0))
        output_tokens = usage.get("output_tokens", usage.get("output", 0))
        cache_read_tokens = usage.get("cache_read_tokens", usage.get("cache_read", 0))
        cache_write_tokens = usage.get(
            "cache_write_tokens", usage.get("cache_write", 0)
        )

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
# Session tree pipeline
# ---------------------------------------------------------------------------


def discover_sessions(amplifier_home: Path) -> dict[str, SessionNode]:
    """Discover all sessions under amplifier_home/projects/*/sessions/.

    Requires at least events.jsonl to be present in each session directory.
    Sessions that also have metadata.json become full nodes; sessions that have
    only events.jsonl become lightweight stub nodes (just enough to anchor
    their children in the tree).

    Returns:
        A flat dict mapping session_id → SessionNode.  Returns {} when
        the projects directory does not exist or no valid sessions are found.
    """
    sessions: dict[str, SessionNode] = {}

    projects_dir = amplifier_home / "projects"
    if not projects_dir.exists():
        return sessions

    for session_dir in projects_dir.glob("*/sessions/*/"):
        metadata_path = session_dir / "metadata.json"
        events_path = session_dir / "events.jsonl"

        if not events_path.exists():
            continue  # Need at least events.jsonl

        if metadata_path.exists():
            # Full session: read metadata only — no event parsing (fast path)
            try:
                metadata = _read_metadata_partial(metadata_path)
                session_id = metadata.get("session_id") or session_dir.name
                parent_id = metadata.get("parent_id") or metadata.get(
                    "parent_session_id"
                )  # None or str
                # project_slug: top-level (test/synthetic format), then
                # config.project_slug (child session format), then derive
                # from the project directory name (real root session format).
                project_slug = (
                    metadata.get("project_slug")
                    or metadata.get("config", {}).get("project_slug")
                    or session_dir.parent.parent.name
                )
                created = metadata.get("created", "")
                name = metadata.get("name")  # may be None

                # Duration and cost are 0.0 until spans are loaded lazily
                node = SessionNode(
                    session_id=session_id,
                    project_slug=project_slug,
                    parent_id=parent_id,
                    start_ts=created,
                    end_ts=None,
                    duration_ms=0,
                    cost_usd=0.0,
                    total_cost_usd=0.0,
                    spans=[],
                    children=[],
                    name=name,
                    events_path=events_path,
                )
                sessions[session_id] = node

            except (json.JSONDecodeError, OSError):
                continue

        else:
            # Stub session: events.jsonl only — create minimal node for tree anchoring
            session_id = session_dir.name
            if session_id in sessions:
                continue  # Already discovered via metadata path
            parent_id = _read_parent_from_events(events_path)
            project_slug = session_dir.parent.parent.name
            node = SessionNode(
                session_id=session_id,
                project_slug=project_slug,
                parent_id=parent_id,
                start_ts="",
                end_ts=None,
                duration_ms=0,
                cost_usd=0.0,
                total_cost_usd=0.0,
                spans=[],
                children=[],
                name=None,
                events_path=events_path,
            )
            sessions[session_id] = node

    return sessions


def build_tree(sessions: dict[str, SessionNode]) -> list[SessionNode]:
    """Arrange flat sessions dict into a forest (list of root SessionNodes).

    Links each node to its parent's children list when the parent is present
    in the sessions dict.

    Returns:
        List of root nodes — those whose parent_id is None or points to a
        session not in the dict.
    """
    for node in sessions.values():
        if node.parent_id is not None and node.parent_id in sessions:
            sessions[node.parent_id].children.append(node)

    return [
        node
        for node in sessions.values()
        if node.parent_id is None or node.parent_id not in sessions
    ]


def aggregate_costs(node: SessionNode) -> None:
    """Recursively set total_cost_usd = cost_usd + sum of children totals.

    Processes children depth-first so each child's total_cost_usd is correct
    before being summed into the parent.
    """
    for child in node.children:
        aggregate_costs(child)
    node.total_cost_usd = node.cost_usd + sum(
        child.total_cost_usd for child in node.children
    )
    node.total_input_tokens += sum(child.total_input_tokens for child in node.children)
    node.total_output_tokens += sum(
        child.total_output_tokens for child in node.children
    )


def _parse_all_spans(node: SessionNode, root_start_ms: int) -> None:
    """Recursively parse spans for node and all descendants.

    For each node with an events_path, calls normalize_timestamps to get the
    session's own start time, then parse_spans to build the span list.
    Sets node.cost_usd to the sum of all span costs.

    Args:
        node: The session node to process (and recurse into).
        root_start_ms: Unix ms of the root session's start, used as the
            time origin for all offset calculations.
    """
    if node.events_path is not None:
        try:
            session_start_ms = normalize_timestamps(node.events_path)
            node.spans = parse_spans(node.events_path, root_start_ms, session_start_ms)
            node.cost_usd = sum(span.cost_usd for span in node.spans)
        except (ValueError, OSError):
            pass  # Skip span parsing for sessions with no start event

    for child in node.children:
        _parse_all_spans(child, root_start_ms)


def _read_observability_costs(
    amplifier_home: Path, session_ids: set[str]
) -> dict[str, dict]:
    """Read pre-computed totals from observability JSONL session_summary records.

    Fast: reads only the last line of each file (session_summary is always last).
    Returns {session_id: {"cost": float, "input_tokens": int, "output_tokens": int}}.
    Falls back to an empty dict for sessions without an observability file.
    """
    obs_dir = amplifier_home / "observability"
    costs: dict[str, dict] = {}
    if not obs_dir.exists():
        return costs

    for jsonl_path in obs_dir.glob("*.jsonl"):
        # filename IS the session_id (possibly with .jsonl extension stripped)
        file_sid = jsonl_path.stem
        if file_sid not in session_ids:
            continue
        try:
            # Read only last non-empty line — session_summary is always last
            last_line = ""
            with jsonl_path.open("rb") as f:
                # Seek to near end and scan back for last newline
                f.seek(0, 2)  # end
                size = f.tell()
                chunk_size = min(4096, size)
                f.seek(max(0, size - chunk_size))
                chunk = f.read().decode("utf-8", errors="replace")
            for line in reversed(chunk.splitlines()):
                if line.strip():
                    last_line = line.strip()
                    break
            if last_line:
                record = json.loads(last_line)
                if record.get("type") == "session_summary":
                    costs[file_sid] = {
                        "cost": float(record.get("total_cost_usd", 0.0)),
                        "input_tokens": int(record.get("total_input_tokens", 0)),
                        "output_tokens": int(record.get("total_output_tokens", 0)),
                    }
        except (OSError, json.JSONDecodeError, ValueError):
            continue
    return costs


def build_session_tree(amplifier_home: Path) -> list[SessionNode]:
    """Discover sessions, build tree, and aggregate costs (metadata only).

    Four-stage pipeline (spans loaded lazily on demand, not here):
      1. discover  — scan metadata files only (fast)
      2. build_tree — link children to parents, identify roots
      3. enrich — read pre-computed costs from observability JSONL (fast, last line only)
      4. aggregate costs — roll up total_cost_usd bottom-up per tree
      5. sort — most-recent root first (by start_ts descending)

    NOTE: Spans are NOT loaded here.  Call parse_spans() per-session when
    a specific session is requested (see server._load_session).

    Returns:
        Root SessionNodes sorted most-recent first.  Returns [] when no
        sessions are found.
    """
    # Stage 1: Discover (metadata only — no event file reading)
    sessions = discover_sessions(amplifier_home)
    if not sessions:
        return []

    # Stage 2: Build tree
    roots = build_tree(sessions)

    # Stage 3: Enrich with pre-computed observability costs (fast — last line only)
    all_sids = set(sessions.keys())
    obs_costs = _read_observability_costs(amplifier_home, all_sids)
    for node in sessions.values():
        if node.session_id in obs_costs:
            entry = obs_costs[node.session_id]
            node.cost_usd = entry["cost"]
            node.total_cost_usd = entry["cost"]
            node.total_input_tokens = entry["input_tokens"]
            node.total_output_tokens = entry["output_tokens"]

    # Stage 4: Aggregate costs — children roll up to parents
    for root in roots:
        aggregate_costs(root)

    # Stage 5: Sort — named sessions first (they're the meaningful ones), then
    # by recency within each group.  Stub nodes (empty start_ts) sort last.
    def _sort_key(n: SessionNode) -> tuple[int, str]:
        # named_rank=1 for named, 0 for unnamed.  With reverse=True the higher
        # rank sorts first, so named sessions always appear before unnamed ones.
        # Within each group, the ISO start_ts string sorts most-recent first.
        named_rank = 1 if n.name else 0
        return (named_rank, n.start_ts or "")

    return sorted(roots, key=_sort_key, reverse=True)
