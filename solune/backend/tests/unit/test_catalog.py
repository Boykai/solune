"""Tests for the Awesome Copilot catalog reader (src/services/agents/catalog.py).

Covers:
- _parse_catalog_index() — parsing llms.txt blocks into CatalogAgent objects
- list_catalog_agents()  — DB integration to mark already-imported agents
- fetch_agent_raw_content() — raw markdown fetch (mocked HTTP)
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from src.exceptions import CatalogUnavailableError
from src.services.agents.catalog import (
    CATALOG_CACHE_KEY,
    _fetch_catalog_index,
    _parse_catalog_index,
    fetch_agent_raw_content,
    list_catalog_agents,
)
from src.services.cache import InMemoryCache

ROOT_INDEX_SAMPLE = """# Awesome GitHub Copilot

## Overview

- **Agents**: Specialized GitHub Copilot agents

## Agents

- [Agent Alpha](https://raw.githubusercontent.com/github/awesome-copilot/main/agents/agent-alpha.agent.md): First catalog agent.
- [Agent Beta](https://raw.githubusercontent.com/github/awesome-copilot/main/agents/agent-beta.agent.md): Second catalog agent.

## Instructions

- [Rules](https://raw.githubusercontent.com/github/awesome-copilot/main/instructions/rules.instructions.md): Shared instructions.
"""

# ── _parse_catalog_index ─────────────────────────────────────────────────


class TestParseCatalogIndex:
    """Unit tests for the llms.txt parser."""

    def test_parses_single_agent(self):
        raw = "# My Agent\n> Helpful assistant\nhttps://example.com/agents/my-agent.agent.md\n"
        result = _parse_catalog_index(raw)
        assert len(result) == 1
        assert result[0].name == "My Agent"
        assert result[0].description == "Helpful assistant"
        assert result[0].source_url == "https://example.com/agents/my-agent.agent.md"
        assert result[0].id == "my-agent"

    def test_parses_multiple_agents(self):
        raw = (
            "# Alpha\n> First agent\nhttps://example.com/agents/alpha.agent.md\n\n"
            "# Beta\n> Second agent\nhttps://example.com/agents/beta.agent.md\n"
        )
        result = _parse_catalog_index(raw)
        assert len(result) == 2
        assert result[0].name == "Alpha"
        assert result[1].name == "Beta"

    def test_parses_agents_section_from_root_index(self):
        result = _parse_catalog_index(ROOT_INDEX_SAMPLE)
        assert len(result) == 2
        assert result[0].name == "Agent Alpha"
        assert result[0].description == "First catalog agent."
        assert result[1].name == "Agent Beta"
        assert result[1].source_url.endswith("agent-beta.agent.md")

    def test_skips_blocks_without_name(self):
        raw = "> Just a description\nhttps://example.com/agent.md\n"
        result = _parse_catalog_index(raw)
        assert result == []

    def test_skips_blocks_without_url(self):
        raw = "# Agent Without URL\n> Has description but no link\n"
        result = _parse_catalog_index(raw)
        assert result == []

    def test_empty_string_returns_empty_list(self):
        assert _parse_catalog_index("") == []

    def test_whitespace_only_returns_empty_list(self):
        assert _parse_catalog_index("   \n  \n  ") == []

    def test_description_defaults_to_name(self):
        raw = "# Solo Agent\nhttps://example.com/agents/solo-agent.agent.md\n"
        result = _parse_catalog_index(raw)
        assert len(result) == 1
        assert result[0].description == "Solo Agent"

    def test_slug_strips_special_chars(self):
        raw = "# My Agent (v2.0)!\nhttps://example.com/agents/my-agent-v2-0.agent.md\n"
        result = _parse_catalog_index(raw)
        assert result[0].id == "my-agent-v2-0"

    def test_skips_duplicate_headers_in_block(self):
        """Only the first '# ' line in a block is taken as the name."""
        raw = "# First\n# Second\nhttps://example.com/first.md\n"
        result = _parse_catalog_index(raw)
        assert len(result) == 1
        assert result[0].name == "First"

    def test_prefers_source_url_for_stable_id(self):
        raw = (
            "# Agent Alpha Renamed\n> Same agent, new title\n"
            "https://example.com/agents/agent-alpha.agent.md\n"
        )
        result = _parse_catalog_index(raw)
        assert len(result) == 1
        assert result[0].id == "agent-alpha"


# ── list_catalog_agents ──────────────────────────────────────────────────


class TestListCatalogAgents:
    """Integration tests for list_catalog_agents with DB already-imported marking."""

    @pytest.fixture
    def test_cache(self):
        return InMemoryCache()

    async def test_marks_already_imported(self, mock_db, test_cache):
        """Agents already in the project DB have already_imported=True."""
        test_cache.set(CATALOG_CACHE_KEY, ROOT_INDEX_SAMPLE)

        # Insert an imported agent matching "agent-alpha"
        await mock_db.execute(
            """INSERT INTO agent_configs
               (id, name, slug, description, system_prompt, status_column,
                tools, project_id, owner, repo, created_by,
                created_at, lifecycle_status, catalog_agent_id, agent_type)
               VALUES ('a1', 'Alpha', 'alpha', 'First agent', '', '', '[]',
                       'proj-1', 'owner', 'repo', 'user1',
                       datetime('now'), 'imported', 'agent-alpha', 'imported')""",
        )
        await mock_db.commit()

        result = await list_catalog_agents("proj-1", mock_db, cache_instance=test_cache)
        alpha = next(a for a in result if a.id == "agent-alpha")
        beta = next(a for a in result if a.id == "agent-beta")
        assert alpha.already_imported is True
        assert beta.already_imported is False

    async def test_returns_empty_when_no_catalog(self, mock_db, test_cache):
        """Returns empty list when cache has empty content."""
        test_cache.set(CATALOG_CACHE_KEY, "")
        result = await list_catalog_agents("proj-1", mock_db, cache_instance=test_cache)
        assert result == []

    async def test_uses_stale_cache_when_upstream_fetch_fails(self, mock_db, test_cache):
        """Expired catalog data is still returned when the upstream request fails."""
        test_cache.set(CATALOG_CACHE_KEY, ROOT_INDEX_SAMPLE, ttl_seconds=-1)

        with patch(
            "src.services.agents.catalog._fetch_catalog_index",
            new_callable=AsyncMock,
            side_effect=httpx.TimeoutException("timed out"),
        ):
            result = await list_catalog_agents("proj-1", mock_db, cache_instance=test_cache)

        assert [agent.id for agent in result] == ["agent-alpha", "agent-beta"]

    async def test_raises_bad_gateway_when_upstream_returns_http_error(self, mock_db, test_cache):
        """HTTP errors from the upstream catalog become catalog availability errors."""
        request = httpx.Request("GET", "https://awesome-copilot.github.com/llms.txt")
        response = httpx.Response(status_code=404, request=request)

        with patch(
            "src.services.agents.catalog._fetch_catalog_index",
            new_callable=AsyncMock,
            side_effect=httpx.HTTPStatusError("not found", request=request, response=response),
        ):
            with pytest.raises(CatalogUnavailableError) as excinfo:
                await list_catalog_agents("proj-1", mock_db, cache_instance=test_cache)

        assert excinfo.value.status_code == 502
        assert excinfo.value.details["upstream_status"] == 404
        assert "could not be found upstream" in excinfo.value.details["reason"]

    async def test_raises_service_unavailable_when_upstream_times_out(self, mock_db, test_cache):
        """Timeouts without stale data become service-unavailable catalog errors."""
        with patch(
            "src.services.agents.catalog._fetch_catalog_index",
            new_callable=AsyncMock,
            side_effect=httpx.TimeoutException("timed out"),
        ):
            with pytest.raises(CatalogUnavailableError) as excinfo:
                await list_catalog_agents("proj-1", mock_db, cache_instance=test_cache)

        assert excinfo.value.status_code == 503
        assert "timed out" in excinfo.value.details["reason"].lower()

    async def test_unexpected_fetch_errors_propagate(self, mock_db, test_cache):
        """Non-HTTP failures should bubble up as generic server errors."""
        with patch(
            "src.services.agents.catalog._fetch_catalog_index",
            new_callable=AsyncMock,
            side_effect=RuntimeError("parser exploded"),
        ):
            with pytest.raises(RuntimeError, match="parser exploded"):
                await list_catalog_agents("proj-1", mock_db, cache_instance=test_cache)


# ── fetch_agent_raw_content ──────────────────────────────────────────────


class TestFetchAgentRawContent:
    async def test_fetch_catalog_index_follows_redirects(self):
        """Catalog index fetches should follow redirects from upstream hosts."""
        settings = SimpleNamespace(
            catalog_fetch_timeout_seconds=7,
            catalog_index_url="https://awesome-copilot.github.com/llms.txt",
        )
        mock_response = httpx.Response(
            200,
            text=ROOT_INDEX_SAMPLE,
            request=httpx.Request("GET", settings.catalog_index_url),
        )

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("src.services.agents.catalog.get_settings", return_value=settings),
            patch("httpx.AsyncClient", return_value=mock_client) as async_client,
        ):
            content = await _fetch_catalog_index()

        async_client.assert_called_once_with(timeout=7, follow_redirects=True)
        mock_client.get.assert_awaited_once_with(settings.catalog_index_url)
        assert content == ROOT_INDEX_SAMPLE

    async def test_returns_raw_text(self):
        """fetch_agent_raw_content returns HTTP response text."""
        settings = SimpleNamespace(catalog_fetch_timeout_seconds=9)

        mock_response = httpx.Response(
            200,
            text="---\nname: Test\n---\nAgent content",
            request=httpx.Request(
                "GET",
                "https://raw.githubusercontent.com/github/awesome-copilot/main/agents/test.agent.md",
            ),
        )

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("src.services.agents.catalog.get_settings", return_value=settings),
            patch("httpx.AsyncClient", return_value=mock_client) as async_client,
        ):
            content = await fetch_agent_raw_content(
                "https://raw.githubusercontent.com/github/awesome-copilot/main/agents/test.agent.md"
            )
            assert content == "---\nname: Test\n---\nAgent content"

        async_client.assert_called_once_with(timeout=9, follow_redirects=True)
