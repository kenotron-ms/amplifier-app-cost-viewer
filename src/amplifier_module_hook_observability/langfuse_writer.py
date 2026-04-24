"""Langfuse writer for Phase 2 observability.

Requires: pip install "hook-observability[langfuse]"

Tested against Langfuse SDK v3+. The SDK changed significantly in v4
(March 2026, OTel-based). If you hit AttributeErrors, check your version:
    python -c "import langfuse; print(langfuse.__version__)"

Self-hosted Langfuse (Docker Compose):
    cd /path/to/langfuse && docker compose up -d
    # UI at http://localhost:3000 (~2 min startup)
    # Create project -> copy public/secret keys -> paste into config
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class LangfuseWriter:
    """Sends observability records to a Langfuse instance.

    Creates one trace per Amplifier session. Provider calls become
    Generation observations; tool calls become Span observations.
    """

    def __init__(self, host: str, public_key: str, secret_key: str) -> None:
        # Set env vars before get_client() so the singleton picks them up.
        # Use setdefault so we don't stomp vars already in the environment.
        if public_key:
            os.environ.setdefault("LANGFUSE_PUBLIC_KEY", public_key)
        if secret_key:
            os.environ.setdefault("LANGFUSE_SECRET_KEY", secret_key)
        if host:
            os.environ.setdefault("LANGFUSE_HOST", host)

        try:
            from langfuse import get_client  # type: ignore[import]

            self._lf = get_client()
        except ImportError as exc:
            raise ImportError(
                "langfuse package not found. "
                "Install with: pip install 'hook-observability[langfuse]'"
            ) from exc

        # Active root-span tokens keyed by session_id.
        self._spans: dict[str, Any] = {}

    # ---------------------------------------------------------------- #

    def start_trace(self, session_id: str) -> None:
        """Called on session:start."""
        try:
            self._lf.propagate_attributes(session_id=session_id)
            obs = self._lf.start_observation(
                name="amplifier-session",
                as_type="span",
                metadata={"session_id": session_id},
            )
            self._spans[session_id] = obs
        except Exception:
            logger.exception("Langfuse start_trace failed for %s", session_id)

    def log_generation(self, session_id: str, record: dict[str, Any]) -> None:
        """Called on provider:response."""
        try:
            obs = self._lf.start_observation(
                name=f"{record['provider']}/{record['model']}",
                as_type="generation",
            )
            obs.update(
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
            obs.end()
        except Exception:
            logger.exception("Langfuse log_generation failed")

    def log_span(self, session_id: str, record: dict[str, Any]) -> None:
        """Called on tool:post."""
        try:
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
        """Called on session:end."""
        try:
            obs = self._spans.pop(session_id, None)
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
