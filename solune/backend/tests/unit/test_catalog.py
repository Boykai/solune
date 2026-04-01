"""Tests for the Awesome Copilot catalog reader (src/services/agents/catalog.py).

Covers:
- _parse_catalog_index() — parsing llms.txt blocks into CatalogAgent objects
- list_catalog_agents()  — DB integration to mark already-imported agents
- fetch_agent_raw_content() — raw markdown fetch (mocked HTTP)
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.models.agents import CatalogAgent
from src.services.agents.catalog import (
    _parse_catalog_index,
    fetch_agent_raw_content,
    list_catalog_agents,
)
from src.services.cache import InMemoryCache


# ── _parse_catalog_index ─────────────────────────────────────────────────


class TestParseCatalogIndex:
    """Unit tests for the llms.txt parser."""

    def test_parses_single_agent(self):
        raw = "# My Agent\n> Helpful assistant\nhttps://example.com/agent.md\n"
        result = _parse_catalog_index(raw)
        assert len(result) == 1
        assert result[0].name == "My Agent"
        assert result[0].description == "Helpful assistant"
        assert result[0].source_url == "https://example.com/agent.md"
        assert result[0].id == "my-agent"

    def test_parses_multiple_agents(self):
        raw = (
            "# Alpha\n> First agent\nhttps://example.com/alpha.md\n\n"
            "# Beta\n> Second agent\nhttps://example.com/beta.md\n"
        )
        result = _parse_catalog_index(raw)
        assert len(result) == 2
        assert result[0].name == "Alpha"
        assert result[1].name == "Beta"

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
        raw = "# Solo Agent\nhttps://example.com/solo.md\n"
        result = _parse_catalog_index(raw)
        assert len(result) == 1
        assert result[0].description == "Solo Agent"

    def test_slug_strips_special_chars(self):
        raw = "# My Agent (v2.0)!\nhttps://example.com/agent.md\n"
        result = _parse_catalog_index(raw)
        assert result[0].id == "my-agent-v2-0"

    def test_skips_duplicate_headers_in_block(self):
        """Only the first '# ' line in a block is taken as the name."""
        raw = "# First\n# Second\nhttps://example.com/first.md\n"
        result = _parse_catalog_index(raw)
        assert len(result) == 1
        assert result[0].name == "First"


# ── list_catalog_agents ──────────────────────────────────────────────────


class TestListCatalogAgents:
    """Integration tests for list_catalog_agents with DB already-imported marking."""

    @pytest.fixture
    def test_cache(self):
        return InMemoryCache()

    async def test_marks_already_imported(self, mock_db, test_cache):
        """Agents already in the project DB have already_imported=True."""
        test_cache.set(
            "catalog:awesome-copilot:agents",
            "# Alpha\n> First agent\nhttps://example.com/alpha.md\n\n"
            "# Beta\n> Second agent\nhttps://example.com/beta.md\n",
        )

        # Insert an imported agent matching "alpha"
        await mock_db.execute(
            """INSERT INTO agent_configs
               (id, name, slug, description, system_prompt, status_column,
                tools, project_id, owner, repo, created_by,
                created_at, lifecycle_status, catalog_agent_id, agent_type)
               VALUES ('a1', 'Alpha', 'alpha', 'First agent', '', '', '[]',
                       'proj-1', 'owner', 'repo', 'user1',
                       datetime('now'), 'imported', 'alpha', 'imported')""",
        )
        await mock_db.commit()

        result = await list_catalog_agents("proj-1", mock_db, cache_instance=test_cache)
        alpha = next(a for a in result if a.id == "alpha")
        beta = next(a for a in result if a.id == "beta")
        assert alpha.already_imported is True
        assert beta.already_imported is False

    async def test_returns_empty_when_no_catalog(self, mock_db, test_cache):
        """Returns empty list when cache has empty content."""
        test_cache.set("catalog:awesome-copilot:agents", "")
        result = await list_catalog_agents("proj-1", mock_db, cache_instance=test_cache)
        assert result == []


# ── fetch_agent_raw_content ──────────────────────────────────────────────


class TestFetchAgentRawContent:
    async def test_returns_raw_text(self):
        """fetch_agent_raw_content returns HTTP response text."""
        import httpx

        mock_response = httpx.Response(
            200,
            text="---\nname: Test\n---\nAgent content",
            request=httpx.Request("GET", "https://example.com/agent.md"),
        )

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            content = await fetch_agent_raw_content("https://example.com/agent.md")
            assert content == "---\nname: Test\n---\nAgent content"
