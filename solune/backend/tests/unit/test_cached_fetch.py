"""Unit tests for cached_fetch() utility function."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from src.utils import cached_fetch


class TestCachedFetch:
    """Tests for the cached_fetch cache-or-fetch pattern."""

    @pytest.fixture(autouse=True)
    def _fresh_cache(self):
        """Provide a clean cache for each test."""
        with patch("src.services.cache.cache") as mock_cache:
            mock_cache.get.return_value = None
            self.mock_cache = mock_cache
            yield

    async def test_cache_miss_calls_fetch_fn(self):
        fetch_fn = AsyncMock(return_value={"data": 42})

        result = await cached_fetch("key", fetch_fn, "arg1")

        assert result == {"data": 42}
        fetch_fn.assert_awaited_once_with("arg1")
        self.mock_cache.set.assert_called_once_with("key", {"data": 42})

    async def test_cache_hit_returns_cached_value(self):
        self.mock_cache.get.return_value = {"cached": True}
        fetch_fn = AsyncMock(return_value={"fresh": True})

        result = await cached_fetch("key", fetch_fn)

        assert result == {"cached": True}
        fetch_fn.assert_not_awaited()

    async def test_refresh_bypasses_cache(self):
        self.mock_cache.get.return_value = {"cached": True}
        fetch_fn = AsyncMock(return_value={"fresh": True})

        result = await cached_fetch("key", fetch_fn, refresh=True)

        assert result == {"fresh": True}
        self.mock_cache.get.assert_not_called()
        fetch_fn.assert_awaited_once()

    async def test_passes_multiple_args_to_fetch_fn(self):
        fetch_fn = AsyncMock(return_value="result")

        await cached_fetch("key", fetch_fn, "a", "b", "c")

        fetch_fn.assert_awaited_once_with("a", "b", "c")

    async def test_stores_result_in_cache_after_fetch(self):
        fetch_fn = AsyncMock(return_value=[1, 2, 3])

        await cached_fetch("my_key", fetch_fn)

        self.mock_cache.set.assert_called_once_with("my_key", [1, 2, 3])
