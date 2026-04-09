"""Tests for MCP store operations (src/services/mcp_store.py).

Covers:
- validate_url_not_ssrf — SSRF validation for MCP endpoint URLs
  - Scheme enforcement (http/https only)
  - Private/reserved/loopback/link-local/unspecified IP rejection
  - Hostname normalization (trailing dot, case-insensitive)
  - Localhost pattern matching (localhost, localhost.localdomain)
  - 0.0.0.0 (unspecified address) rejection
  - Valid public URLs pass through
- create_mcp — per-user MCP limit enforcement
- list_mcps  — listing user-scoped MCPs
- delete_mcp — ownership-scoped deletion
- update_mcp — optimistic concurrency with collision detection
"""

import pytest

from src.exceptions import McpLimitExceededError, McpValidationError
from src.models.mcp import McpConfigurationCreate, McpConfigurationUpdate
from src.services.mcp_store import (
    MAX_MCPS_PER_USER,
    create_mcp,
    delete_mcp,
    list_mcps,
    update_mcp,
    validate_url_not_ssrf,
)

# ── validate_url_not_ssrf ──────────────────────────────────────────────────


class TestValidateUrlNotSsrf:
    """Unit tests for the SSRF URL validation helper."""

    # ── Valid URLs that should pass ──

    @pytest.mark.parametrize(
        "url",
        [
            "https://example.com/mcp",
            "http://example.com/api/v1",
            "https://mcp.acme.io:8443/endpoint",
            "https://8.8.8.8/dns",
            "http://93.184.216.34/resource",
        ],
    )
    def test_valid_public_urls_pass(self, url: str):
        """Public HTTP(S) URLs should pass validation unchanged."""
        assert validate_url_not_ssrf(url) == url

    # ── Scheme enforcement ──

    @pytest.mark.parametrize(
        "url",
        [
            "ftp://example.com/file",
            "file:///etc/passwd",
            "gopher://evil.com",
            "javascript:alert(1)",
        ],
    )
    def test_rejects_non_http_schemes(self, url: str):
        """Non-HTTP(S) schemes must be rejected."""
        with pytest.raises(ValueError, match="Only http and https URLs are allowed"):
            validate_url_not_ssrf(url)

    # ── Missing hostname ──

    def test_rejects_url_without_hostname(self):
        """URLs without a hostname must be rejected."""
        with pytest.raises(ValueError, match="URL must have a valid hostname"):
            validate_url_not_ssrf("http:///no-host")

    # ── Private / reserved IPv4 ──

    @pytest.mark.parametrize(
        "ip",
        [
            "10.0.0.1",
            "172.16.0.1",
            "192.168.1.1",
        ],
    )
    def test_rejects_private_ipv4(self, ip: str):
        """Private IPv4 addresses (RFC 1918) must be blocked."""
        with pytest.raises(ValueError, match="private or reserved"):
            validate_url_not_ssrf(f"http://{ip}/api")

    # ── Loopback ──

    def test_rejects_ipv4_loopback(self):
        """127.0.0.1 (IPv4 loopback) must be blocked."""
        with pytest.raises(ValueError, match="private or reserved"):
            validate_url_not_ssrf("http://127.0.0.1/api")

    def test_rejects_ipv6_loopback(self):
        """::1 (IPv6 loopback) must be blocked."""
        with pytest.raises(ValueError, match="private or reserved"):
            validate_url_not_ssrf("http://[::1]/api")

    # ── Unspecified address (0.0.0.0) — critical SSRF bypass vector ──

    def test_rejects_unspecified_address(self):
        """0.0.0.0 resolves to the local machine on most OSes and must be blocked."""
        with pytest.raises(ValueError, match="private or reserved"):
            validate_url_not_ssrf("http://0.0.0.0/api")

    def test_rejects_ipv6_unspecified(self):
        """[::] (IPv6 unspecified) must be blocked."""
        with pytest.raises(ValueError, match="private or reserved"):
            validate_url_not_ssrf("http://[::]/api")

    # ── Link-local ──

    def test_rejects_link_local(self):
        """169.254.x.x (link-local) must be blocked."""
        with pytest.raises(ValueError, match="private or reserved"):
            validate_url_not_ssrf("http://169.254.169.254/latest/meta-data")

    # ── Localhost hostname variants ──

    def test_rejects_localhost(self):
        """Plain 'localhost' hostname must be blocked."""
        with pytest.raises(ValueError, match="private or reserved"):
            validate_url_not_ssrf("http://localhost/api")

    def test_rejects_localhost_with_trailing_dot(self):
        """'localhost.' (FQDN with trailing dot) must also be blocked."""
        with pytest.raises(ValueError, match="private or reserved"):
            validate_url_not_ssrf("http://localhost./api")

    def test_rejects_localhost_localdomain(self):
        """'localhost.localdomain' must be blocked (first label is localhost)."""
        with pytest.raises(ValueError, match="private or reserved"):
            validate_url_not_ssrf("http://localhost.localdomain/api")

    def test_rejects_localhost_case_insensitive(self):
        """Hostname normalisation should treat 'LOCALHOST' as 'localhost'."""
        with pytest.raises(ValueError, match="private or reserved"):
            validate_url_not_ssrf("http://LOCALHOST/api")

    # ── Reserved ──

    def test_rejects_reserved_ip(self):
        """240.0.0.1 is in the reserved range and must be blocked."""
        with pytest.raises(ValueError, match="private or reserved"):
            validate_url_not_ssrf("http://240.0.0.1/api")


