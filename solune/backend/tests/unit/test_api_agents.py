"""Tests for agents API routes (src/api/agents.py).

Covers:
- GET    /api/v1/agents/{project_id}              → list_agents
- GET    /api/v1/agents/{project_id}/pending       → list_pending_agents
- DELETE /api/v1/agents/{project_id}/pending       → purge_pending_agents
- PATCH  /api/v1/agents/{project_id}/bulk-model    → bulk_update_models
- POST   /api/v1/agents/{project_id}              → create_agent
- PATCH  /api/v1/agents/{project_id}/{agent_id}    → update_agent
- DELETE /api/v1/agents/{project_id}/{agent_id}    → delete_agent
- POST   /api/v1/agents/{project_id}/chat          → agent_chat
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.agents import (
    Agent,
    AgentChatResponse,
    AgentCreateResult,
    AgentDeleteResult,
    AgentPendingCleanupResult,
    AgentStatus,
    BulkModelUpdateResult,
    CatalogAgent,
    ImportAgentResult,
    InstallAgentResult,
)

PROJECT_ID = "PVT_test123"
AGENT_ID = "agent-abc"
BASE = f"/api/v1/agents/{PROJECT_ID}"


def _mock_service():
    """Return an AsyncMock that stands in for AgentsService."""
    return AsyncMock(name="AgentsService")


def _sample_agent(**overrides) -> Agent:
    """Build a valid Agent model instance."""
    defaults = {
        "id": AGENT_ID,
        "name": "my-agent",
        "slug": "my-agent",
        "description": "A test agent",
        "system_prompt": "You are a helpful agent.",
        "status": AgentStatus.ACTIVE,
    }
    defaults.update(overrides)
    return Agent(**defaults)


def _sample_create_result(**overrides) -> AgentCreateResult:
    """Build a valid AgentCreateResult model instance."""
    defaults = {
        "agent": _sample_agent(),
        "pr_url": "https://github.com/owner/repo/pull/1",
        "pr_number": 1,
        "branch_name": "agent/my-agent",
    }
    defaults.update(overrides)
    return AgentCreateResult(**defaults)


# ── GET /{project_id} ──────────────────────────────────────────────────────


class TestListAgents:
    """Tests for the list_agents endpoint."""

    @pytest.fixture(autouse=True)
    def _patch(self):
        svc = _mock_service()
        self.svc = svc
        with (
            patch("src.api.agents._get_service", return_value=svc),
            patch(
                "src.api.agents.resolve_repository",
                new_callable=AsyncMock,
                return_value=("owner", "repo"),
            ),
            patch("src.api.agents.get_db", return_value=MagicMock()),
        ):
            yield

    async def test_list_agents_empty(self, client):
        """Returns empty list when no agents exist."""
        self.svc.list_agents.return_value = []
        resp = await client.get(BASE)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_list_agents_returns_items(self, client):
        """Returns agents from the service."""
        self.svc.list_agents.return_value = [_sample_agent()]
        resp = await client.get(BASE)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "my-agent"


# ── GET /{project_id}/pending ──────────────────────────────────────────────


class TestListPendingAgents:
    """Tests for the list_pending_agents endpoint."""

    @pytest.fixture(autouse=True)
    def _patch(self):
        svc = _mock_service()
        self.svc = svc
        with (
            patch("src.api.agents._get_service", return_value=svc),
            patch(
                "src.api.agents.resolve_repository",
                new_callable=AsyncMock,
                return_value=("owner", "repo"),
            ),
            patch("src.api.agents.get_db", return_value=MagicMock()),
        ):
            yield

    async def test_list_pending_empty(self, client):
        """Returns empty list when no pending agents."""
        self.svc.list_pending_agents.return_value = []
        resp = await client.get(f"{BASE}/pending")
        assert resp.status_code == 200
        assert resp.json() == []


# ── DELETE /{project_id}/pending ───────────────────────────────────────────


class TestPurgePendingAgents:
    """Tests for the purge_pending_agents endpoint."""

    @pytest.fixture(autouse=True)
    def _patch(self):
        svc = _mock_service()
        self.svc = svc
        with (
            patch("src.api.agents._get_service", return_value=svc),
            patch(
                "src.api.agents.resolve_repository",
                new_callable=AsyncMock,
                return_value=("owner", "repo"),
            ),
            patch("src.api.agents.get_db", return_value=MagicMock()),
        ):
            yield

    async def test_purge_pending_success(self, client):
        """Purges stale pending agents and returns count."""
        self.svc.purge_pending_agents.return_value = AgentPendingCleanupResult(deleted_count=2)
        resp = await client.delete(f"{BASE}/pending")
        assert resp.status_code == 200
        assert resp.json()["deleted_count"] == 2


# ── PATCH /{project_id}/bulk-model ─────────────────────────────────────────


class TestBulkUpdateModels:
    """Tests for the bulk_update_models endpoint."""

    @pytest.fixture(autouse=True)
    def _patch(self):
        svc = _mock_service()
        self.svc = svc
        with (
            patch("src.api.agents._get_service", return_value=svc),
            patch(
                "src.api.agents.resolve_repository",
                new_callable=AsyncMock,
                return_value=("owner", "repo"),
            ),
            patch("src.api.agents.get_db", return_value=MagicMock()),
        ):
            yield

    async def test_bulk_update_success(self, client):
        """Bulk update returns result from the service."""
        self.svc.bulk_update_models.return_value = BulkModelUpdateResult(
            updated_count=3,
            target_model_id="gpt-4o",
            target_model_name="GPT-4o",
        )
        resp = await client.patch(
            f"{BASE}/bulk-model",
            json={"target_model_id": "gpt-4o", "target_model_name": "GPT-4o"},
        )
        assert resp.status_code == 200
        assert resp.json()["updated_count"] == 3


# ── POST /{project_id} ────────────────────────────────────────────────────


class TestCreateAgent:
    """Tests for the create_agent endpoint."""

    @pytest.fixture(autouse=True)
    def _patch(self):
        svc = _mock_service()
        self.svc = svc
        with (
            patch("src.api.agents._get_service", return_value=svc),
            patch(
                "src.api.agents.resolve_repository",
                new_callable=AsyncMock,
                return_value=("owner", "repo"),
            ),
            patch("src.api.agents.get_db", return_value=MagicMock()),
        ):
            yield

    async def test_create_agent_success(self, client):
        """Creates agent and returns 201."""
        self.svc.create_agent.return_value = _sample_create_result()
        resp = await client.post(
            BASE,
            json={
                "name": "my-agent",
                "description": "A test agent",
                "system_prompt": "You are helpful.",
            },
        )
        assert resp.status_code == 201

    async def test_create_agent_value_error_returns_422(self, client):
        """ValueError from service is mapped to 422."""
        self.svc.create_agent.side_effect = ValueError("duplicate name")
        resp = await client.post(
            BASE,
            json={
                "name": "my-agent",
                "description": "dup",
                "system_prompt": "prompt",
            },
        )
        assert resp.status_code == 422

    async def test_create_agent_runtime_error_returns_502(self, client):
        """RuntimeError from service is mapped to 502 (via GitHubAPIError)."""
        self.svc.create_agent.side_effect = RuntimeError("GitHub API down")
        resp = await client.post(
            BASE,
            json={
                "name": "my-agent",
                "description": "fail",
                "system_prompt": "prompt",
            },
        )
        assert resp.status_code == 502


# ── PATCH /{project_id}/{agent_id} ────────────────────────────────────────


class TestUpdateAgent:
    """Tests for the update_agent endpoint."""

    @pytest.fixture(autouse=True)
    def _patch(self):
        svc = _mock_service()
        self.svc = svc
        with (
            patch("src.api.agents._get_service", return_value=svc),
            patch(
                "src.api.agents.resolve_repository",
                new_callable=AsyncMock,
                return_value=("owner", "repo"),
            ),
            patch("src.api.agents.get_db", return_value=MagicMock()),
        ):
            yield

    async def test_update_agent_success(self, client):
        """Updates agent and returns result."""
        self.svc.update_agent.return_value = _sample_create_result()
        resp = await client.patch(
            f"{BASE}/{AGENT_ID}",
            json={"description": "updated desc"},
        )
        assert resp.status_code == 200

    async def test_update_agent_not_found_returns_404(self, client):
        """LookupError from service is mapped to 404."""
        self.svc.update_agent.side_effect = LookupError("agent not found")
        resp = await client.patch(
            f"{BASE}/{AGENT_ID}",
            json={"description": "missing"},
        )
        assert resp.status_code == 404

    async def test_update_agent_value_error_returns_422(self, client):
        """ValueError from service is mapped to 422."""
        self.svc.update_agent.side_effect = ValueError("invalid field")
        resp = await client.patch(
            f"{BASE}/{AGENT_ID}",
            json={"description": "bad"},
        )
        assert resp.status_code == 422


# ── DELETE /{project_id}/{agent_id} ────────────────────────────────────────


class TestDeleteAgent:
    """Tests for the delete_agent endpoint."""

    @pytest.fixture(autouse=True)
    def _patch(self):
        svc = _mock_service()
        self.svc = svc
        with (
            patch("src.api.agents._get_service", return_value=svc),
            patch(
                "src.api.agents.resolve_repository",
                new_callable=AsyncMock,
                return_value=("owner", "repo"),
            ),
            patch("src.api.agents.get_db", return_value=MagicMock()),
        ):
            yield

    async def test_delete_agent_success(self, client):
        """Deletes agent and returns result."""
        self.svc.delete_agent.return_value = AgentDeleteResult(
            success=True,
            pr_url="https://github.com/owner/repo/pull/3",
            pr_number=3,
        )
        resp = await client.delete(f"{BASE}/{AGENT_ID}")
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    async def test_delete_agent_not_found_returns_404(self, client):
        """LookupError from service is mapped to 404."""
        self.svc.delete_agent.side_effect = LookupError("agent not found")
        resp = await client.delete(f"{BASE}/{AGENT_ID}")
        assert resp.status_code == 404

    async def test_delete_agent_runtime_error_returns_502(self, client):
        """RuntimeError from service is mapped to 502 (via GitHubAPIError)."""
        self.svc.delete_agent.side_effect = RuntimeError("GitHub API failure")
        resp = await client.delete(f"{BASE}/{AGENT_ID}")
        assert resp.status_code == 502


# ── POST /{project_id}/chat ───────────────────────────────────────────────


class TestAgentChat:
    """Tests for the agent_chat endpoint."""

    @pytest.fixture(autouse=True)
    def _patch(self):
        svc = _mock_service()
        self.svc = svc
        with (
            patch("src.api.agents._get_service", return_value=svc),
            patch(
                "src.api.agents.resolve_repository",
                new_callable=AsyncMock,
                return_value=("owner", "repo"),
            ),
            patch("src.api.agents.get_db", return_value=MagicMock()),
        ):
            yield

    async def test_agent_chat_success(self, client):
        """Chat returns response from service."""
        self.svc.chat.return_value = AgentChatResponse(
            reply="Hello!",
            session_id="sess-1",
        )
        resp = await client.post(
            f"{BASE}/chat",
            json={"message": "Help me build an agent"},
        )
        assert resp.status_code == 200
        assert resp.json()["reply"] == "Hello!"

    async def test_agent_chat_generic_error_returns_500(self, client):
        """Generic exceptions from chat are mapped via handle_service_error."""
        self.svc.chat.side_effect = Exception("unexpected failure")
        resp = await client.post(
            f"{BASE}/chat",
            json={"message": "trigger error"},
        )
        assert resp.status_code == 500


# ── _get_service() ────────────────────────────────────────────────────────


class TestGetService:
    """Tests for the _get_service helper function."""

    def test_get_service_returns_agents_service(self):
        """_get_service() returns an AgentsService instance."""
        from src.api.agents import _get_service

        mock_db = MagicMock()
        with patch("src.api.agents.get_db", return_value=mock_db):
            service = _get_service()
        assert service is not None


# ── resolve_repository error paths ────────────────────────────────────────


class TestResolveRepositoryErrors:
    """Tests for resolve_repository error handling across endpoints."""

    @pytest.fixture(autouse=True)
    def _patch(self):
        svc = _mock_service()
        self.svc = svc
        with (
            patch("src.api.agents._get_service", return_value=svc),
            patch("src.api.agents.get_db", return_value=MagicMock()),
        ):
            yield

    async def test_list_agents_resolve_repo_app_exception_propagates(self, client):
        """AppException from resolve_repository is re-raised as-is."""
        from src.exceptions import AppException

        with patch(
            "src.api.agents.resolve_repository",
            new_callable=AsyncMock,
            side_effect=AppException("project error", status_code=400),
        ):
            resp = await client.get(BASE)
        assert resp.status_code == 400

    async def test_list_agents_resolve_repo_generic_error(self, client):
        """Non-AppException from resolve_repository is mapped to ValidationError."""
        with patch(
            "src.api.agents.resolve_repository",
            new_callable=AsyncMock,
            side_effect=RuntimeError("network failure"),
        ):
            resp = await client.get(BASE)
        assert resp.status_code == 422

    async def test_list_agents_with_pagination(self, client):
        """List agents with limit param triggers pagination logic."""
        with patch(
            "src.api.agents.resolve_repository",
            new_callable=AsyncMock,
            return_value=("owner", "repo"),
        ):
            self.svc.list_agents.return_value = [_sample_agent()]
            resp = await client.get(BASE, params={"limit": 10})
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data

    async def test_delete_agent_value_error_returns_422(self, client):
        """ValueError from delete_agent is mapped to 422."""
        with patch(
            "src.api.agents.resolve_repository",
            new_callable=AsyncMock,
            return_value=("owner", "repo"),
        ):
            self.svc.delete_agent.side_effect = ValueError("invalid agent")
            resp = await client.delete(f"{BASE}/{AGENT_ID}")
        assert resp.status_code == 422


# ── GET /{project_id}/catalog ─────────────────────────────────────────────


class TestBrowseCatalog:
    """Tests for the browse_catalog endpoint."""

    @pytest.fixture(autouse=True)
    def _patch(self):
        svc = _mock_service()
        self.svc = svc
        with (
            patch("src.api.agents._get_service", return_value=svc),
            patch(
                "src.api.agents.resolve_repository",
                new_callable=AsyncMock,
                return_value=("owner", "repo"),
            ),
            patch("src.api.agents.get_db", return_value=MagicMock()),
        ):
            yield

    async def test_browse_catalog_success(self, client):
        """Returns catalog agents from the catalog reader."""
        agents = [
            CatalogAgent(
                id="test-agent",
                name="Test Agent",
                description="A test agent",
                source_url="https://example.com/agent.md",
            ),
        ]
        with patch(
            "src.services.agents.catalog.list_catalog_agents",
            new_callable=AsyncMock,
            return_value=agents,
        ):
            resp = await client.get(f"{BASE}/catalog")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["id"] == "test-agent"

    async def test_browse_catalog_error_returns_500(self, client):
        """Exceptions from the catalog reader are handled gracefully."""
        with patch(
            "src.services.agents.catalog.list_catalog_agents",
            new_callable=AsyncMock,
            side_effect=RuntimeError("fetch failed"),
        ):
            resp = await client.get(f"{BASE}/catalog")
        assert resp.status_code == 500


# ── POST /{project_id}/import ─────────────────────────────────────────────


class TestImportAgent:
    """Tests for the import_agent endpoint."""

    @pytest.fixture(autouse=True)
    def _patch(self):
        svc = _mock_service()
        self.svc = svc
        with (
            patch("src.api.agents._get_service", return_value=svc),
            patch(
                "src.api.agents.resolve_repository",
                new_callable=AsyncMock,
                return_value=("owner", "repo"),
            ),
            patch("src.api.agents.get_db", return_value=MagicMock()),
            patch("src.api.agents.log_event", new_callable=AsyncMock),
        ):
            yield

    async def test_import_agent_success(self, client):
        """Imports agent and returns 201."""
        imported_agent = _sample_agent(status=AgentStatus.IMPORTED, agent_type="imported")
        self.svc.import_agent.return_value = ImportAgentResult(
            agent=imported_agent,
            message="Agent 'my-agent' imported successfully.",
        )
        resp = await client.post(
            f"{BASE}/import",
            json={
                "catalog_agent_id": "test-agent",
                "name": "my-agent",
                "description": "A test agent",
                "source_url": "https://example.com/agent.md",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["message"] == "Agent 'my-agent' imported successfully."

    async def test_import_agent_duplicate_returns_409(self, client):
        """ValueError (duplicate) from service is mapped to 409."""
        self.svc.import_agent.side_effect = ValueError("already imported")
        resp = await client.post(
            f"{BASE}/import",
            json={
                "catalog_agent_id": "test-agent",
                "name": "my-agent",
                "description": "dup",
                "source_url": "https://example.com/agent.md",
            },
        )
        assert resp.status_code == 409

    async def test_import_agent_fetch_error_returns_502(self, client):
        """RuntimeError from fetching agent content is mapped to 502."""
        self.svc.import_agent.side_effect = RuntimeError("fetch failed")
        resp = await client.post(
            f"{BASE}/import",
            json={
                "catalog_agent_id": "test-agent",
                "name": "my-agent",
                "description": "fail",
                "source_url": "https://example.com/agent.md",
            },
        )
        assert resp.status_code == 502


# ── POST /{project_id}/{agent_id}/install ─────────────────────────────────


class TestInstallAgent:
    """Tests for the install_agent endpoint."""

    @pytest.fixture(autouse=True)
    def _patch(self):
        svc = _mock_service()
        self.svc = svc
        with (
            patch("src.api.agents._get_service", return_value=svc),
            patch(
                "src.api.agents.resolve_repository",
                new_callable=AsyncMock,
                return_value=("owner", "repo"),
            ),
            patch("src.api.agents.get_db", return_value=MagicMock()),
            patch("src.api.agents.log_event", new_callable=AsyncMock),
        ):
            yield

    async def test_install_agent_success(self, client):
        """Installs agent and returns install result."""
        installed_agent = _sample_agent(status=AgentStatus.INSTALLED, agent_type="imported")
        self.svc.install_agent.return_value = InstallAgentResult(
            agent=installed_agent,
            pr_url="https://github.com/owner/repo/pull/10",
            pr_number=10,
            issue_number=5,
            branch_name="agent/my-agent",
        )
        resp = await client.post(f"{BASE}/{AGENT_ID}/install")
        assert resp.status_code == 200
        data = resp.json()
        assert data["pr_number"] == 10
        assert data["issue_number"] == 5

    async def test_install_agent_not_found_returns_404(self, client):
        """LookupError from service is mapped to 404."""
        self.svc.install_agent.side_effect = LookupError("agent not found")
        resp = await client.post(f"{BASE}/{AGENT_ID}/install")
        assert resp.status_code == 404

    async def test_install_agent_wrong_state_returns_422(self, client):
        """ValueError (wrong lifecycle state) is mapped to 422."""
        self.svc.install_agent.side_effect = ValueError("not in imported state")
        resp = await client.post(f"{BASE}/{AGENT_ID}/install")
        assert resp.status_code == 422

    async def test_install_agent_github_error_returns_502(self, client):
        """RuntimeError from GitHub API is mapped to 502."""
        self.svc.install_agent.side_effect = RuntimeError("GitHub API failure")
        resp = await client.post(f"{BASE}/{AGENT_ID}/install")
        assert resp.status_code == 502
