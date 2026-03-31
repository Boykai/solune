"""Auth lifecycle E2E tests (User Story 1).

Verifies: dev-login → cookie set → session persistence → logout → invalidation.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from src.constants import SESSION_COOKIE_NAME
from tests.conftest import TEST_GITHUB_USER_ID, TEST_GITHUB_USERNAME


class TestAuthLifecycle:
    """Authenticated session lifecycle through the real FastAPI app."""

    @pytest.mark.asyncio
    async def test_dev_login_sets_session_cookie_and_returns_user(self, auth_client):
        """auth_client fixture successfully logged in; /auth/me returns the test user."""
        response = await auth_client.get("/api/v1/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert data["github_username"] == TEST_GITHUB_USERNAME
        assert data["github_user_id"] == TEST_GITHUB_USER_ID

    @pytest.mark.asyncio
    async def test_session_persists_across_multiple_requests(self, auth_client):
        """Multiple sequential authenticated requests all return 200 with the same user."""
        for _ in range(3):
            response = await auth_client.get("/api/v1/auth/me")
            assert response.status_code == 200
            data = response.json()
            assert data["github_username"] == TEST_GITHUB_USERNAME
            assert data["github_user_id"] == TEST_GITHUB_USER_ID

    @pytest.mark.asyncio
    async def test_logout_invalidates_session(self, auth_client):
        """POST /logout clears the session; subsequent /auth/me returns 401."""
        # Confirm logged in
        me = await auth_client.get("/api/v1/auth/me")
        assert me.status_code == 200

        # Logout
        logout = await auth_client.post("/api/v1/auth/logout")
        assert logout.status_code == 200

        # Session should now be invalid
        me_after = await auth_client.get("/api/v1/auth/me")
        assert me_after.status_code == 401

    @pytest.mark.asyncio
    async def test_unauthenticated_request_returns_401(self, unauthenticated_client):
        """/auth/me without a session cookie returns 401."""
        response = await unauthenticated_client.get("/api/v1/auth/me")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_cookie_returns_401(self, unauthenticated_client):
        """A made-up session cookie is rejected with 401."""
        unauthenticated_client.cookies.set(SESSION_COOKIE_NAME, "bogus-invalid-session-id")
        response = await unauthenticated_client.get("/api/v1/auth/me")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_expired_session_returns_401(self, auth_client, test_db):
        """A session whose updated_at is older than session_expire_hours returns 401."""
        # Confirm logged in first
        me = await auth_client.get("/api/v1/auth/me")
        assert me.status_code == 200

        # Force the session to be expired by backdating updated_at
        expired_time = (datetime.now(UTC) - timedelta(hours=24)).isoformat()
        await test_db.execute("UPDATE user_sessions SET updated_at = ?", (expired_time,))
        await test_db.commit()

        # Now the session should be treated as expired → 401
        me_after = await auth_client.get("/api/v1/auth/me")
        assert me_after.status_code == 401