# ── CRUD Operations ───────────────────────────────────────────────────────


class TestCreateMcp:
    """Tests for the create_mcp service function."""

    async def test_create_mcp_success(self, mock_db):
        """A valid MCP should be created and returned."""
        data = McpConfigurationCreate(name="Test MCP", endpoint_url="https://example.com/mcp")
        result = await create_mcp(mock_db, "user-1", data)

        assert result.name == "Test MCP"
        assert result.endpoint_url == "https://example.com/mcp"
        assert result.is_active is True
        assert result.id  # UUID generated

    async def test_create_mcp_ssrf_rejected(self, mock_db):
        """Creating an MCP with a private-IP URL raises McpValidationError."""
        data = McpConfigurationCreate(name="Bad MCP", endpoint_url="http://192.168.1.1/api")
        with pytest.raises(McpValidationError, match="private or reserved"):
            await create_mcp(mock_db, "user-1", data)

    async def test_create_mcp_limit_exceeded(self, mock_db):
        """Exceeding MAX_MCPS_PER_USER raises McpLimitExceededError."""
        data = McpConfigurationCreate(name="MCP", endpoint_url="https://example.com/mcp")
        for i in range(MAX_MCPS_PER_USER):
            await create_mcp(
                mock_db,
                "user-1",
                McpConfigurationCreate(
                    name=f"MCP {i}", endpoint_url=f"https://example.com/mcp/{i}"
                ),
            )

        with pytest.raises(McpLimitExceededError, match="Maximum of"):
            await create_mcp(mock_db, "user-1", data)

    async def test_create_mcp_limit_is_per_user(self, mock_db):
        """The MCP limit is per-user; a second user is unaffected."""
        for i in range(MAX_MCPS_PER_USER):
            await create_mcp(
                mock_db,
                "user-1",
                McpConfigurationCreate(
                    name=f"MCP {i}", endpoint_url=f"https://example.com/mcp/{i}"
                ),
            )

        # Different user should succeed
        data = McpConfigurationCreate(
            name="Other User MCP", endpoint_url="https://example.com/other"
        )
        result = await create_mcp(mock_db, "user-2", data)
        assert result.name == "Other User MCP"


class TestListMcps:
    """Tests for the list_mcps service function."""

    async def test_list_empty(self, mock_db):
        """Listing MCPs for a user with none returns an empty list."""
        result = await list_mcps(mock_db, "user-1")
        assert result.mcps == []
        assert result.count == 0

    async def test_list_returns_only_user_mcps(self, mock_db):
        """Listing MCPs only returns configurations owned by the specified user."""
        await create_mcp(
            mock_db,
            "user-1",
            McpConfigurationCreate(name="User1 MCP", endpoint_url="https://example.com/1"),
        )
        await create_mcp(
            mock_db,
            "user-2",
            McpConfigurationCreate(name="User2 MCP", endpoint_url="https://example.com/2"),
        )

        result = await list_mcps(mock_db, "user-1")
        assert result.count == 1
        assert result.mcps[0].name == "User1 MCP"


class TestDeleteMcp:
    """Tests for the delete_mcp service function."""

    async def test_delete_own_mcp(self, mock_db):
        """Users can delete their own MCP configurations."""
        created = await create_mcp(
            mock_db,
            "user-1",
            McpConfigurationCreate(name="To Delete", endpoint_url="https://example.com/del"),
        )

        assert await delete_mcp(mock_db, "user-1", created.id) is True

        # Verify it's gone
        result = await list_mcps(mock_db, "user-1")
        assert result.count == 0

    async def test_delete_nonexistent_returns_false(self, mock_db):
        """Deleting a non-existent MCP returns False (not found)."""
        assert await delete_mcp(mock_db, "user-1", "nonexistent-id") is False

    async def test_cannot_delete_other_users_mcp(self, mock_db):
        """Users cannot delete another user's MCP configuration."""
        created = await create_mcp(
            mock_db,
            "user-1",
            McpConfigurationCreate(name="Private MCP", endpoint_url="https://example.com/priv"),
        )

        # user-2 tries to delete user-1's MCP → returns False
        assert await delete_mcp(mock_db, "user-2", created.id) is False

        # MCP still exists for user-1
        result = await list_mcps(mock_db, "user-1")
        assert result.count == 1


