"""Shared test fixtures and mocks for hook-observability tests."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Mock amplifier_core (peer dep not installed in dev/test)
# ---------------------------------------------------------------------------


class _HookResult:
    def __init__(self, action: str = "continue") -> None:
        self.action = action


_mock_amplifier_core = MagicMock()
_mock_amplifier_core.HookResult = _HookResult
sys.modules.setdefault("amplifier_core", _mock_amplifier_core)


# ---------------------------------------------------------------------------
# Coordinator fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def coordinator():
    """Minimal mock coordinator with hooks registration."""
    hooks = MagicMock()
    registered: dict = {}

    def _register(event, handler, priority=50, name=""):
        registered.setdefault(event, []).append((priority, name, handler))

    hooks.register = _register
    hooks._registered = registered

    coord = MagicMock()
    coord.hooks = hooks
    coord.session_id = "test-session-123"
    coord.parent_id = None
    return coord


@pytest.fixture
def get_handlers(coordinator):
    """Helper: return the registered handlers for a given event."""

    def _get(event: str):
        return [h for _, _, h in coordinator.hooks._registered.get(event, [])]

    return _get
