"""Awesome Copilot catalog reader — browse and fetch agent definitions.

Parses the cached ``llms.txt`` index from ``awesome-copilot.github.com``
for browsing/searching, and fetches raw agent markdown on demand when a
user imports a specific agent.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

import aiosqlite
import httpx
from fastapi import status

from src.config import get_settings
from src.exceptions import CatalogUnavailableError
from src.logging_utils import get_logger
from src.models.agents import CatalogAgent
from src.services.cache import InMemoryCache, cache, cached_fetch

logger = get_logger(__name__)

# ── Constants ────────────────────────────────────────────────────────────

CATALOG_CACHE_KEY = "catalog:awesome-copilot:agents"
CATALOG_CACHE_TTL = 3600  # 1 hour
_AGENTS_SECTION_HEADER = "## Agents"
_SECTION_HEADER_PREFIX = "## "
_AGENT_LIST_ITEM_RE = re.compile(
    r"^- \[(?P<name>[^\]]+)\]\((?P<url>https://[^)]+)\):\s*(?P<description>.+)$"
)

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


def _slugify_catalog_value(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _derive_catalog_agent_id(name: str, source_url: str) -> str | None:
    parsed = urlparse(source_url)
    filename = parsed.path.rsplit("/", 1)[-1]

    if filename:
        stem = re.sub(r"\.(agent|prompt|instructions)\.md$", "", filename, flags=re.IGNORECASE)
        stem = re.sub(r"\.md$", "", stem, flags=re.IGNORECASE)
        slug = _slugify_catalog_value(stem)
        if slug:
            return slug

    slug = _slugify_catalog_value(name)
    return slug or None


def _build_catalog_agent(name: str, description: str, source_url: str) -> CatalogAgent | None:
    """Create a catalog agent with a normalized slug, or return None when invalid."""
    slug = _derive_catalog_agent_id(name, source_url)
    if not slug:
        return None

    return CatalogAgent(
        id=slug,
        name=name,
        description=description or name,
        source_url=source_url,
    )


# ── Parsing ──────────────────────────────────────────────────────────────


def _parse_agents_section_index(raw_text: str) -> list[CatalogAgent]:
    """Parse the current root llms.txt format using the ``## Agents`` section."""
    agents: list[CatalogAgent] = []
    in_agents_section = False

    for raw_line in raw_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if line == _AGENTS_SECTION_HEADER:
            in_agents_section = True
            continue

        if line.startswith(_SECTION_HEADER_PREFIX):
            if in_agents_section:
                break
            continue

        if not in_agents_section:
            continue

        match = _AGENT_LIST_ITEM_RE.match(line)
        if not match:
            continue

        agent = _build_catalog_agent(
            match.group("name").strip(),
            match.group("description").strip(),
            match.group("url").strip(),
        )
        if agent is not None:
            agents.append(agent)

    return agents


def _parse_legacy_block_index(raw_text: str) -> list[CatalogAgent]:
    """Parse the legacy llms.txt block format used by older catalog indexes."""
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

        agent = _build_catalog_agent(name, description, source_url)
        if agent is not None:
            agents.append(agent)

    return agents


def _map_catalog_fetch_error(exc: Exception) -> CatalogUnavailableError:
    """Translate upstream fetch failures into safe, user-facing catalog errors."""
    if isinstance(exc, httpx.HTTPStatusError):
        upstream_status = exc.response.status_code
        reason = f"The Awesome Copilot catalog returned HTTP {upstream_status}."
        if upstream_status == status.HTTP_404_NOT_FOUND:
            reason = "The Awesome Copilot catalog index could not be found upstream."
        return CatalogUnavailableError(
            status_code=status.HTTP_502_BAD_GATEWAY,
            details={
                "reason": reason,
                "upstream_status": upstream_status,
            },
        )

    if isinstance(exc, httpx.TimeoutException):
        reason = "The Awesome Copilot catalog timed out. Retry in a moment."
    elif isinstance(exc, httpx.ConnectError):
        reason = "The Awesome Copilot catalog could not be reached. Retry in a moment."
    elif isinstance(exc, httpx.RequestError):
        reason = "The Awesome Copilot catalog request failed before a response was received."
    else:
        reason = "The Awesome Copilot catalog could not be loaded right now."

    return CatalogUnavailableError(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        details={"reason": reason},
    )


def _parse_catalog_index(raw_text: str) -> list[CatalogAgent]:
    """Parse the llms.txt index into ``CatalogAgent`` objects.

    The current upstream root index stores agents in the ``## Agents``
    section as markdown list items. Older indexes used blank-line-separated
    blocks with a ``# Agent Name`` header, optional ``> Description`` line,
    and a raw URL line.

    We accept both formats so cached legacy data remains readable while the
    live upstream root index continues to work.
    """
    if not raw_text or not raw_text.strip():
        return []

    agents = _parse_agents_section_index(raw_text)
    if agents:
        return agents

    return _parse_legacy_block_index(raw_text)


# ── Fetching ─────────────────────────────────────────────────────────────


async def _fetch_catalog_index() -> str:
    """Fetch the raw llms.txt content from the Awesome Copilot site."""
    settings = get_settings()

    async with httpx.AsyncClient(
        timeout=settings.catalog_fetch_timeout_seconds,
        follow_redirects=True,
    ) as client:
        resp = await client.get(settings.catalog_index_url)
        resp.raise_for_status()
        return resp.text


async def fetch_agent_raw_content(source_url: str) -> str:
    """Fetch the raw markdown content for a specific agent.

    This is called at import time to snapshot the agent definition.
    The *source_url* is validated against an allowlist before the request.
    """
    validate_source_url(source_url)

    settings = get_settings()

    async with httpx.AsyncClient(
        timeout=settings.catalog_fetch_timeout_seconds,
        follow_redirects=True,
    ) as client:
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

    try:
        raw_text: str = await cached_fetch(
            _cache,
            CATALOG_CACHE_KEY,
            _fetch_catalog_index,
            ttl_seconds=CATALOG_CACHE_TTL,
            stale_fallback=True,
        )
    except httpx.HTTPError as exc:
        logger.warning("Catalog index fetch failed", exc_info=True)
        raise _map_catalog_fetch_error(exc) from exc

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
