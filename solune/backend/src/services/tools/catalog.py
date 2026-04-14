"""MCP catalog service — browse and import external MCP servers from Glama.

Proxies the public Glama API to let users discover MCP servers, then maps
their install configs into the existing ``McpToolConfig`` persistence model.
"""

from __future__ import annotations

import json
import re
from urllib.parse import urlparse

import httpx
from fastapi import status

from src.exceptions import CatalogUnavailableError, ValidationError
from src.logging_utils import get_logger
from src.models.tools import (
    CatalogInstallConfig,
    CatalogMcpServer,
    CatalogMcpServerListResponse,
    McpToolConfigCreate,
)
from src.services.cache import InMemoryCache, cache, cached_fetch

logger = get_logger(__name__)

# ── Constants ────────────────────────────────────────────────────────────

GLAMA_BASE_URL = "https://glama.ai/api/mcp/v1/servers"
CATALOG_CACHE_KEY = "catalog:mcp:glama"
CATALOG_CACHE_TTL = 3600  # 1 hour
_GLAMA_FETCH_TIMEOUT = 15.0  # seconds

_ALLOWED_UPSTREAM_HOSTS = frozenset({"glama.ai"})

_SUPPORTED_TRANSPORTS = frozenset({"http", "sse", "stdio", "local"})


def _slugify(value: str) -> str:
    """Create a URL-safe slug from a display name."""
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _sanitize_repo_url(url: object) -> str | None:
    """Return a safe external repository URL or ``None`` when invalid."""
    if not isinstance(url, str):
        return None

    candidate = url.strip()
    if not candidate:
        return None

    parsed = urlparse(candidate)
    if parsed.scheme != "https" or not parsed.netloc:
        return None

    return parsed.geturl()


# ── Upstream validation ──────────────────────────────────────────────────


def validate_upstream_url(url: str) -> None:
    """Ensure *url* is HTTPS and points to an allowed host (SSRF mitigation)."""
    try:
        parsed = urlparse(url)
    except Exception as exc:
        raise ValueError(f"Invalid upstream URL: {exc}") from exc

    if parsed.scheme != "https":
        raise ValueError("Only HTTPS upstream URLs are allowed.")
    if parsed.hostname not in _ALLOWED_UPSTREAM_HOSTS:
        raise ValueError(f"Upstream host '{parsed.hostname}' is not in the allowed list.")
    if parsed.port is not None and parsed.port != 443:
        raise ValueError("Only standard HTTPS port (443) is allowed for upstream URLs.")


# ── Upstream fetching ────────────────────────────────────────────────────


async def _fetch_glama_servers(
    query: str = "",
    category: str = "",
) -> list[dict]:
    """Fetch servers from the Glama MCP API."""
    params: dict[str, str] = {}
    if query:
        params["query"] = query
    if category:
        params["category"] = category

    url = GLAMA_BASE_URL
    validate_upstream_url(url)

    async with httpx.AsyncClient(
        timeout=_GLAMA_FETCH_TIMEOUT,
        follow_redirects=False,
    ) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        try:
            data = resp.json()
        except json.JSONDecodeError as exc:
            raise CatalogUnavailableError(
                "MCP catalog upstream returned an invalid response.",
                status_code=status.HTTP_502_BAD_GATEWAY,
                details={"reason": "The MCP catalog returned invalid JSON."},
            ) from exc

    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("servers", data.get("data", []))
    return []


def _normalize_server(raw: dict) -> CatalogMcpServer | None:
    """Parse a single upstream Glama server entry into a catalog model."""
    name = raw.get("name") or raw.get("title") or ""
    if not name:
        return None

    server_id = raw.get("id") or _slugify(name)
    if not server_id:
        return None

    description = raw.get("description") or raw.get("summary") or name
    repo_url = _sanitize_repo_url(
        raw.get("repo_url") or raw.get("repository") or raw.get("github_url")
    )

    # Extract category: prefer explicit field, fall back to first tag
    tags = raw.get("tags")
    if isinstance(tags, list) and tags:
        category = raw.get("category") or tags[0]
    else:
        category = raw.get("category")

    quality_score = raw.get("quality_score") or raw.get("quality") or raw.get("score")
    if quality_score is not None:
        quality_score = str(quality_score)

    # Parse install config
    raw_config = raw.get("install_config") or raw.get("config") or {}
    if isinstance(raw_config, str):
        try:
            raw_config = json.loads(raw_config)
        except json.JSONDecodeError:
            raw_config = {}

    transport = raw_config.get("transport") or raw_config.get("type") or ""
    url_val = raw_config.get("url")
    command = raw_config.get("command")
    args = raw_config.get("args", [])
    env = raw_config.get("env", {})
    headers = raw_config.get("headers", {})
    tools = raw_config.get("tools", [])

    # Infer transport from fields when not explicitly set
    if not transport:
        if command:
            transport = "stdio"
        elif url_val:
            transport = "http"
        else:
            transport = "unknown"

    # Determine server_type badge
    server_type = transport if transport in _SUPPORTED_TRANSPORTS else "remote"

    install_config = CatalogInstallConfig(
        transport=transport,
        url=url_val,
        command=command,
        args=args if isinstance(args, list) else [],
        env=env if isinstance(env, dict) else {},
        headers=headers if isinstance(headers, dict) else {},
        tools=tools if isinstance(tools, list) else [],
    )

    return CatalogMcpServer(
        id=str(server_id),
        name=name,
        description=str(description),
        repo_url=str(repo_url) if repo_url else None,
        category=str(category) if category else None,
        server_type=server_type,
        install_config=install_config,
        quality_score=quality_score,
        already_installed=False,
    )


