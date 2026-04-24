"""Amplifier hook module for token cost observability.

Subscribes to provider and session lifecycle events and writes JSONL records
to ``~/.amplifier/observability/<session_id>.jsonl``.  The JSONL file is the
primary source of truth — it is self-contained and readable by any tool.

Langfuse is an *optional* secondary sink.  Disabling it loses nothing.

Configuration (via bundle YAML)::

    hooks:
      - module: hook-observability
        source: ./src
        config:
          output_dir: "~/.amplifier/observability"  # JSONL destination
          model: "claude-sonnet-4-5"                # fallback if not in event
          log_io: false     # set true to capture prompt + response + tool IO
                            # in JSONL (and Langfuse if enabled).  Produces
                            # richer records; fine to enable permanently.

          # Langfuse is fully optional — leave langfuse_enabled: false
          # to use only the local JSONL log.
          langfuse_enabled: false
          langfuse_host: "http://localhost:3000"
          langfuse_public_key: "pk-lf-..."
          langfuse_secret_key: "sk-lf-..."
          langfuse_timeout: 10

JSONL record shapes
-------------------

provider_call (always)::

    {
      "ts": "2026-04-24T17:00:00Z",
      "type": "provider_call",
      "session_id": "...",
      "provider": "anthropic",
      "model": "claude-sonnet-4-6",
      "input_tokens": 512,
      "output_tokens": 128,
      "cache_read_tokens": 0,
      "cache_write_tokens": 0,
      "reasoning_tokens": 0,
      "total_tokens": 640,
      "cost_usd": 0.003456,
      "latency_ms": 2100.0,
      // when log_io=true:
      "input": [{"role": "user", "content": "..."}],
      "output": "..."
    }

tool_call (always)::

    {
      "ts": "...",
      "type": "tool_call",
      "session_id": "...",
      "tool_name": "bash",
      "success": true,
      "latency_ms": 342.0,
      // when log_io=true:
      "input": {"command": "ls -la"},
      "output": "total 208\\n..."
    }

session_summary (on session:end)::

    {
      "ts": "...",
      "type": "session_summary",
      "session_id": "...",
      "duration_s": 42.3,
      "total_input_tokens": 8192,
      "total_output_tokens": 2048,
      "total_cost_usd": 0.08,
      "provider_calls": 12,
      "tool_calls": 34,
      "parent_session_id": "..."   // only present for child sessions
    }
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .langfuse_writer import LangfuseWriter

logger = logging.getLogger(__name__)

__amplifier_module_type__ = "hook"


async def mount(coordinator: Any, config: dict[str, Any] | None = None) -> None:  # noqa: C901
    """Register observability hooks with the Amplifier coordinator."""
    config = config or {}

    output_dir: str = config.get("output_dir", "~/.amplifier/observability")
    default_model: str = config.get("model", "unknown")

    # log_io controls IO capture for ALL sinks (JSONL + Langfuse if enabled).
    # Accept legacy key langfuse_log_io for backward compatibility.
    log_io: bool = bool(config.get("log_io", config.get("langfuse_log_io", False)))

    langfuse_enabled: bool = bool(config.get("langfuse_enabled", False))
    langfuse_timeout: int = int(config.get("langfuse_timeout", 10))

    # --- Writers ---
    from .jsonl_writer import JSONLWriter

    jsonl = JSONLWriter(output_dir)

    lf_writer: LangfuseWriter | None = None
    if langfuse_enabled:
        try:
            from .langfuse_writer import LangfuseWriter as _LangfuseWriter

            lf_writer = _LangfuseWriter(
                host=config.get("langfuse_host", "http://localhost:3000"),
                public_key=config.get("langfuse_public_key", ""),
                secret_key=config.get("langfuse_secret_key", ""),
                timeout=langfuse_timeout,
            )
            logger.info(
                "hook-observability: Langfuse enabled -> %s (timeout=%ds)",
                config.get("langfuse_host"),
                langfuse_timeout,
            )
        except ImportError:
            logger.warning(
                "hook-observability: langfuse_enabled=true but 'langfuse' package not "
                "installed. Install with: pip install 'hook-observability[langfuse]'"
            )

    # Startup auth check — surface problems immediately rather than silently.
    if lf_writer is not None:
        try:
            ok = await asyncio.to_thread(lf_writer._lf.auth_check)
            if ok:
                logger.info(
                    "hook-observability: Langfuse connection OK -> %s",
                    config.get("langfuse_host"),
                )
            else:
                logger.warning(
                    "hook-observability: Langfuse auth FAILED for %s — "
                    "check LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY",
                    config.get("langfuse_host"),
                )
        except Exception as exc:
            logger.warning(
                "hook-observability: Langfuse unreachable at %s: %s",
                config.get("langfuse_host"),
                exc,
            )

    # --- Per-session state (keyed by session_id) ---
    state: dict[str, dict[str, Any]] = {}

    # ------------------------------------------------------------------ #
    #  Small helpers                                                       #
    # ------------------------------------------------------------------ #

    _MAX_IO_CHARS = 8_000  # chars — keep records scannable

    def _truncate(value: Any, limit: int = _MAX_IO_CHARS) -> Any:
        """Truncate long string values so logs stay scannable."""
        if value is None:
            return None
        if isinstance(value, str) and len(value) > limit:
            return value[:limit] + f"\n…[truncated {len(value) - limit} chars]"
        return value

    def _usage_int(usage: Any, field: str) -> int:
        if usage is None:
            return 0
        if hasattr(usage, field):
            return int(getattr(usage, field) or 0)
        if isinstance(usage, dict):
            return int(usage.get(field) or 0)
        return 0

    # ------------------------------------------------------------------ #
    #  Handlers                                                            #
    # ------------------------------------------------------------------ #

    async def on_session_start(event: str, data: dict[str, Any]) -> Any:
        from amplifier_core import HookResult  # type: ignore[import]

        sid: str = data.get("session_id", "unknown")

        # Resolve parent_id: event data takes precedence, then coordinator attribute.
        parent_id: str | None = (
            data.get("parent_id")
            or data.get("parent_session_id")
            or getattr(coordinator, "parent_id", None)
        )

        state[sid] = {
            "parent_session_id": parent_id,
            "start_time": time.perf_counter(),
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cost_usd": 0.0,
            "provider_calls": 0,
            "tool_calls": 0,
            "tool_start": None,
            "current_model": default_model,
            "current_provider": "unknown",
        }
        if lf_writer is not None:
            await asyncio.to_thread(
                lf_writer.start_trace, sid, parent_session_id=parent_id
            )
        return HookResult(action="continue")

    async def on_session_end(event: str, data: dict[str, Any]) -> Any:
        from amplifier_core import HookResult  # type: ignore[import]

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
        # Include parent link so JSONL logs carry the full delegation chain.
        if s.get("parent_session_id"):
            record["parent_session_id"] = s["parent_session_id"]
        jsonl.write(record)
        if lf_writer is not None:
            # end_trace calls flush() — run off the event loop so we don't block.
            await asyncio.to_thread(lf_writer.end_trace, sid, record)
        return HookResult(action="continue")

    async def on_llm_response(event: str, data: dict[str, Any]) -> Any:
        """Handle llm:response — fired by providers with actual usage data.

        The llm:response event uses short keys in the usage dict:
          "input" / "output" / "cache_read" / "cache_write"
        and does not carry session_id, so we fall back to coordinator.session_id.
        """
        from amplifier_core import HookResult  # type: ignore[import]
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
        cache_read = _usage_int(usage, "cache_read") or _usage_int(
            usage, "cache_read_tokens"
        )
        cache_write = _usage_int(usage, "cache_write") or _usage_int(
            usage, "cache_write_tokens"
        )
        reasoning = _usage_int(usage, "reasoning") or _usage_int(
            usage, "reasoning_tokens"
        )

        model = data.get("model") or s.get("current_model", default_model)
        provider = data.get("provider") or s.get("current_provider", "unknown")
        cost = compute_cost(
            model, input_tok, output_tok, cache_read, cache_write, reasoning
        )

        # duration_ms is provided directly in the llm:response event
        duration_ms = data.get("duration_ms")
        latency_ms: float | None = (
            round(float(duration_ms), 1) if duration_ms is not None else None
        )

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

        # Drain IO state captured by prompt:submit / content_block:end handlers.
        # This runs whenever log_io=true, regardless of whether Langfuse is on.
        io_data: dict[str, Any] | None = None
        if log_io:
            pending_input: str | None = s.pop("pending_input", None)
            out_parts: list[str] = s.pop("pending_output_parts", None) or []
            tool_uses: list[dict[str, Any]] = s.pop("pending_tool_uses", None) or []

            lf_input = (
                [{"role": "user", "content": pending_input}] if pending_input else None
            )

            # Build structured output: text first, then tool calls.
            out_content: list[Any] = []
            if out_parts:
                out_content.append({"type": "text", "text": "".join(out_parts)})
            out_content.extend(tool_uses)

            lf_output: Any = None
            if out_content:
                # Flatten single plain-text block to a string — cleaner in both
                # JSONL and Langfuse UI.
                lf_output = (
                    out_content[0]["text"]
                    if len(out_content) == 1 and out_content[0].get("type") == "text"
                    else {"role": "assistant", "content": out_content}
                )

            io_data = {"input": lf_input, "output": lf_output}
            # Enrich the JSONL record with IO so the file is self-contained.
            if lf_input is not None:
                record["input"] = lf_input
            if lf_output is not None:
                record["output"] = lf_output

        # JSONL is always written first — it is the primary sink.
        jsonl.write(record)

        if lf_writer is not None:
            await asyncio.to_thread(lf_writer.log_generation, sid, record, io_data)
        return HookResult(action="continue")

    async def on_tool_pre(event: str, data: dict[str, Any]) -> Any:
        from amplifier_core import HookResult  # type: ignore[import]

        sid: str = data.get("session_id", "unknown")
        if sid in state:
            state[sid]["tool_start"] = time.perf_counter()
        return HookResult(action="continue")

    async def on_tool_post(event: str, data: dict[str, Any]) -> Any:
        from amplifier_core import HookResult  # type: ignore[import]

        sid: str = data.get("session_id", "unknown")
        s = state.get(sid, {})

        latency_ms: float | None = None
        if s.get("tool_start") is not None:
            latency_ms = round((time.perf_counter() - s["tool_start"]) * 1000, 1)
            s["tool_start"] = None

        # The orchestrator sends the result under "result" (not "tool_result").
        # result_data is already serialized: model_dump() dict or str.
        result_data = data.get("result")
        success = True
        if isinstance(result_data, dict):
            success = bool(result_data.get("success", True))

        s["tool_calls"] = s.get("tool_calls", 0) + 1

        record: dict[str, Any] = {
            "type": "tool_call",
            "session_id": sid,
            "tool_name": data.get("tool_name", "unknown"),
            "success": success,
            "latency_ms": latency_ms,
        }

        # Capture tool IO when log_io=true — goes into JSONL AND Langfuse.
        io_data: dict[str, Any] | None = None
        if log_io:
            tool_input = data.get("tool_input")
            tool_output: Any = None
            if isinstance(result_data, dict):
                raw = result_data.get("output") or result_data.get("error")
                tool_output = _truncate(raw)
            elif result_data is not None:
                tool_output = _truncate(str(result_data))

            if tool_input is not None:
                record["input"] = tool_input
            if tool_output is not None:
                record["output"] = tool_output
            if tool_input is not None or tool_output is not None:
                io_data = {"input": tool_input, "output": tool_output}

        # JSONL is always written first — it is the primary sink.
        jsonl.write(record)

        if lf_writer is not None:
            await asyncio.to_thread(lf_writer.log_span, sid, record, io_data)
        return HookResult(action="continue")

    async def on_prompt_submit(event: str, data: dict[str, Any]) -> Any:
        """Capture the user prompt before the LLM call — stored for IO logging."""
        from amplifier_core import HookResult  # type: ignore[import]

        sid = coordinator.session_id or "unknown"
        if sid not in state:
            # Fallback: if state has exactly one session, use it.
            if len(state) == 1:
                sid = next(iter(state))
            else:
                logger.debug(
                    "on_prompt_submit: session %s not in state (keys=%s)",
                    sid,
                    list(state),
                )
                return HookResult(action="continue")
        prompt = data.get("prompt", "")
        if prompt:
            state[sid]["pending_input"] = prompt
            logger.debug(
                "on_prompt_submit: captured %d chars for session %s", len(prompt), sid
            )
        return HookResult(action="continue")

    async def on_content_block_end(event: str, data: dict[str, Any]) -> Any:
        """Accumulate LLM output blocks — stored for IO logging."""
        from amplifier_core import HookResult  # type: ignore[import]

        sid = coordinator.session_id or "unknown"
        if sid not in state:
            # Fallback: if state has exactly one session, use it.
            if len(state) == 1:
                sid = next(iter(state))
            else:
                return HookResult(action="continue")

        block = data.get("block") or {}
        btype = block.get("type", "")

        if btype == "text":
            text = block.get("text", "")
            if text:
                state[sid].setdefault("pending_output_parts", []).append(text)
        elif btype == "tool_use":
            state[sid].setdefault("pending_tool_uses", []).append(
                {
                    "type": "tool_use",
                    "name": block.get("name", ""),
                    "input": block.get("input", {}),
                }
            )
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

    # IO capture handlers — only wired when log_io=true to avoid accumulating
    # state we'll never consume.
    if log_io:
        hooks.register(
            "prompt:submit", on_prompt_submit, priority=5, name="obs-prompt-submit"
        )
        hooks.register(
            "content_block:end",
            on_content_block_end,
            priority=95,
            name="obs-content-block-end",
        )

    logger.info(
        "hook-observability mounted -- output_dir=%s log_io=%s langfuse=%s",
        output_dir,
        log_io,
        langfuse_enabled,
    )