# ── update_mcp — Optimistic Concurrency ──────────────────────────────────


class TestUpdateMcp:
    """Tests for the update_mcp service function (optimistic concurrency)."""

    async def _create_test_mcp(self, mock_db, user="user-1", name="Test MCP"):
        """Helper: create a base MCP for update tests."""
        return await create_mcp(
            mock_db,
            user,
            McpConfigurationCreate(name=name, endpoint_url="https://example.com/mcp"),
        )

    async def test_update_success_no_conflict(self, mock_db):
        """A matching expected_version updates the MCP cleanly."""
        created = await self._create_test_mcp(mock_db)
        data = McpConfigurationUpdate(
            name="Updated MCP",
            endpoint_url="https://example.com/v2",
            expected_version=created.version,
        )
        result, collision = await update_mcp(mock_db, "user-1", created.id, data)

        assert result is not None
        assert collision is None
        assert result.name == "Updated MCP"
        assert result.endpoint_url == "https://example.com/v2"
        assert result.version == created.version + 1

    async def test_update_not_found_returns_none(self, mock_db):
        """Updating a non-existent MCP returns (None, None)."""
        data = McpConfigurationUpdate(
            name="Ghost", endpoint_url="https://example.com/x", expected_version=1
        )
        result, collision = await update_mcp(mock_db, "user-1", "nonexistent-id", data)
        assert result is None
        assert collision is None

    async def test_update_wrong_user_returns_none(self, mock_db):
        """User-2 cannot update user-1's MCP — treated as not found."""
        created = await self._create_test_mcp(mock_db, user="user-1")
        data = McpConfigurationUpdate(
            name="Hijack",
            endpoint_url="https://example.com/evil",
            expected_version=created.version,
        )
        result, collision = await update_mcp(mock_db, "user-2", created.id, data)
        assert result is None
        assert collision is None

    async def test_update_ssrf_rejected(self, mock_db):
        """Updating with a private-IP URL raises McpValidationError."""
        created = await self._create_test_mcp(mock_db)
        data = McpConfigurationUpdate(
            name="Bad URL",
            endpoint_url="http://192.168.1.1/api",
            expected_version=created.version,
        )
        with pytest.raises(McpValidationError, match="private or reserved"):
            await update_mcp(mock_db, "user-1", created.id, data)

    async def test_update_increments_version(self, mock_db):
        """Successive updates increment the version number correctly."""
        created = await self._create_test_mcp(mock_db)
        data_v2 = McpConfigurationUpdate(
            name="V2", endpoint_url="https://example.com/v2", expected_version=1
        )
        result_v2, _ = await update_mcp(mock_db, "user-1", created.id, data_v2)
        assert result_v2 is not None
        assert result_v2.version == 2

        data_v3 = McpConfigurationUpdate(
            name="V3", endpoint_url="https://example.com/v3", expected_version=2
        )
        result_v3, _ = await update_mcp(mock_db, "user-1", created.id, data_v3)
        assert result_v3 is not None
        assert result_v3.version == 3

    async def test_update_with_version_mismatch_triggers_collision(self, mock_db):
        """A stale expected_version triggers collision detection.

        For user-initiated updates (default), the collision resolver applies
        "user_priority" — the incoming user operation (operation_b) wins over
        the synthetic automation-side operation (operation_a). So the update
        should still succeed with a collision event attached.
        """
        created = await self._create_test_mcp(mock_db)
        # Update once to advance version to 2
        data_v2 = McpConfigurationUpdate(
            name="V2", endpoint_url="https://example.com/v2", expected_version=1
        )
        await update_mcp(mock_db, "user-1", created.id, data_v2)

        # Now attempt an update with the stale version 1
        stale_data = McpConfigurationUpdate(
            name="Stale Update",
            endpoint_url="https://example.com/stale",
            expected_version=1,
        )
        result, collision = await update_mcp(mock_db, "user-1", created.id, stale_data)

        # The collision event should be present
        assert collision is not None
        assert collision.target_entity_type == "mcp_config"
        assert collision.target_entity_id == created.id

        # User-initiated wins (operation_b) — update should still succeed
        assert result is not None
        assert result.name == "Stale Update"
        assert result.version == 3

    async def test_update_persists_to_database(self, mock_db):
        """Updated values are persisted and visible via list_mcps."""
        created = await self._create_test_mcp(mock_db)
        data = McpConfigurationUpdate(
            name="Persisted",
            endpoint_url="https://example.com/persisted",
            expected_version=created.version,
        )
        await update_mcp(mock_db, "user-1", created.id, data)

        # Verify via list
        listing = await list_mcps(mock_db, "user-1")
        assert listing.count == 1
        assert listing.mcps[0].name == "Persisted"
        assert listing.mcps[0].endpoint_url == "https://example.com/persisted"