def _map_catalog_fetch_error(exc: Exception) -> CatalogUnavailableError:
    """Translate upstream fetch failures into user-facing catalog errors."""
    if isinstance(exc, httpx.HTTPStatusError):
        upstream_status = exc.response.status_code
        reason = f"The MCP catalog returned HTTP {upstream_status}."
        if upstream_status == status.HTTP_404_NOT_FOUND:
            reason = "The MCP catalog index could not be found upstream."
        return CatalogUnavailableError(
            "MCP catalog is temporarily unavailable.",
            status_code=status.HTTP_502_BAD_GATEWAY,
            details={"reason": reason, "upstream_status": upstream_status},
        )

    if isinstance(exc, httpx.TimeoutException):
        reason = "The MCP catalog timed out. Retry in a moment."
    elif isinstance(exc, httpx.ConnectError):
        reason = "The MCP catalog could not be reached. Retry in a moment."
    elif isinstance(exc, httpx.RequestError):
        reason = "The MCP catalog request failed before a response was received."
    else:
        reason = "The MCP catalog could not be loaded right now."

    return CatalogUnavailableError(
        "MCP catalog is temporarily unavailable.",
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        details={"reason": reason},
    )


# ── Public API ───────────────────────────────────────────────────────────


async def list_catalog_servers(
    project_id: str,
    existing_tool_names: set[str],
    *,
    query: str = "",
    category: str = "",
    cache_instance: InMemoryCache | None = None,
) -> CatalogMcpServerListResponse:
    """Return catalog MCP servers with ``already_installed`` flags set.

    Uses :func:`cached_fetch` with stale-fallback so the browse section
    stays functional even when the upstream catalog is temporarily unreachable.
    """
    _cache = cache_instance or cache
    cache_key = f"{CATALOG_CACHE_KEY}:{query or ''}:{category or ''}"

    try:
        raw_servers: list[dict] = await cached_fetch(
            _cache,
            cache_key,
            lambda: _fetch_glama_servers(query=query, category=category),
            ttl_seconds=CATALOG_CACHE_TTL,
            stale_fallback=True,
        )
    except CatalogUnavailableError:
        raise
    except httpx.HTTPError as exc:
        logger.warning("MCP catalog fetch failed", exc_info=True)
        raise _map_catalog_fetch_error(exc) from exc

    servers: list[CatalogMcpServer] = []
    normalized_names = {n.lower().strip() for n in existing_tool_names}

    for raw in raw_servers:
        server = _normalize_server(raw)
        if server is None:
            continue
        if server.name.lower().strip() in normalized_names:
            server.already_installed = True
        servers.append(server)

    return CatalogMcpServerListResponse(
        servers=servers,
        count=len(servers),
        query=query or None,
        category=category or None,
    )


def build_import_config(server: CatalogMcpServer) -> McpToolConfigCreate:
    """Map a catalog server's install config into a ``McpToolConfigCreate``.

    Produces a standard ``mcpServers`` JSON snippet that the existing
    tool CRUD/sync flow accepts.
    """
    cfg = server.install_config
    transport = cfg.transport.lower()
    server_name = _slugify(server.name) or "imported-server"

    if transport in ("http", "sse"):
        if not cfg.url:
            raise ValidationError(f"Catalog server '{server.name}' ({transport}) requires a URL.")
        server_config: dict[str, object] = {"type": transport, "url": cfg.url}
        if cfg.headers:
            server_config["headers"] = cfg.headers
        if cfg.tools:
            server_config["tools"] = cfg.tools
        if cfg.env:
            server_config["env"] = cfg.env

    elif transport in ("stdio", "local"):
        if not cfg.command:
            raise ValidationError(
                f"Catalog server '{server.name}' ({transport}) requires a command."
            )
        server_config = {"type": transport, "command": cfg.command}
        if cfg.args:
            server_config["args"] = cfg.args
        if cfg.env:
            server_config["env"] = cfg.env
        if cfg.tools:
            server_config["tools"] = cfg.tools

    else:
        raise ValidationError(
            f"Unsupported transport '{transport}' for catalog server '{server.name}'."
        )

    config_content = (
        json.dumps(
            {"mcpServers": {server_name: server_config}},
            indent=2,
        )
        + "\n"
    )

    return McpToolConfigCreate(
        name=server.name,
        description=server.description,
        config_content=config_content,
        github_repo_target="",
    )
