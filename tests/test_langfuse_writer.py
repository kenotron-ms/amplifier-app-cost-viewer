"""Tests for LangfuseWriter — subagent trace nesting."""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Helpers — build a mock Langfuse environment
# ---------------------------------------------------------------------------


def _make_propagate_ctx():
    """Return a mock propagate_attributes usable as a context manager."""

    @contextmanager
    def _ctx(*args, **kwargs):
        yield

    mock = MagicMock(side_effect=_ctx)
    return mock


def _make_langfuse_env(monkeypatch):
    """
    Patch the langfuse module so LangfuseWriter can be imported without
    the real SDK installed.  Returns (mock_Langfuse_class, mock_lf_instance,
    mock_propagate).
    """
    mock_lf = MagicMock()
    mock_Langfuse = MagicMock(return_value=mock_lf)
    mock_propagate = _make_propagate_ctx()

    langfuse_mod = MagicMock()
    langfuse_mod.Langfuse = mock_Langfuse
    langfuse_mod.propagate_attributes = mock_propagate

    import sys

    sys.modules["langfuse"] = langfuse_mod
    return mock_Langfuse, mock_lf, mock_propagate


@pytest.fixture
def lf_env(monkeypatch):
    mock_Langfuse, mock_lf, mock_propagate = _make_langfuse_env(monkeypatch)
    return {"Langfuse": mock_Langfuse, "lf": mock_lf, "propagate": mock_propagate}


@pytest.fixture
def writer(lf_env):
    from amplifier_module_hook_observability.langfuse_writer import LangfuseWriter

    return LangfuseWriter(
        host="http://localhost:3000",
        public_key="pk-test",
        secret_key="sk-test",
    )


# ---------------------------------------------------------------------------
# start_trace: root session
# ---------------------------------------------------------------------------


class TestStartTraceRoot:
    def test_creates_span_via_client(self, writer, lf_env):
        mock_span = MagicMock()
        lf_env["lf"].start_observation.return_value = mock_span

        writer.start_trace("session-1")

        lf_env["lf"].start_observation.assert_called_once_with(
            name="amplifier-session",
            as_type="span",
            metadata={"session_id": "session-1"},
        )

    def test_span_stored(self, writer, lf_env):
        mock_span = MagicMock()
        lf_env["lf"].start_observation.return_value = mock_span

        writer.start_trace("session-1")

        assert writer._spans["session-1"] is mock_span

    def test_no_parent_session_tracked(self, writer, lf_env):
        lf_env["lf"].start_observation.return_value = MagicMock()
        writer.start_trace("session-1")
        assert "session-1" not in writer._parent_sessions


# ---------------------------------------------------------------------------
# start_trace: child session (the key new behaviour)
# ---------------------------------------------------------------------------


