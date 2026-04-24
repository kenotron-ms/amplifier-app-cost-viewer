"""Amplifier hook module for token cost observability.

Subscribes to provider and session lifecycle events, writes JSONL records
locally, and optionally ships to Langfuse.

Configuration (via bundle YAML):

    hooks:
      - module: hook-observability
        source: ./src
        config:
          output_dir: "~/.amplifier/observability"  # JSONL destination
          model: "claude-sonnet-4-5"                # fallback if not in response
          langfuse_enabled: false
          langfuse_host: "http://localhost:3000"
          langfuse_public_key: "pk-lf-..."
          langfuse_secret_key: "sk-lf-..."
"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

__amplifier_module_type__ = "hook"


async def mount(coordinator: Any, config: dict[str, Any] | None = None) -> None:  # noqa: C901
    """Register observability hooks with the Amplifier coordinator."""
    config = config or {}

    output_dir: str = config.get("output_dir", "~/.amplifier/observability")
    default_model: str = config.get("model", "unknown")
    langfuse_enabled: bool = bool(config.get("langfuse_enabled", False))

    # --- Writers ---
    from .jsonl_writer import JSONLWriter

    jsonl = JSONLWriter(output_dir)

    langfuse_writer = None
    if langfuse_enabled:
        try:
            from .langfuse_writer import LangfuseWriter

            langfuse_writer = LangfuseWriter(
                host=config.get("langfuse_host", "http://localhost:3000"),
                public_key=config.get("langfuse_public_key", ""),
                secret_key=config.get("langfuse_secret_key", ""),
            )
            logger.info(
                "hook-observability: Langfuse enabled -> %s",
                config.get("langfuse_host"),
            )
        except ImportError:
            logger.warning(
                "hook-observability: langfuse_enabled=true but 'langfuse' package not "
                "installed. Install with: pip install 'hook-observability[langfuse]'"
            )

    # --- Per-session state (keyed by session_id) ---
    state: dict[str, dict[str, Any]] = {}

    # ------------------------------------------------------------------ #
    #  Small helpers                                                       #
    # ------------------------------------------------------------------ #

    def _usage_int(usage: Any, field: str) -> int:
        if usage is None:
            return 0
        if hasattr(usage, field):
            return int(getattr(usage, field) or 0)
        if isinstance(usage, dict):
            return int(usage.get(field) or 0)
        return 0

    def _model_from_response(response: Any, fallback: str) -> str:
        if response is not None and hasattr(response, "metadata"):
            meta = response.metadata
            if isinstance(meta, dict):
                return meta.get("model", fallback)
        return fallback

    # ------------------------------------------------------------------ #
    #  Handlers                                                            #
    # ------------------------------------------------------------------ #

    async def on_session_start(event: str, data: dict[str, Any]) -> Any:
        from amplifier_core import HookResult

        sid: str = data.get("session_id", "unknown")
        state[sid] = {
            "start_time": time.perf_counter(),
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cost_usd": 0.0,
            "provider_calls": 0,
            "tool_calls": 0,
            "llm_start": None,
            "tool_start": None,
            "current_model": default_model,
            "current_provider": "unknown",
        }
        if langfuse_writer is not None:
            langfuse_writer.start_trace(sid)
        return HookResult(action="continue")

    async def on_session_end(event: str, data: dict[str, Any]) -> Any:
        from amplifier_core import HookResult

        sid: str = data.get("session_id", "unknown")
        s = state.pop(sid, {})
        elapsed = time.perf_counter() - s.get("start_time", time.perf_counter())

        record: dict[str, Any] = {
            "type": "session_summary",
            "session_id": sid,
            "duration_s": round(elapsed, 3),
            "total_input_tokens": s.get("total_input_tokens", 0),
            "total_output_tokens": s.get("total_output_tokens", 0),
            "total_cost_usd": round(s.get("total_cost_usd", 0.0), 6),
            "provider_calls": s.get("provider_calls", 0),
            "tool_calls": s.get("tool_calls", 0),
        }
        jsonl.write(record)
        if langfuse_writer is not None:
            langfuse_writer.end_trace(sid, record)
        return HookResult(action="continue")

    async def on_llm_response(event: str, data: dict[str, Any]) -> Any:
        """Handle llm:response — fired by providers with actual usage data.

        The llm:response event uses short keys in the usage dict:
          "input" / "output" / "cache_read" / "cache_write"
        and does not carry session_id, so we fall back to coordinator.session_id.
        """
        from amplifier_core import HookResult
        from .pricing import compute_cost

        # llm:response has no session_id — fall back to this session's ID
        sid: str = data.get("session_id") or coordinator.session_id or "unknown"
        s = state.get(sid)
        if s is None:
            # Hook mounted mid-session — create a stub so we still log.
            s = {
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_cost_usd": 0.0,
                "provider_calls": 0,
                "current_provider": data.get("provider", "unknown"),
                "current_model": default_model,
            }
            state[sid] = s

        usage = data.get("usage") or {}
        # llm:response uses short keys: "input", "output", "cache_read", "cache_write"
        input_tok = _usage_int(usage, "input") or _usage_int(usage, "input_tokens")
        output_tok = _usage_int(usage, "output") or _usage_int(usage, "output_tokens")
        cache_read = _usage_int(usage, "cache_read") or _usage_int(usage, "cache_read_tokens")
        cache_write = _usage_int(usage, "cache_write") or _usage_int(usage, "cache_write_tokens")
        reasoning = _usage_int(usage, "reasoning") or _usage_int(usage, "reasoning_tokens")

        model = data.get("model") or s.get("current_model", default_model)
        provider = data.get("provider") or s.get("current_provider", "unknown")
        cost = compute_cost(model, input_tok, output_tok, cache_read, cache_write, reasoning)

        # duration_ms is provided directly in the llm:response event
        duration_ms = data.get("duration_ms")
        latency_ms: float | None = round(float(duration_ms), 1) if duration_ms is not None else None

        s["total_input_tokens"] += input_tok
        s["total_output_tokens"] += output_tok
        s["total_cost_usd"] += cost
        s["provider_calls"] += 1
        s["current_model"] = model

        record: dict[str, Any] = {
            "type": "provider_call",
            "session_id": sid,
            "provider": provider,
            "model": model,
            "input_tokens": input_tok,
            "output_tokens": output_tok,
            "cache_read_tokens": cache_read,
            "cache_write_tokens": cache_write,
            "reasoning_tokens": reasoning,
            "total_tokens": input_tok + output_tok,
            "cost_usd": round(cost, 6),
            "latency_ms": latency_ms,
        }
        jsonl.write(record)
        if langfuse_writer is not None:
            langfuse_writer.log_generation(sid, record)
        return HookResult(action="continue")

    async def on_tool_pre(event: str, data: dict[str, Any]) -> Any:
        from amplifier_core import HookResult

        sid: str = data.get("session_id", "unknown")
        if sid in state:
            state[sid]["tool_start"] = time.perf_counter()
        return HookResult(action="continue")

    async def on_tool_post(event: str, data: dict[str, Any]) -> Any:
        from amplifier_core import HookResult

        sid: str = data.get("session_id", "unknown")
        s = state.get(sid, {})

        latency_ms: float | None = None
        if s.get("tool_start") is not None:
            latency_ms = round((time.perf_counter() - s["tool_start"]) * 1000, 1)
            s["tool_start"] = None

        tool_result = data.get("tool_result")
        success = True
        if tool_result is not None:
            if hasattr(tool_result, "success"):
                success = bool(tool_result.success)
            elif isinstance(tool_result, dict):
                success = bool(tool_result.get("success", True))

        s["tool_calls"] = s.get("tool_calls", 0) + 1

        record: dict[str, Any] = {
            "type": "tool_call",
            "session_id": sid,
            "tool_name": data.get("tool_name", "unknown"),
            "success": success,
            "latency_ms": latency_ms,
        }
        jsonl.write(record)
        if langfuse_writer is not None:
            langfuse_writer.log_span(sid, record)
        return HookResult(action="continue")

    # ------------------------------------------------------------------ #
    #  Registration                                                        #
    # ------------------------------------------------------------------ #

    hooks = coordinator.hooks
    hooks.register(
        "session:start", on_session_start, priority=5, name="obs-session-start"
    )
    hooks.register("session:end", on_session_end, priority=95, name="obs-session-end")
    hooks.register(
        "llm:response",
        on_llm_response,
        priority=90,
        name="obs-llm-response",
    )
    hooks.register("tool:pre", on_tool_pre, priority=5, name="obs-tool-pre")
    hooks.register("tool:post", on_tool_post, priority=90, name="obs-tool-post")

    logger.info(
        "hook-observability mounted -- output_dir=%s langfuse=%s",
        output_dir,
        langfuse_enabled,
    )
