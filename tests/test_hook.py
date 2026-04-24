"""Integration tests for the hook mount() function — subagent parent_id propagation."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _call_handler(coordinator, event: str, data: dict):
    """Find and invoke the first registered handler for an event."""
    handlers = coordinator.hooks._registered.get(event, [])
    assert handlers, f"No handler registered for '{event}'"
    _, _, handler = handlers[0]
    return await handler(event, data)


# ---------------------------------------------------------------------------
# Basic mount tests
# ---------------------------------------------------------------------------


class TestMount:
    @pytest.mark.asyncio
    async def test_registers_core_hooks(self, coordinator, tmp_path):
        from amplifier_module_hook_observability import mount

        await mount(coordinator, {"output_dir": str(tmp_path)})

        registered = set(coordinator.hooks._registered.keys())
        assert "session:start" in registered
        assert "session:end" in registered
        assert "llm:response" in registered
        assert "tool:pre" in registered
        assert "tool:post" in registered

    @pytest.mark.asyncio
    async def test_io_hooks_not_registered_by_default(self, coordinator, tmp_path):
        from amplifier_module_hook_observability import mount

        await mount(coordinator, {"output_dir": str(tmp_path)})

        registered = set(coordinator.hooks._registered.keys())
        assert "prompt:submit" not in registered
        assert "content_block:end" not in registered


# ---------------------------------------------------------------------------
# session:start — parent_id extraction
# ---------------------------------------------------------------------------


class TestSessionStartParentId:
    @pytest.mark.asyncio
    async def test_no_parent_id_in_data(self, coordinator, tmp_path):
        from amplifier_module_hook_observability import mount

        await mount(coordinator, {"output_dir": str(tmp_path)})

        result = await _call_handler(
            coordinator, "session:start", {"session_id": "sess-1"}
        )
        assert result.action == "continue"

    @pytest.mark.asyncio
    async def test_parent_id_from_event_data(self, coordinator, tmp_path):
        """parent_id in event data is written to session_summary."""
        from amplifier_module_hook_observability import mount

        await mount(coordinator, {"output_dir": str(tmp_path)})

        await _call_handler(
            coordinator,
            "session:start",
            {
                "session_id": "child-sess",
                "parent_id": "parent-sess",
            },
        )

        coordinator.session_id = "child-sess"
        await _call_handler(coordinator, "session:end", {"session_id": "child-sess"})

        log_path = tmp_path / "child-sess.jsonl"
        assert log_path.exists()
        records = [
            json.loads(line) for line in log_path.read_text().splitlines() if line
        ]
        summary = next(r for r in records if r["type"] == "session_summary")
        assert summary["parent_session_id"] == "parent-sess"

    @pytest.mark.asyncio
    async def test_parent_session_id_field_also_accepted(self, coordinator, tmp_path):
        """Accepts parent_session_id as an alternative field name."""
        from amplifier_module_hook_observability import mount

        await mount(coordinator, {"output_dir": str(tmp_path)})

        await _call_handler(
            coordinator,
            "session:start",
            {
                "session_id": "child-sess2",
                "parent_session_id": "parent-sess",
            },
        )
        coordinator.session_id = "child-sess2"
        await _call_handler(coordinator, "session:end", {"session_id": "child-sess2"})

        records = [
            json.loads(line)
            for line in (tmp_path / "child-sess2.jsonl").read_text().splitlines()
        ]
        summary = next(r for r in records if r["type"] == "session_summary")
        assert summary["parent_session_id"] == "parent-sess"

    @pytest.mark.asyncio
    async def test_parent_id_from_coordinator_attribute(self, coordinator, tmp_path):
        """Falls back to coordinator.parent_id when not in event data."""
        from amplifier_module_hook_observability import mount

        coordinator.parent_id = "coord-parent"
        await mount(coordinator, {"output_dir": str(tmp_path)})

        await _call_handler(coordinator, "session:start", {"session_id": "child-sess3"})
        coordinator.session_id = "child-sess3"
        await _call_handler(coordinator, "session:end", {"session_id": "child-sess3"})

        records = [
            json.loads(line)
            for line in (tmp_path / "child-sess3.jsonl").read_text().splitlines()
        ]
        summary = next(r for r in records if r["type"] == "session_summary")
        assert summary["parent_session_id"] == "coord-parent"

    @pytest.mark.asyncio
    async def test_no_parent_id_not_in_summary(self, coordinator, tmp_path):
        """When there's no parent_id, parent_session_id is absent from summary."""
        from amplifier_module_hook_observability import mount

        await mount(coordinator, {"output_dir": str(tmp_path)})

        await _call_handler(coordinator, "session:start", {"session_id": "root-sess"})
        coordinator.session_id = "root-sess"
        await _call_handler(coordinator, "session:end", {"session_id": "root-sess"})

        records = [
            json.loads(line)
            for line in (tmp_path / "root-sess.jsonl").read_text().splitlines()
        ]
        summary = next(r for r in records if r["type"] == "session_summary")
        assert "parent_session_id" not in summary