class TestStartTraceChild:
    def _setup_parent(self, writer, lf_env):
        mock_parent_span = MagicMock()
        lf_env["lf"].start_observation.return_value = mock_parent_span
        writer.start_trace("parent-session")
        lf_env["lf"].start_observation.reset_mock()
        return mock_parent_span

    def test_child_uses_parent_span_not_client(self, writer, lf_env):
        mock_parent_span = self._setup_parent(writer, lf_env)
        mock_child_span = MagicMock()
        mock_parent_span.start_observation.return_value = mock_child_span

        writer.start_trace("child-session", parent_session_id="parent-session")

        # Client-level start_observation NOT called for child
        lf_env["lf"].start_observation.assert_not_called()
        # Parent span's start_observation IS called
        mock_parent_span.start_observation.assert_called_once()

    def test_child_span_name_contains_short_id(self, writer, lf_env):
        mock_parent_span = self._setup_parent(writer, lf_env)
        mock_child_span = MagicMock()
        mock_parent_span.start_observation.return_value = mock_child_span

        writer.start_trace("child-session-abcdef", parent_session_id="parent-session")

        args, kwargs = mock_parent_span.start_observation.call_args
        assert "child-session-abcdef"[:8] in kwargs.get("name", "")

    def test_child_span_metadata_has_both_ids(self, writer, lf_env):
        mock_parent_span = self._setup_parent(writer, lf_env)
        mock_parent_span.start_observation.return_value = MagicMock()

        writer.start_trace("child-123", parent_session_id="parent-session")

        _, kwargs = mock_parent_span.start_observation.call_args
        meta = kwargs.get("metadata", {})
        assert meta["session_id"] == "child-123"
        assert meta["parent_session_id"] == "parent-session"

    def test_child_span_stored_keyed_by_child_id(self, writer, lf_env):
        mock_parent_span = self._setup_parent(writer, lf_env)
        mock_child_span = MagicMock()
        mock_parent_span.start_observation.return_value = mock_child_span

        writer.start_trace("child-123", parent_session_id="parent-session")

        assert writer._spans["child-123"] is mock_child_span

    def test_parent_session_tracked(self, writer, lf_env):
        self._setup_parent(writer, lf_env)
        lf_env["lf"].start_observation.return_value = MagicMock()
        writer._spans["parent-session"].start_observation.return_value = MagicMock()

        writer.start_trace("child-123", parent_session_id="parent-session")

        assert writer._parent_sessions["child-123"] == "parent-session"

    def test_unknown_parent_falls_back_to_root(self, writer, lf_env):
        """If parent session has no stored span, create a new root trace."""
        mock_span = MagicMock()
        lf_env["lf"].start_observation.return_value = mock_span

        writer.start_trace("child-orphan", parent_session_id="nonexistent-parent")

        # Should fall back to client-level call (like a root session)
        lf_env["lf"].start_observation.assert_called_once()

    def test_langfuse_session_grouping_uses_parent_id(self, writer, lf_env):
        """Child session's Langfuse Session should be keyed by parent's session_id."""
        mock_parent_span = self._setup_parent(writer, lf_env)
        mock_parent_span.start_observation.return_value = MagicMock()

        writer.start_trace("child-abc", parent_session_id="parent-session")

        # _langfuse_session_id should return parent's ID for grouping
        assert writer._langfuse_session_id("child-abc") == "parent-session"


# ---------------------------------------------------------------------------
# log_generation — nested under root span
# ---------------------------------------------------------------------------


class TestLogGeneration:
    def _record(self, **kw):
        base = {
            "provider": "anthropic",
            "model": "claude-sonnet-4-5",
            "input_tokens": 100,
            "output_tokens": 50,
            "cache_read_tokens": 0,
            "cache_write_tokens": 0,
            "reasoning_tokens": 0,
            "cost_usd": 0.001,
            "latency_ms": 500.0,
        }
        base.update(kw)
        return base

    def test_uses_root_span_when_available(self, writer, lf_env):
        mock_root = MagicMock()
        mock_gen = MagicMock()
        mock_root.start_observation.return_value = mock_gen
        lf_env["lf"].start_observation.return_value = mock_root
        writer.start_trace("sess-1")

        writer.log_generation("sess-1", self._record())

        # Should use root span, not client
        mock_root.start_observation.assert_called_once()
        lf_env["lf"].start_observation.assert_called_once()  # only from start_trace

    def test_generation_name_is_provider_slash_model(self, writer, lf_env):
        mock_root = MagicMock()
        mock_gen = MagicMock()
        mock_root.start_observation.return_value = mock_gen
        lf_env["lf"].start_observation.return_value = mock_root
        writer.start_trace("sess-1")

        writer.log_generation("sess-1", self._record(provider="openai", model="gpt-4o"))

        _, kwargs = mock_root.start_observation.call_args
        assert kwargs.get("name") == "openai/gpt-4o"
        assert kwargs.get("as_type") == "generation"

    def test_generation_ended(self, writer, lf_env):
        mock_root = MagicMock()
        mock_gen = MagicMock()
        mock_root.start_observation.return_value = mock_gen
        lf_env["lf"].start_observation.return_value = mock_root
        writer.start_trace("sess-1")

        writer.log_generation("sess-1", self._record())

        mock_gen.end.assert_called_once()

    def test_fallback_to_client_when_no_root_span(self, writer, lf_env):
        mock_gen = MagicMock()
        lf_env["lf"].start_observation.return_value = mock_gen

        writer.log_generation("no-trace-session", self._record())

        lf_env["lf"].start_observation.assert_called_once()

    def test_io_data_passed_when_provided(self, writer, lf_env):
        mock_root = MagicMock()
        mock_gen = MagicMock()
        mock_root.start_observation.return_value = mock_gen
        lf_env["lf"].start_observation.return_value = mock_root
        writer.start_trace("sess-1")

        io = {"input": [{"role": "user", "content": "hello"}], "output": "world"}
        writer.log_generation("sess-1", self._record(), io_data=io)

        _, update_kwargs = mock_gen.update.call_args
        assert update_kwargs.get("input") == io["input"]
        assert update_kwargs.get("output") == io["output"]


