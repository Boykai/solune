"""Awesome Copilot catalog reader — browse and fetch agent definitions.

Parses the cached ``llms.txt`` index from ``awesome-copilot.github.com``
for browsing/searching, and fetches raw agent markdown on demand when a
user imports a specific agent.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

import aiosqlite

from src.logging_utils import get_logger
from src.models.agents import CatalogAgent
from src.services.cache import InMemoryCache, cache, cached_fetch

logger = get_logger(__name__)

# ── Constants ────────────────────────────────────────────────────────────

CATALOG_INDEX_URL = "https://awesome-copilot.github.com/agents/llms.txt"
CATALOG_CACHE_KEY = "catalog:awesome-copilot:agents"
CATALOG_CACHE_TTL = 3600  # 1 hour

# Allowlisted hosts for fetching raw agent content (SSRF mitigation)
_ALLOWED_SOURCE_HOSTS = frozenset(
    {
        "raw.githubusercontent.com",
        "awesome-copilot.github.com",
        "github.com",
    }
)


def validate_source_url(url: str) -> None:
    """Validate that *url* points to an allowed host with HTTPS scheme.

    Raises :class:`ValueError` when the URL is invalid or not allowlisted.
    """
    try:
        parsed = urlparse(url)
    except Exception as exc:
        raise ValueError(f"Invalid source URL: {exc}") from exc

    if parsed.scheme != "https":
        raise ValueError("Only HTTPS source URLs are allowed.")
    if parsed.hostname not in _ALLOWED_SOURCE_HOSTS:
        raise ValueError(f"Source URL host '{parsed.hostname}' is not in the allowed list.")


# ── Parsing ──────────────────────────────────────────────────────────────


def _parse_catalog_index(raw_text: str) -> list[CatalogAgent]:
    """Parse the llms.txt index into ``CatalogAgent`` objects.

    The llms.txt format consists of blocks separated by blank lines.
    Each block has:
    - Line 1: ``# Agent Name``
    - Line 2 (optional): ``> Description text``
    - A line containing the URL to the raw agent file

    We use a lenient parser that extracts as many valid entries as
    possible and skips malformed blocks.
    """
    if not raw_text or not raw_text.strip():
        return []

    agents: list[CatalogAgent] = []
    # Split on double-newlines (or more) to get blocks
    blocks = re.split(r"\n{2,}", raw_text.strip())

    for block in blocks:
        lines = [line.strip() for line in block.strip().splitlines() if line.strip()]
        if not lines:
            continue

        name: str | None = None
        description = ""
        source_url: str | None = None

        for line in lines:
            if line.startswith("# ") and name is None:
                name = line[2:].strip()
            elif line.startswith("> ") and not description:
                description = line[2:].strip()
            elif line.startswith("http") and source_url is None:
                source_url = line.strip()

        if not name or not source_url:
            continue

        # Derive slug from name
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        if not slug:
            continue

        if not description:
            description = name

        agents.append(
            CatalogAgent(
                id=slug,
                name=name,
                description=description,
                source_url=source_url,
            )
        )

    return agents


# ── Fetching ─────────────────────────────────────────────────────────────


async def _fetch_catalog_index() -> str:
    """Fetch the raw llms.txt content from the Awesome Copilot site."""
    import httpx

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(CATALOG_INDEX_URL)
        resp.raise_for_status()
        return resp.text


async def fetch_agent_raw_content(source_url: str) -> str:
    """Fetch the raw markdown content for a specific agent.

    This is called at import time to snapshot the agent definition.
    The *source_url* is validated against an allowlist before the request.
    """
    validate_source_url(source_url)

    import httpx

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(source_url)
        resp.raise_for_status()
        return resp.text


# ── Public API ───────────────────────────────────────────────────────────


async def list_catalog_agents(
    project_id: str,
    db: aiosqlite.Connection,
    *,
    cache_instance: InMemoryCache | None = None,
) -> list[CatalogAgent]:
    """Return catalog agents with ``already_imported`` flags set.

    Uses :func:`cached_fetch` with stale-fallback so the browse modal
    stays functional even when the upstream index is temporarily unreachable.
    """
    _cache = cache_instance or cache

    raw_text: str = await cached_fetch(
        _cache,
        CATALOG_CACHE_KEY,
        _fetch_catalog_index,
        ttl_seconds=CATALOG_CACHE_TTL,
        stale_fallback=True,
    )

    agents = _parse_catalog_index(raw_text)

    # Mark agents already imported into this project
    cursor = await db.execute(
        "SELECT catalog_agent_id FROM agent_configs WHERE project_id = ? AND catalog_agent_id IS NOT NULL",
        (project_id,),
    )
    imported_ids = {row[0] for row in await cursor.fetchall()}

    for agent in agents:
        if agent.id in imported_ids:
            agent.already_imported = True

    return agents
