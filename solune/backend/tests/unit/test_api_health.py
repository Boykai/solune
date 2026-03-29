"""Tests for health check endpoint (src/api/health.py).

Covers:
- GET /api/v1/health -> health_check
- All components pass -> 200, status "pass"
- Database fails -> 503, status "fail"
- GitHub API fails -> 503, status "fail"
- Polling loop stopped -> 200, status "pass" (warn component, not fail)
- Database exception -> 503
- GET /api/v1/ready -> readiness_check
- Readiness DB write check
- Readiness OAuth check
- Readiness encryption check
- Readiness polling check
- _check_startup_config validation
- _check_database, _check_github_api, _check_polling_loop direct tests
- GET /api/v1/rate-limit/history -> rate_limit_history
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

HEALTH_URL = "/api/v1/health"
READY_URL = "/api/v1/ready"
RATE_LIMIT_HISTORY_URL = "/api/v1/rate-limit/history"


class TestHealthAllPass:
    """Tests when all health check components pass."""

    @pytest.fixture(autouse=True)
    def _patch(self):
        with (
            patch("src.api.health._check_database", new_callable=AsyncMock) as mock_db,
            patch("src.api.health._check_github_api", new_callable=AsyncMock) as mock_gh,
            patch("src.api.health._check_polling_loop") as mock_poll,
        ):
            mock_db.return_value = {"status": "pass", "time": "1ms"}
            mock_gh.return_value = {"status": "pass", "time": "50ms"}
            mock_poll.return_value = {"status": "pass", "observed_value": "running"}
            yield

    async def test_all_pass_returns_200(self, client):
        """All components healthy returns 200 with status pass."""
        resp = await client.get(HEALTH_URL)
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "pass"

    async def test_all_pass_has_three_components(self, client):
        """Response includes database, github_api, and polling_loop checks."""
        resp = await client.get(HEALTH_URL)
        checks = resp.json()["checks"]
        assert "database" in checks
        assert "github_api" in checks
        assert "polling_loop" in checks


class TestHealthDatabaseFail:
    """Tests when the database health check fails."""

    @pytest.fixture(autouse=True)
    def _patch(self):
        with (
            patch("src.api.health._check_database", new_callable=AsyncMock) as mock_db,
            patch("src.api.health._check_github_api", new_callable=AsyncMock) as mock_gh,
            patch("src.api.health._check_polling_loop") as mock_poll,
        ):
            mock_db.return_value = {"status": "fail", "output": "database connectivity"}
            mock_gh.return_value = {"status": "pass", "time": "50ms"}
            mock_poll.return_value = {"status": "pass", "observed_value": "running"}
            yield

    async def test_db_fail_returns_503(self, client):
        """Database failure results in 503 with status fail."""
        resp = await client.get(HEALTH_URL)
        assert resp.status_code == 503
        assert resp.json()["status"] == "fail"


class TestHealthGitHubApiFail:
    """Tests when the GitHub API health check fails."""

    @pytest.fixture(autouse=True)
    def _patch(self):
        with (
            patch("src.api.health._check_database", new_callable=AsyncMock) as mock_db,
            patch("src.api.health._check_github_api", new_callable=AsyncMock) as mock_gh,
            patch("src.api.health._check_polling_loop") as mock_poll,
        ):
            mock_db.return_value = {"status": "pass", "time": "1ms"}
            mock_gh.return_value = {"status": "fail", "output": "GitHub API connectivity"}
            mock_poll.return_value = {"status": "pass", "observed_value": "running"}
            yield

    async def test_github_api_fail_returns_503(self, client):
        """GitHub API failure results in 503."""
        resp = await client.get(HEALTH_URL)
        assert resp.status_code == 503
        assert resp.json()["status"] == "fail"


class TestHealthPollingLoopStopped:
    """Tests when the polling loop is stopped (warn, not fail)."""

    @pytest.fixture(autouse=True)
    def _patch(self):
        with (
            patch("src.api.health._check_database", new_callable=AsyncMock) as mock_db,
            patch("src.api.health._check_github_api", new_callable=AsyncMock) as mock_gh,
            patch("src.api.health._check_polling_loop") as mock_poll,
        ):
            mock_db.return_value = {"status": "pass", "time": "1ms"}
            mock_gh.return_value = {"status": "pass", "time": "50ms"}
            mock_poll.return_value = {"status": "warn", "observed_value": "stopped"}
            yield

    async def test_polling_stopped_returns_200(self, client):
        """Polling loop stopped is a warn, not a fail -- still 200."""
        resp = await client.get(HEALTH_URL)
        assert resp.status_code == 200

    async def test_polling_stopped_overall_pass(self, client):
        """Overall status is pass when only polling_loop is warn."""
        resp = await client.get(HEALTH_URL)
        assert resp.json()["status"] == "pass"


class TestHealthDatabaseException:
    """Tests when the database check function returns fail due to exception."""

    @pytest.fixture(autouse=True)
    def _patch(self):
        with (
            patch("src.api.health._check_database", new_callable=AsyncMock) as mock_db,
            patch("src.api.health._check_github_api", new_callable=AsyncMock) as mock_gh,
            patch("src.api.health._check_polling_loop") as mock_poll,
        ):
            mock_db.return_value = {"status": "fail", "output": "database connectivity"}
            mock_gh.return_value = {"status": "pass", "time": "50ms"}
            mock_poll.return_value = {"status": "pass", "observed_value": "running"}
            yield

    async def test_db_exception_returns_503(self, client):
        """Database exception causes 503."""
        resp = await client.get(HEALTH_URL)
        assert resp.status_code == 503
        assert resp.json()["status"] == "fail"


# ── Health check version ─────────────────────────────────────────────────


class TestHealthVersion:
    """Test that version string is included in health response."""

    @pytest.fixture(autouse=True)
    def _patch(self):
        with (
            patch("src.api.health._check_database", new_callable=AsyncMock) as mock_db,
            patch("src.api.health._check_github_api", new_callable=AsyncMock) as mock_gh,
            patch("src.api.health._check_polling_loop") as mock_poll,
        ):
            mock_db.return_value = {"status": "pass", "time": "1ms"}
            mock_gh.return_value = {"status": "pass", "time": "50ms"}
            mock_poll.return_value = {"status": "pass", "observed_value": "running"}
            yield

    async def test_version_in_response(self, client):
        resp = await client.get(HEALTH_URL)
        assert "version" in resp.json()

    async def test_startup_checks_in_response(self, client):
        resp = await client.get(HEALTH_URL)
        assert "startup_checks" in resp.json()["checks"]


# ── Readiness endpoint ───────────────────────────────────────────────────


class TestReadinessAllPass:
    """Tests for GET /api/v1/ready when all checks pass."""

    @pytest.fixture(autouse=True)
    def _patch(self):
        with (
            patch("src.api.health._readiness_check_db", new_callable=AsyncMock) as mock_db,
            patch("src.api.health._readiness_check_oauth") as mock_oauth,
            patch("src.api.health._readiness_check_encryption") as mock_enc,
            patch("src.api.health._readiness_check_polling") as mock_poll,
        ):
            from src.api.health import ReadinessCheckResult

            mock_db.return_value = ReadinessCheckResult(
                component_id="database:writeable", status="pass", time="t"
            )
            mock_oauth.return_value = ReadinessCheckResult(
                component_id="oauth:configured", status="pass", time="t"
            )
            mock_enc.return_value = ReadinessCheckResult(
                component_id="encryption:enabled", status="pass", time="t"
            )
            mock_poll.return_value = ReadinessCheckResult(
                component_id="polling:alive", status="pass", time="t"
            )
            yield

    async def test_ready_all_pass_returns_200(self, client):
        resp = await client.get(READY_URL)
        assert resp.status_code == 200
        assert resp.json()["status"] == "pass"

    async def test_ready_has_four_checks(self, client):
        resp = await client.get(READY_URL)
        checks = resp.json()["checks"]
        assert len(checks) == 4


class TestReadinessDbFail:
    """Tests for readiness when DB write check fails."""

    @pytest.fixture(autouse=True)
    def _patch(self):
        with (
            patch("src.api.health._readiness_check_db", new_callable=AsyncMock) as mock_db,
            patch("src.api.health._readiness_check_oauth") as mock_oauth,
            patch("src.api.health._readiness_check_encryption") as mock_enc,
            patch("src.api.health._readiness_check_polling") as mock_poll,
        ):
            from src.api.health import ReadinessCheckResult

            mock_db.return_value = ReadinessCheckResult(
                component_id="database:writeable",
                status="fail",
                time="t",
                output="Database write check failed",
            )
            mock_oauth.return_value = ReadinessCheckResult(
                component_id="oauth:configured", status="pass", time="t"
            )
            mock_enc.return_value = ReadinessCheckResult(
                component_id="encryption:enabled", status="pass", time="t"
            )
            mock_poll.return_value = ReadinessCheckResult(
                component_id="polling:alive", status="pass", time="t"
            )
            yield

    async def test_ready_returns_503_on_db_fail(self, client):
        resp = await client.get(READY_URL)
        assert resp.status_code == 503
        assert resp.json()["status"] == "fail"


class TestReadinessOauthFail:
    """Tests for readiness when OAuth check fails."""

    @pytest.fixture(autouse=True)
    def _patch(self):
        with (
            patch("src.api.health._readiness_check_db", new_callable=AsyncMock) as mock_db,
            patch("src.api.health._readiness_check_oauth") as mock_oauth,
            patch("src.api.health._readiness_check_encryption") as mock_enc,
            patch("src.api.health._readiness_check_polling") as mock_poll,
        ):
            from src.api.health import ReadinessCheckResult

            mock_db.return_value = ReadinessCheckResult(
                component_id="database:writeable", status="pass", time="t"
            )
            mock_oauth.return_value = ReadinessCheckResult(
                component_id="oauth:configured",
                status="fail",
                time="t",
                output="GitHub OAuth client ID or secret is empty",
            )
            mock_enc.return_value = ReadinessCheckResult(
                component_id="encryption:enabled", status="pass", time="t"
            )
            mock_poll.return_value = ReadinessCheckResult(
                component_id="polling:alive", status="pass", time="t"
            )
            yield

    async def test_ready_returns_503_on_oauth_fail(self, client):
        resp = await client.get(READY_URL)
        assert resp.status_code == 503
        body = resp.json()
        assert body["status"] == "fail"


# ── Direct component check unit tests ────────────────────────────────────


class TestCheckStartupConfig:
    """Tests for _check_startup_config() directly."""

    def test_all_configured(self):
        from src.api.health import _check_startup_config

        mock_settings = MagicMock()
        mock_settings.encryption_key = "some-key"
        mock_settings.github_client_id = "id"
        mock_settings.github_client_secret = "secret"
        mock_settings.session_secret_key = "a" * 64
        mock_settings.github_webhook_secret = "webhook-secret"

        with patch("src.config.get_settings", return_value=mock_settings):
            result = _check_startup_config()
        assert result["status"] == "pass"

    def test_missing_encryption_key(self):
        from src.api.health import _check_startup_config

        mock_settings = MagicMock()
        mock_settings.encryption_key = ""
        mock_settings.github_client_id = "id"
        mock_settings.github_client_secret = "secret"
        mock_settings.session_secret_key = "a" * 64
        mock_settings.github_webhook_secret = "webhook"

        with patch("src.config.get_settings", return_value=mock_settings):
            result = _check_startup_config()
        assert result["status"] == "warn"
        assert any("ENCRYPTION_KEY" in i for i in result["issues"])

    def test_short_session_secret(self):
        from src.api.health import _check_startup_config

        mock_settings = MagicMock()
        mock_settings.encryption_key = "key"
        mock_settings.github_client_id = "id"
        mock_settings.github_client_secret = "secret"
        mock_settings.session_secret_key = "short"
        mock_settings.github_webhook_secret = "webhook"

        with patch("src.config.get_settings", return_value=mock_settings):
            result = _check_startup_config()
        assert result["status"] == "warn"
        assert any("SESSION_SECRET_KEY" in i for i in result["issues"])

    def test_missing_webhook_secret(self):
        from src.api.health import _check_startup_config

        mock_settings = MagicMock()
        mock_settings.encryption_key = "key"
        mock_settings.github_client_id = "id"
        mock_settings.github_client_secret = "secret"
        mock_settings.session_secret_key = "a" * 64
        mock_settings.github_webhook_secret = ""

        with patch("src.config.get_settings", return_value=mock_settings):
            result = _check_startup_config()
        assert result["status"] == "warn"
        assert any("WEBHOOK_SECRET" in i for i in result["issues"])

    def test_exception_returns_warn(self):
        from src.api.health import _check_startup_config

        with patch("src.config.get_settings", side_effect=RuntimeError("boom")):
            result = _check_startup_config()
        assert result["status"] == "warn"


class TestCheckDatabase:
    async def test_success_returns_pass(self, mock_db):
        from src.api.health import _check_database

        with patch("src.api.health.get_db", return_value=mock_db):
            result = await _check_database()
        assert result["status"] == "pass"
        assert "time" in result

    async def test_failure_returns_fail(self):
        from src.api.health import _check_database

        mock_bad_db = AsyncMock()
        mock_bad_db.execute.side_effect = RuntimeError("connection lost")
        with patch("src.api.health.get_db", return_value=mock_bad_db):
            result = await _check_database()
        assert result["status"] == "fail"


class TestCheckPollingLoop:
    def test_running_task(self):
        from src.api.health import _check_polling_loop

        mock_task = MagicMock()
        mock_task.done.return_value = False

        with (
            patch("src.api.health._check_polling_loop.__module__", create=True),
            patch("src.services.copilot_polling._polling_task", mock_task),
            patch("src.services.copilot_polling.state._polling_state") as mock_state,
        ):
            mock_state.is_running = False
            result = _check_polling_loop()
        assert result["status"] == "pass"
        assert result["observed_value"] == "running"

    def test_no_task_and_not_running(self):
        from src.api.health import _check_polling_loop

        with (
            patch("src.services.copilot_polling._polling_task", None),
            patch("src.services.copilot_polling.state._polling_state") as mock_state,
        ):
            mock_state.is_running = False
            result = _check_polling_loop()
        assert result["status"] == "warn"
        assert result["observed_value"] == "stopped"


class TestReadinessCheckOauth:
    def test_configured(self, mock_settings):
        from src.api.health import _readiness_check_oauth

        with patch("src.config.get_settings", return_value=mock_settings):
            result = _readiness_check_oauth()
        assert result.status == "pass"

    def test_missing_client_id(self, mock_settings):
        from src.api.health import _readiness_check_oauth

        mock_settings.github_client_id = ""
        with patch("src.config.get_settings", return_value=mock_settings):
            result = _readiness_check_oauth()
        assert result.status == "fail"

    def test_missing_client_secret(self, mock_settings):
        from src.api.health import _readiness_check_oauth

        mock_settings.github_client_secret = ""
        with patch("src.config.get_settings", return_value=mock_settings):
            result = _readiness_check_oauth()
        assert result.status == "fail"


class TestReadinessCheckDb:
    async def test_write_check_passes(self, mock_db):
        from src.api.health import _readiness_check_db

        with patch("src.api.health.get_db", return_value=mock_db):
            result = await _readiness_check_db()
        assert result.status == "pass"

    async def test_write_check_fails(self):
        from src.api.health import _readiness_check_db

        mock_bad_db = AsyncMock()
        mock_bad_db.execute.side_effect = RuntimeError("db locked")
        with patch("src.api.health.get_db", return_value=mock_bad_db):
            result = await _readiness_check_db()
        assert result.status == "fail"
        assert "write check" in result.output.lower()


# ── Rate-limit history endpoint ──────────────────────────────────────────


class TestRateLimitHistory:
    async def test_returns_snapshots(self, client):
        from src.services.rate_limit_tracker import RateLimitTracker

        with patch.object(
            RateLimitTracker,
            "get_history",
            new_callable=AsyncMock,
            return_value=[{"timestamp": "t", "remaining": 4500, "limit": 5000, "reset_at": 0}],
        ):
            resp = await client.get(RATE_LIMIT_HISTORY_URL)
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["hours"] == 24

    async def test_custom_hours(self, client):
        from src.services.rate_limit_tracker import RateLimitTracker

        with patch.object(
            RateLimitTracker,
            "get_history",
            new_callable=AsyncMock,
            return_value=[],
        ) as mock_hist:
            resp = await client.get(RATE_LIMIT_HISTORY_URL, params={"hours": 6})
        assert resp.status_code == 200
        assert resp.json()["hours"] == 6
        mock_hist.assert_awaited_once_with(hours=6)