# ---------------------------------------------------------------------------
# log_span — nested under root span
# ---------------------------------------------------------------------------


class TestLogSpan:
    def _record(self, **kw):
        base = {"tool_name": "bash", "success": True, "latency_ms": 123.0}
        base.update(kw)
        return base

    def test_uses_root_span_when_available(self, writer, lf_env):
        mock_root = MagicMock()
        mock_span = MagicMock()
        mock_root.start_observation.return_value = mock_span
        lf_env["lf"].start_observation.return_value = mock_root
        writer.start_trace("sess-1")

        writer.log_span("sess-1", self._record())

        mock_root.start_observation.assert_called_once()
        lf_env["lf"].start_observation.assert_called_once()  # only from start_trace

    def test_span_name_is_tool_name(self, writer, lf_env):
        mock_root = MagicMock()
        mock_span = MagicMock()
        mock_root.start_observation.return_value = mock_span
        lf_env["lf"].start_observation.return_value = mock_root
        writer.start_trace("sess-1")

        writer.log_span("sess-1", self._record(tool_name="filesystem"))

        _, kwargs = mock_root.start_observation.call_args
        assert kwargs.get("name") == "filesystem"

    def test_span_ended(self, writer, lf_env):
        mock_root = MagicMock()
        mock_span = MagicMock()
        mock_root.start_observation.return_value = mock_span
        lf_env["lf"].start_observation.return_value = mock_root
        writer.start_trace("sess-1")

        writer.log_span("sess-1", self._record())

        mock_span.end.assert_called_once()

    def test_failure_sets_warning_level(self, writer, lf_env):
        mock_root = MagicMock()
        mock_span = MagicMock()
        mock_root.start_observation.return_value = mock_span
        lf_env["lf"].start_observation.return_value = mock_root
        writer.start_trace("sess-1")

        writer.log_span("sess-1", self._record(success=False))

        _, update_kwargs = mock_span.update.call_args
        assert update_kwargs.get("level") == "WARNING"


# ---------------------------------------------------------------------------
# end_trace
# ---------------------------------------------------------------------------


class TestEndTrace:
    def test_end_trace_closes_root_span(self, writer, lf_env):
        mock_root = MagicMock()
        lf_env["lf"].start_observation.return_value = mock_root
        writer.start_trace("sess-1")

        writer.end_trace(
            "sess-1",
            {
                "total_cost_usd": 0.01,
                "provider_calls": 1,
                "tool_calls": 2,
                "duration_s": 10.0,
            },
        )

        mock_root.end.assert_called_once()

    def test_end_trace_flushes(self, writer, lf_env):
        lf_env["lf"].start_observation.return_value = MagicMock()
        writer.start_trace("sess-1")

        writer.end_trace("sess-1", {})

        lf_env["lf"].flush.assert_called_once()

    def test_end_trace_removes_span(self, writer, lf_env):
        lf_env["lf"].start_observation.return_value = MagicMock()
        writer.start_trace("sess-1")
        assert "sess-1" in writer._spans

        writer.end_trace("sess-1", {})

        assert "sess-1" not in writer._spans

    def test_end_trace_removes_parent_session_tracking(self, writer, lf_env):
        # setup parent
        mock_parent = MagicMock()
        mock_child = MagicMock()
        mock_parent.start_observation.return_value = mock_child
        lf_env["lf"].start_observation.return_value = mock_parent
        writer.start_trace("parent-sess")
        writer.start_trace("child-sess", parent_session_id="parent-sess")
        assert "child-sess" in writer._parent_sessions

        writer.end_trace("child-sess", {})

        assert "child-sess" not in writer._parent_sessions

    def test_end_trace_unknown_session_is_noop(self, writer, lf_env):
        # Should not raise
        writer.end_trace("no-such-session", {})
        # flush still called
        lf_env["lf"].flush.assert_called_once()
