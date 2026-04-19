"""Tests for src/services/resettable_state.py."""

from __future__ import annotations

import logging

from src.services.resettable_state import _registry, register_resettable, reset_all


class TestResettableStateRegistry:
    def setup_method(self):
        """Snapshot registry so tests don't pollute each other."""
        self._snapshot = list(_registry)

    def teardown_method(self):
        _registry.clear()
        _registry.extend(self._snapshot)

    # ── registration ─────────────────────────────────────────────────────

    def test_register_adds_entry(self):
        register_resettable("test.entry", lambda: None)
        assert any(name == "test.entry" for name, _ in _registry)

    def test_register_multiple_entries(self):
        register_resettable("a", lambda: None)
        register_resettable("b", lambda: None)
        names = [n for n, _ in _registry]
        assert "a" in names and "b" in names

    # ── reset_all ────────────────────────────────────────────────────────

    def test_reset_all_calls_every_reset_fn(self):
        called: list[str] = []
        register_resettable("first", lambda: called.append("first"))
        register_resettable("second", lambda: called.append("second"))

        reset_all()

        assert "first" in called and "second" in called

    def test_reset_all_resets_dict(self):
        data: dict[str, int] = {"key": 42}
        register_resettable("test.dict", data.clear)

        reset_all()

        assert data == {}

    def test_reset_all_continues_after_error(self, caplog):
        """A failing reset fn must not prevent subsequent entries from running."""
        called: list[str] = []

        def _fail() -> None:
            raise RuntimeError("boom")

        register_resettable("fail", _fail)
        register_resettable("ok", lambda: called.append("ok"))

        with caplog.at_level(logging.ERROR):
            reset_all()

        assert called == ["ok"], "Second entry was not called after first raised"
        assert "Failed to reset state: fail" in caplog.text

    def test_reset_all_logs_failing_entry_name(self, caplog):
        register_resettable("my.bad.state", lambda: 1 / 0)

        with caplog.at_level(logging.ERROR):
            reset_all()

        assert "my.bad.state" in caplog.text
