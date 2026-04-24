"""Langfuse writer for Phase 2 observability.

Requires: pip install "hook-observability[langfuse]"

Tested against Langfuse SDK v3+. The SDK changed significantly in v4
(March 2026, OTel-based). If you hit AttributeErrors, check your version:
    python -c "import langfuse; print(langfuse.__version__)"

Self-hosted Langfuse (Docker Compose):
    cd /path/to/langfuse && docker compose up -d
    # UI at http://localhost:3000 (~2 min startup)
    # Create project -> copy public/secret keys -> paste into config

Non-blocking usage
------------------
All public methods are synchronous so they can be run in a thread pool.
Call them via ``asyncio.to_thread(writer.method, ...)`` from async hook
handlers so they never block the CLI event loop.

Subagent tracing
----------------
When Amplifier spawns a child session (via delegate()), the child session's
``session:start`` event carries a ``parent_id`` field.  Pass this to
``start_trace(session_id, parent_session_id=parent_id)`` and the child
session's root span will be nested inside the parent's root span, creating
a proper trace hierarchy in the Langfuse UI:

    Parent Session Trace
    └── amplifier-session
        ├── anthropic/claude-sonnet (generation)
        ├── bash (tool span)
        └── child-session:<short_id>   ← child session root
            ├── anthropic/claude-sonnet (generation)
            └── bash (tool span)

Same-process nesting works automatically; the parent's root span object is
stored in ``_spans`` and used as the parent for the child's ``start_observation``.

Sessions
--------
All observations are grouped in a Langfuse Session keyed by the *root*
ancestor's session_id.  Child sessions inherit their parent's session_id
so the entire delegation tree appears in a single Langfuse Session.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class LangfuseWriter:
    """Sends observability records to a Langfuse instance.

    Creates one Langfuse *session* per Amplifier session tree (grouping all
    traces and subagent calls together).  Provider calls become Generation
    observations; tool calls become Span observations; subagent sessions
    become nested Span observations under their parent's root span.

    Methods are synchronous — call them via ``asyncio.to_thread()`` from async
    hook handlers to avoid blocking the event loop.
    """

    def __init__(
        self,
        host: str,
        public_key: str,
        secret_key: str,
        timeout: int = 10,
    ) -> None:
        # Strip stray quotes that can appear when values come from Amplifier
        # keys.yaml (which wraps values in "...") vs keys.env (already stripped).
        def _strip(v: str) -> str:
            return v.strip('"').strip("'").strip()

        host = _strip(host)
        public_key = _strip(public_key)
        secret_key = _strip(secret_key)

        # Set env vars before get_client() so the singleton picks them up.
        if public_key:
            os.environ["LANGFUSE_PUBLIC_KEY"] = public_key
        if secret_key:
            os.environ["LANGFUSE_SECRET_KEY"] = secret_key
        if host:
            os.environ["LANGFUSE_HOST"] = host

        try:
            from langfuse import Langfuse  # type: ignore[import]

            self._lf = Langfuse(timeout=timeout)
        except ImportError as exc:
            raise ImportError(
                "langfuse package not found. "
                "Install with: pip install 'hook-observability[langfuse]'"
            ) from exc

        # Root-span objects keyed by session_id.
        self._spans: dict[str, Any] = {}

        # Maps child_session_id → parent_session_id for Langfuse Session grouping.
        # Child sessions group under the root ancestor's session_id so the
        # entire delegation tree appears in a single Langfuse Session.
        self._parent_sessions: dict[str, str] = {}

    # ---------------------------------------------------------------- #
    #  Helpers                                                           #
    # ---------------------------------------------------------------- #

    def _langfuse_session_id(self, session_id: str) -> str:
        """Return the Langfuse session_id to use for grouping.

        Child sessions inherit their parent's session_id so all related work
        appears in a single Langfuse Session view.
        """
        return self._parent_sessions.get(session_id, session_id)

    # ---------------------------------------------------------------- #
    #  Public API                                                        #
    # ---------------------------------------------------------------- #

    def start_trace(
        self,
        session_id: str,
        parent_session_id: str | None = None,
    ) -> None:
        """Called on session:start — opens the root summary span.

        Args:
            session_id: Amplifier session ID for this session.
            parent_session_id: ID of the parent session when this is a child
                (spawned via delegate()).  When provided and the parent's root
                span is available, the child's root span is nested inside the
                parent's, creating a proper trace hierarchy in Langfuse.
        """
        if parent_session_id:
            self._parent_sessions[session_id] = parent_session_id

        parent_span = self._spans.get(parent_session_id) if parent_session_id else None
        lf_sid = self._langfuse_session_id(session_id)

        try:
            from langfuse import propagate_attributes  # type: ignore[import]

            metadata: dict[str, Any] = {"session_id": session_id}
            if parent_session_id:
                metadata["parent_session_id"] = parent_session_id

            with propagate_attributes(session_id=lf_sid):
                if parent_span is not None:
                    # Child session: nest under the parent's root span.
                    # This places the child's span inside the parent's trace,
                    # building a proper hierarchy without cross-service IDs.
                    obs = parent_span.start_observation(
                        name=f"child-session:{session_id[:8]}",
                        as_type="span",
                        metadata=metadata,
                    )
                else:
                    # Root session (or orphaned child): new trace.
                    obs = self._lf.start_observation(
                        name="amplifier-session",
                        as_type="span",
                        metadata=metadata,
                    )
            self._spans[session_id] = obs
        except Exception:
            logger.exception("Langfuse start_trace failed for %s", session_id)

    def log_generation(
        self,
        session_id: str,
        record: dict[str, Any],
        io_data: dict[str, Any] | None = None,
    ) -> None:
        """Called on llm:response.

        Creates a Generation observation nested under the session's root span
        (if available), giving each LLM call proper hierarchy in the trace.

        Args:
            session_id: Amplifier session ID.
            record: Cost/usage record built by the hook.
            io_data: Optional ``{"input": ..., "output": ...}`` with the raw
                prompt messages and response content.  Only passed when
                ``langfuse_log_io`` is enabled in config.
        """
        try:
            from langfuse import propagate_attributes  # type: ignore[import]

            lf_sid = self._langfuse_session_id(session_id)
            root_span = self._spans.get(session_id)

            with propagate_attributes(session_id=lf_sid):
                if root_span is not None:
                    obs = root_span.start_observation(
                        name=f"{record['provider']}/{record['model']}",
                        as_type="generation",
                    )
                else:
                    obs = self._lf.start_observation(
                        name=f"{record['provider']}/{record['model']}",
                        as_type="generation",
                    )
                update_kwargs: dict[str, Any] = dict(
                    model=record["model"],
                    usage_details={
                        "input": record["input_tokens"],
                        "output": record["output_tokens"],
                    },
                    cost_details={
                        "input": _split_cost(record, "input"),
                        "output": _split_cost(record, "output"),
                        "total": record["cost_usd"],
                    },
                    metadata={
                        "session_id": session_id,
                        "provider": record["provider"],
                        "cache_read_tokens": record.get("cache_read_tokens", 0),
                        "cache_write_tokens": record.get("cache_write_tokens", 0),
                        "reasoning_tokens": record.get("reasoning_tokens", 0),
                        "latency_ms": record.get("latency_ms"),
                    },
                )
                if io_data is not None:
                    if io_data.get("input") is not None:
                        update_kwargs["input"] = io_data["input"]
                    if io_data.get("output") is not None:
                        update_kwargs["output"] = io_data["output"]
                obs.update(**update_kwargs)
                obs.end()
        except Exception:
            logger.exception("Langfuse log_generation failed")

    def log_span(self, session_id: str, record: dict[str, Any]) -> None:
        """Called on tool:post.

        Creates a Span observation nested under the session's root span.
        """
        try:
            from langfuse import propagate_attributes  # type: ignore[import]

            lf_sid = self._langfuse_session_id(session_id)
            root_span = self._spans.get(session_id)

            with propagate_attributes(session_id=lf_sid):
                if root_span is not None:
                    obs = root_span.start_observation(
                        name=record["tool_name"],
                        as_type="span",
                    )
                else:
                    obs = self._lf.start_observation(
                        name=record["tool_name"],
                        as_type="span",
                    )
                obs.update(
                    metadata={
                        "session_id": session_id,
                        "success": record["success"],
                        "latency_ms": record.get("latency_ms"),
                    },
                    level="DEFAULT" if record["success"] else "WARNING",
                )
                obs.end()
        except Exception:
            logger.exception("Langfuse log_span failed")

    def end_trace(self, session_id: str, summary: dict[str, Any]) -> None:
        """Called on session:end — closes the root span and flushes.

        ``flush()`` is blocking (waits for the OTel batch to drain).  This
        method is intended to be called via ``asyncio.to_thread()`` so it
        runs off the event loop.
        """
        try:
            obs = self._spans.pop(session_id, None)
            self._parent_sessions.pop(session_id, None)

            if obs is not None:
                obs.update(
                    metadata={
                        "total_cost_usd": summary.get("total_cost_usd"),
                        "provider_calls": summary.get("provider_calls"),
                        "tool_calls": summary.get("tool_calls"),
                        "duration_s": summary.get("duration_s"),
                    },
                )
                obs.end()
            self._lf.flush()
        except Exception:
            logger.exception("Langfuse end_trace failed for %s", session_id)

    def flush(self) -> None:
        """Blocking flush — call via ``asyncio.to_thread()``."""
        try:
            self._lf.flush()
        except Exception:
            logger.exception("Langfuse flush failed")


# ---------------------------------------------------------------- #
#  Helpers                                                          #
# ---------------------------------------------------------------- #


def _split_cost(record: dict[str, Any], side: str) -> float:
    """Approximate input or output portion of total cost."""
    total = record.get("cost_usd", 0.0)
    in_tok = record.get("input_tokens", 0)
    out_tok = record.get("output_tokens", 0)
    denom = in_tok + out_tok
    if denom == 0:
        return 0.0
    frac = in_tok / denom if side == "input" else out_tok / denom
    return round(total * frac, 6)
