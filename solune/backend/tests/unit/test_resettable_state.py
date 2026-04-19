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

    # ── edge cases ───────────────────────────────────────────────────────

    def test_reset_all_on_empty_registry_is_noop(self):
        """reset_all() must not raise when the registry is empty."""
        _registry.clear()
        reset_all()  # should complete without error

    def test_registration_preserves_order(self):
        """reset_all() must call reset fns in the order they were registered."""
        order: list[str] = []
        register_resettable("first", lambda: order.append("first"))
        register_resettable("second", lambda: order.append("second"))
        register_resettable("third", lambda: order.append("third"))

        reset_all()

        assert order == ["first", "second", "third"]

    def test_reset_all_is_idempotent(self):
        """Calling reset_all() twice should invoke every fn each time."""
        counter = {"n": 0}
        register_resettable("counter", lambda: counter.__setitem__("n", counter["n"] + 1))

        reset_all()
        assert counter["n"] == 1

        reset_all()
        assert counter["n"] == 2

    def test_duplicate_names_are_both_called(self):
        """Two entries with the same name should both run."""
        called: list[str] = []
        register_resettable("dup", lambda: called.append("a"))
        register_resettable("dup", lambda: called.append("b"))

        reset_all()

        assert called == ["a", "b"]

    def test_reset_all_continues_past_multiple_failures(self, caplog):
        """All entries run even when multiple entries fail."""
        called: list[str] = []

        def _fail_value():
            raise ValueError("v")

        def _fail_type():
            raise TypeError("t")

        register_resettable("fail1", _fail_value)
        register_resettable("ok1", lambda: called.append("ok1"))
        register_resettable("fail2", _fail_type)
        register_resettable("ok2", lambda: called.append("ok2"))

        with caplog.at_level(logging.ERROR):
            reset_all()

        assert called == ["ok1", "ok2"]
        assert "fail1" in caplog.text
        assert "fail2" in caplog.text