# ---------------------------------------------------------------------------
# session:start — passes parent_id to LangfuseWriter
# ---------------------------------------------------------------------------


class TestSessionStartLangfuse:
    @pytest.mark.asyncio
    async def test_start_trace_called_with_parent_id(
        self, coordinator, tmp_path, monkeypatch
    ):
        """start_trace receives parent_session_id when parent_id is in event data."""
        import amplifier_module_hook_observability.langfuse_writer as lfw_mod
        from amplifier_module_hook_observability import mount

        mock_lf = MagicMock()
        monkeypatch.setattr(lfw_mod, "LangfuseWriter", MagicMock(return_value=mock_lf))

        config = {
            "output_dir": str(tmp_path),
            "langfuse_enabled": True,
            "langfuse_host": "http://localhost:3000",
            "langfuse_public_key": "pk-test",
            "langfuse_secret_key": "sk-test",
        }
        await mount(coordinator, config)

        await _call_handler(
            coordinator,
            "session:start",
            {
                "session_id": "child-lf",
                "parent_id": "parent-lf",
            },
        )

        mock_lf.start_trace.assert_called_once_with(
            "child-lf", parent_session_id="parent-lf"
        )

    @pytest.mark.asyncio
    async def test_start_trace_no_parent_when_root(
        self, coordinator, tmp_path, monkeypatch
    ):
        """Root sessions call start_trace with parent_session_id=None."""
        import amplifier_module_hook_observability.langfuse_writer as lfw_mod
        from amplifier_module_hook_observability import mount

        mock_lf = MagicMock()
        monkeypatch.setattr(lfw_mod, "LangfuseWriter", MagicMock(return_value=mock_lf))

        await mount(
            coordinator,
            {
                "output_dir": str(tmp_path),
                "langfuse_enabled": True,
                "langfuse_public_key": "pk",
                "langfuse_secret_key": "sk",
            },
        )

        await _call_handler(coordinator, "session:start", {"session_id": "root-sess"})

        mock_lf.start_trace.assert_called_once_with("root-sess", parent_session_id=None)


# ---------------------------------------------------------------------------
# llm:response — basic JSONL emission (regression)
# ---------------------------------------------------------------------------


class TestLlmResponse:
    @pytest.mark.asyncio
    async def test_emits_provider_call_record(self, coordinator, tmp_path):
        from amplifier_module_hook_observability import mount

        await mount(coordinator, {"output_dir": str(tmp_path)})

        await _call_handler(coordinator, "session:start", {"session_id": "sess-llm"})
        coordinator.session_id = "sess-llm"

        await _call_handler(
            coordinator,
            "llm:response",
            {
                "session_id": "sess-llm",
                "provider": "anthropic",
                "model": "claude-sonnet-4-5",
                "usage": {"input": 100, "output": 50},
                "duration_ms": 500,
            },
        )

        records = [
            json.loads(line)
            for line in (tmp_path / "sess-llm.jsonl").read_text().splitlines()
            if line
        ]
        calls = [r for r in records if r["type"] == "provider_call"]
        assert len(calls) == 1
        assert calls[0]["provider"] == "anthropic"
        assert calls[0]["input_tokens"] == 100
        assert calls[0]["output_tokens"] == 50
        assert "cost_usd" in calls[0]
