"""Unit tests for BoundedDict on_evict callback and edge cases."""

from __future__ import annotations

from src.utils import BoundedDict


class TestBoundedDictOnEvict:
    """Tests for the on_evict callback in BoundedDict."""

    def test_callback_receives_evicted_key_value(self):
        evicted: list[tuple] = []
        bd = BoundedDict(maxlen=2, on_evict=lambda k, v: evicted.append((k, v)))
        bd["a"] = 1
        bd["b"] = 2
        bd["c"] = 3  # evicts ("a", 1)

        assert evicted == [("a", 1)]

    def test_callback_called_on_each_eviction(self):
        evicted: list[tuple] = []
        bd = BoundedDict(maxlen=2, on_evict=lambda k, v: evicted.append((k, v)))
        bd["a"] = 1
        bd["b"] = 2
        bd["c"] = 3  # evicts ("a", 1)
        bd["d"] = 4  # evicts ("b", 2)

        assert evicted == [("a", 1), ("b", 2)]

    def test_callback_not_called_when_within_capacity(self):
        evicted: list[tuple] = []
        bd = BoundedDict(maxlen=5, on_evict=lambda k, v: evicted.append((k, v)))
        bd["a"] = 1
        bd["b"] = 2
        bd["c"] = 3

        assert evicted == []

    def test_callback_not_called_on_update(self):
        """Updating an existing key should NOT trigger on_evict."""
        evicted: list[tuple] = []
        bd = BoundedDict(maxlen=2, on_evict=lambda k, v: evicted.append((k, v)))
        bd["a"] = 1
        bd["b"] = 2
        bd["a"] = 99  # update, not eviction

        assert evicted == []

    def test_callback_exception_does_not_prevent_insertion(self):
        """A failing on_evict callback should not block the new item."""

        def failing_callback(k, v):
            raise RuntimeError("callback failed")

        bd = BoundedDict(maxlen=2, on_evict=failing_callback)
        bd["a"] = 1
        bd["b"] = 2
        bd["c"] = 3  # triggers eviction with failing callback

        # Despite callback failure, new item should still be inserted
        assert "c" in bd
        assert len(bd) == 2

    def test_no_callback_default(self):
        """BoundedDict should work fine without on_evict."""
        bd = BoundedDict(maxlen=2)
        bd["a"] = 1
        bd["b"] = 2
        bd["c"] = 3

        assert "c" in bd
        assert "a" not in bd

    def test_eviction_order_is_fifo(self):
        """Eviction should follow FIFO — oldest insertion removed first."""
        evict_order: list[str] = []
        bd = BoundedDict(maxlen=3, on_evict=lambda k, v: evict_order.append(k))
        bd["a"] = 1
        bd["b"] = 2
        bd["c"] = 3
        bd["d"] = 4  # evicts "a"
        bd["e"] = 5  # evicts "b"
        bd["f"] = 6  # evicts "c"

        assert evict_order == ["a", "b", "c"]

    def test_eviction_after_move_to_end(self):
        """Accessing an existing key moves it; eviction should skip it."""
        evicted_keys: list[str] = []
        bd = BoundedDict(maxlen=3, on_evict=lambda k, v: evicted_keys.append(k))
        bd["a"] = 1
        bd["b"] = 2
        bd["c"] = 3
        bd["a"] = 10  # move "a" to end; order is now b, c, a
        bd["d"] = 4  # evicts "b" (now oldest)

        assert evicted_keys == ["b"]
        assert list(bd.keys()) == ["c", "a", "d"]


class TestBoundedDictPopNoneDefault:
    """Test pop with None default (third overload)."""

    def test_pop_missing_with_none_default(self):
        bd = BoundedDict(maxlen=5)
        result = bd.pop("missing", None)
        assert result is None

    def test_pop_existing_with_none_default(self):
        bd = BoundedDict(maxlen=5)
        bd["a"] = 42
        result = bd.pop("a", None)
        assert result == 42
        assert "a" not in bd


class TestBoundedDictTouch:
    """Tests for the touch() LRU-refresh method."""

    def test_touch_moves_key_to_end(self):
        bd = BoundedDict(maxlen=3)
        bd["a"] = 1
        bd["b"] = 2
        bd["c"] = 3
        bd.touch("a")  # move "a" to end; order is now b, c, a
        assert list(bd.keys()) == ["b", "c", "a"]

    def test_touch_prevents_eviction_of_active_key(self):
        evicted_keys: list[str] = []
        bd = BoundedDict(maxlen=3, on_evict=lambda k, v: evicted_keys.append(k))
        bd["a"] = 1
        bd["b"] = 2
        bd["c"] = 3
        bd.touch("a")  # refresh "a"; order is now b, c, a
        bd["d"] = 4  # evicts "b" (oldest), not "a"

        assert evicted_keys == ["b"]
        assert "a" in bd

    def test_touch_missing_key_raises(self):
        bd = BoundedDict(maxlen=3)
        import pytest

        with pytest.raises(KeyError):
            bd.touch("missing")
