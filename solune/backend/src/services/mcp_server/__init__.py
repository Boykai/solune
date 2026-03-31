"""Solune MCP Server package.

Exposes Solune's capabilities as an MCP (Model Context Protocol) server
using the ``mcp`` Python SDK's ``FastMCP`` class.  The server is mounted
into the existing FastAPI application at ``/api/v1/mcp`` when the
``mcp_server_enabled`` feature flag is ``True``.

All MCP tools delegate to the same service layer used by the REST API
and internal agent ``@tool`` functions — single source of truth.
"""

from src.services.mcp_server.server import create_mcp_server, get_mcp_app

__all__ = ["create_mcp_server", "get_mcp_app"]
