import json
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from src.models.agents import Agent, AgentSource, AgentStatus
from src.services.agents.service import (
    _MAX_CHAT_SESSIONS,
    _SESSION_TTL_SECONDS,
    AgentsService,
    _chat_session_timestamps,
    _chat_sessions,
    _prune_expired_sessions,
)
from src.services.cache import cache, get_repo_agents_cache_key

PROJECT_ID = "project-123"
OWNER = "octo"
REPO = "widgets"
ACCESS_TOKEN = "token"
GITHUB_USER_ID = "user-123"

AGENT_FILE_CONTENT = """---
name: Reviewer
description: Reviews pull requests
tools:
  - read
  - comment
---
Review pull requests carefully.
"""


async def _insert_mcp_tool(
    db,
    *,
    tool_id: str,
    project_id: str = PROJECT_ID,
    github_user_id: str = GITHUB_USER_ID,
    name: str = "Context7",
    config_content: str = '{"mcpServers":{"context7":{"type":"http","url":"https://example.com/mcp","tools":["*"]}}}',
) -> None:
    await db.execute(
        """INSERT INTO mcp_configurations
           (id, github_user_id, project_id, name, description, endpoint_url, config_content,
            sync_status, sync_error, synced_at, github_repo_target, is_active, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, 'synced', '', NULL, ?, 1, datetime('now'), datetime('now'))""",
        (
            tool_id,
            github_user_id,
            project_id,
            name,
            "Shared MCP server",
            "https://example.com/mcp",
            config_content,
            f"{OWNER}/{REPO}",
        ),
    )
    await db.commit()


async def _insert_agent_row(
    db,
    *,
    agent_id: str,
    name: str = "Reviewer",
    slug: str,
    lifecycle_status: str = "pending_pr",
    github_issue_number: int | None = None,
    github_pr_number: int | None = None,
    branch_name: str | None = None,
) -> None:
    await db.execute(
        """INSERT INTO agent_configs
           (id, name, slug, description, system_prompt, status_column,
            tools, project_id, owner, repo, created_by,
            github_issue_number, github_pr_number, branch_name, created_at, lifecycle_status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), ?)""",
        (
            agent_id,
            name,
            slug,
            "Reviews pull requests",
            "Review pull requests carefully.",
            "",
            '["read","comment"]',
            PROJECT_ID,
            OWNER,
            REPO,
            GITHUB_USER_ID,
            github_issue_number,
            github_pr_number,
            branch_name,
            lifecycle_status,
        ),
    )
    await db.commit()


def _workflow_result(pr_number: int = 91, issue_number: int = 44) -> SimpleNamespace:
    return SimpleNamespace(
        success=True,
        pr_url=f"https://github.com/{OWNER}/{REPO}/pull/{pr_number}",
        pr_number=pr_number,
        issue_number=issue_number,
        errors=[],
    )


def _repo_entry(slug: str) -> dict[str, str]:
    return {
        "name": f"{slug}.agent.md",
        "content": AGENT_FILE_CONTENT,
    }


class TestAgentsServiceDeletion:
    @pytest.fixture(autouse=True)
    def clear_cache(self):
        cache.clear()
        yield
        cache.clear()

    async def test_delete_marks_shared_agent_pending_deletion(self, mock_db):
        await _insert_agent_row(mock_db, agent_id="agent-1", slug="reviewer")
        service = AgentsService(mock_db)
        mock_github_service = AsyncMock()
        mock_github_service.get_directory_contents.return_value = [_repo_entry("reviewer")]

        with (
            patch("src.services.agents.service.github_projects_service", mock_github_service),
            patch(
                "src.services.agents.service.commit_files_workflow",
                AsyncMock(return_value=_workflow_result(pr_number=77, issue_number=55)),
            ),
        ):
            result = await service.delete_agent(
                project_id=PROJECT_ID,
                owner=OWNER,
                repo=REPO,
                agent_id="agent-1",
                access_token=ACCESS_TOKEN,
                github_user_id=GITHUB_USER_ID,
            )
            agents = await service.list_agents(
                project_id=PROJECT_ID,
                owner=OWNER,
                repo=REPO,
                access_token=ACCESS_TOKEN,
            )

        assert result.success is True
        assert result.pr_number == 77
        assert len(agents) == 1
        assert agents[0].id == "repo:reviewer"
        assert agents[0].source == AgentSource.REPO
        assert agents[0].status == AgentStatus.ACTIVE
        assert agents[0].github_pr_number is None

        cursor = await mock_db.execute(
            "SELECT lifecycle_status, github_pr_number, github_issue_number, branch_name "
            "FROM agent_configs WHERE id = ?",
            ("agent-1",),
        )
        row = await cursor.fetchone()
        assert row["lifecycle_status"] == AgentStatus.PENDING_DELETION.value
        assert row["github_pr_number"] == 77
        assert row["github_issue_number"] == 55
        assert row["branch_name"] == "agent/delete-reviewer"

    async def test_delete_allows_repo_only_agent_and_creates_tombstone(self, mock_db):
        service = AgentsService(mock_db)
        mock_github_service = AsyncMock()
        mock_github_service.get_directory_contents.return_value = [_repo_entry("reviewer")]

        with (
            patch("src.services.agents.service.github_projects_service", mock_github_service),
            patch(
                "src.services.agents.service.commit_files_workflow",
                AsyncMock(return_value=_workflow_result(pr_number=82, issue_number=63)),
            ),
        ):
            result = await service.delete_agent(
                project_id=PROJECT_ID,
                owner=OWNER,
                repo=REPO,
                agent_id="repo:reviewer",
                access_token=ACCESS_TOKEN,
                github_user_id=GITHUB_USER_ID,
            )
            agents = await service.list_agents(
                project_id=PROJECT_ID,
                owner=OWNER,
                repo=REPO,
                access_token=ACCESS_TOKEN,
            )

        assert result.success is True
        assert len(agents) == 1
        assert agents[0].source == AgentSource.REPO
        assert agents[0].status == AgentStatus.ACTIVE
        assert agents[0].id == "repo:reviewer"
        assert agents[0].github_pr_number is None

        cursor = await mock_db.execute(
            "SELECT id, lifecycle_status, github_pr_number FROM agent_configs WHERE slug = ?",
            ("reviewer",),
        )
        row = await cursor.fetchone()
        assert row is not None
        assert row["id"] != "repo:reviewer"
        assert row["lifecycle_status"] == AgentStatus.PENDING_DELETION.value
        assert row["github_pr_number"] == 82

    async def test_list_agents_removes_pending_deletion_tombstone_after_repo_file_is_gone(
        self,
        mock_db,
    ):
        await _insert_agent_row(
            mock_db,
            agent_id="agent-1",
            slug="reviewer",
            lifecycle_status=AgentStatus.PENDING_DELETION.value,
        )
        service = AgentsService(mock_db)
        mock_github_service = AsyncMock()
        mock_github_service.get_directory_contents.return_value = []

        with patch("src.services.agents.service.github_projects_service", mock_github_service):
            agents = await service.list_agents(
                project_id=PROJECT_ID,
                owner=OWNER,
                repo=REPO,
                access_token=ACCESS_TOKEN,
            )

        assert agents == []

        cursor = await mock_db.execute(
            "SELECT COUNT(*) AS count FROM agent_configs WHERE id = ?", ("agent-1",)
        )
        row = await cursor.fetchone()
        assert row["count"] == 0

    async def test_list_agents_uses_cached_repo_results(self, mock_db):
        service = AgentsService(mock_db)
        mock_github_service = AsyncMock()
        mock_github_service.get_directory_contents.return_value = [_repo_entry("reviewer")]

        with patch("src.services.agents.service.github_projects_service", mock_github_service):
            first = await service.list_agents(
                project_id=PROJECT_ID,
                owner=OWNER,
                repo=REPO,
                access_token=ACCESS_TOKEN,
            )
            second = await service.list_agents(
                project_id=PROJECT_ID,
                owner=OWNER,
                repo=REPO,
                access_token=ACCESS_TOKEN,
            )

        assert len(first) == 1
        assert len(second) == 1
        mock_github_service.get_directory_contents.assert_awaited_once()

    async def test_list_pending_agents_exposes_unmerged_creation_prs(self, mock_db):
        await _insert_agent_row(
            mock_db,
            agent_id="agent-1",
            slug="reviewer",
            lifecycle_status=AgentStatus.PENDING_PR.value,
            github_pr_number=55,
        )
        service = AgentsService(mock_db)
        mock_github_service = AsyncMock()
        mock_github_service.get_directory_contents.return_value = []

        with patch("src.services.agents.service.github_projects_service", mock_github_service):
            pending = await service.list_pending_agents(
                project_id=PROJECT_ID,
                owner=OWNER,
                repo=REPO,
                access_token=ACCESS_TOKEN,
            )

        assert len(pending) == 1
        assert pending[0].id == "agent-1"
        assert pending[0].status == AgentStatus.PENDING_PR
        assert pending[0].source == AgentSource.LOCAL

    async def test_list_pending_agents_cleans_up_after_merge_to_main(self, mock_db):
        await _insert_agent_row(
            mock_db,
            agent_id="agent-1",
            slug="reviewer",
            lifecycle_status=AgentStatus.PENDING_PR.value,
            github_pr_number=55,
        )
        service = AgentsService(mock_db)
        mock_github_service = AsyncMock()
        mock_github_service.get_directory_contents.return_value = [_repo_entry("reviewer")]

        with patch("src.services.agents.service.github_projects_service", mock_github_service):
            pending = await service.list_pending_agents(
                project_id=PROJECT_ID,
                owner=OWNER,
                repo=REPO,
                access_token=ACCESS_TOKEN,
            )

        assert pending == []
        cursor = await mock_db.execute(
            "SELECT COUNT(*) AS count FROM agent_configs WHERE id = ?",
            ("agent-1",),
        )
        row = await cursor.fetchone()
        assert row["count"] == 0

    async def test_purge_pending_agents_deletes_only_non_active_rows(self, mock_db):
        await _insert_agent_row(
            mock_db,
            agent_id="pending-create",
            name="Reviewer Create",
            slug="reviewer",
            lifecycle_status=AgentStatus.PENDING_PR.value,
        )
        await _insert_agent_row(
            mock_db,
            agent_id="pending-delete",
            name="Reviewer Delete",
            slug="reviewer-delete",
            lifecycle_status=AgentStatus.PENDING_DELETION.value,
        )
        await _insert_agent_row(
            mock_db,
            agent_id="active-local",
            name="Reviewer Active",
            slug="reviewer-active",
            lifecycle_status=AgentStatus.ACTIVE.value,
        )

        service = AgentsService(mock_db)

        result = await service.purge_pending_agents(project_id=PROJECT_ID)

        assert result.success is True
        assert result.deleted_count == 2

        cursor = await mock_db.execute("SELECT id, lifecycle_status FROM agent_configs ORDER BY id")
        rows = await cursor.fetchall()
        assert len(rows) == 1
        assert rows[0]["id"] == "active-local"
        assert rows[0]["lifecycle_status"] == AgentStatus.ACTIVE.value


class TestAgentsServiceBulkModelUpdate:
    @pytest.fixture(autouse=True)
    def clear_cache(self):
        cache.clear()
        yield
        cache.clear()

    async def test_bulk_update_models_includes_pending_pr_agents_and_skips_pending_deletions(
        self,
        mock_db,
    ):
        service = AgentsService(mock_db)
        active_agent = SimpleNamespace(
            id="repo:reviewer",
            slug="reviewer",
            icon_name=None,
            default_model_id="old-model",
            default_model_name="Old Model",
            status=AgentStatus.ACTIVE,
        )
        pending_agent = SimpleNamespace(
            id="pending-1",
            slug="writer",
            icon_name=None,
            default_model_id="old-model",
            default_model_name="Old Model",
            status=AgentStatus.PENDING_PR,
        )
        deleting_agent = SimpleNamespace(
            id="pending-2",
            slug="legacy",
            icon_name=None,
            default_model_id="old-model",
            default_model_name="Old Model",
            status=AgentStatus.PENDING_DELETION,
        )
        body = SimpleNamespace(target_model_id="model-1", target_model_name="GPT-5")

        with (
            patch.object(service, "list_agents", AsyncMock(return_value=[active_agent])),
            patch.object(
                service,
                "list_pending_agents",
                AsyncMock(return_value=[pending_agent, deleting_agent]),
            ),
            patch.object(service, "_save_runtime_preferences", AsyncMock()) as save_preferences,
        ):
            result = await service.bulk_update_models(
                project_id=PROJECT_ID,
                owner=OWNER,
                repo=REPO,
                github_user_id=GITHUB_USER_ID,
                body=body,
                access_token=ACCESS_TOKEN,
            )

        assert result.success is True
        assert result.updated_count == 2
        assert result.failed_count == 0
        assert result.updated_agents == ["reviewer", "writer"]
        assert result.failed_agents == []
        assert save_preferences.await_count == 2
        awaited_agents = [call.kwargs["agent"].slug for call in save_preferences.await_args_list]
        assert awaited_agents == ["reviewer", "writer"]


class TestAgentsServiceUpdate:
    @pytest.fixture(autouse=True)
    def clear_cache(self):
        cache.clear()
        yield
        cache.clear()

    async def test_update_agent_allows_repo_only_agent_and_persists_pending_row(self, mock_db):
        service = AgentsService(mock_db)
        mock_github_service = AsyncMock()
        mock_github_service.get_directory_contents.return_value = [_repo_entry("reviewer")]

        with (
            patch("src.services.agents.service.github_projects_service", mock_github_service),
            patch(
                "src.services.agents.service.commit_files_workflow",
                AsyncMock(return_value=_workflow_result(pr_number=88, issue_number=66)),
            ),
        ):
            result = await service.update_agent(
                project_id=PROJECT_ID,
                owner=OWNER,
                repo=REPO,
                agent_id="repo:reviewer",
                body=SimpleNamespace(
                    name="Reviewer",
                    description=None,
                    icon_name=None,
                    system_prompt="Review pull requests carefully.",
                    tools=["read", "comment", "write"],
                    default_model_id=None,
                    default_model_name=None,
                ),
                access_token=ACCESS_TOKEN,
                github_user_id=GITHUB_USER_ID,
            )

        assert result.pr_number == 88
        assert result.agent.status == AgentStatus.PENDING_PR
        assert result.agent.source == AgentSource.LOCAL
        assert result.agent.tools == ["read", "comment", "write"]

        cursor = await mock_db.execute(
            "SELECT slug, tools, lifecycle_status, github_pr_number FROM agent_configs WHERE slug = ?",
            ("reviewer",),
        )
        row = await cursor.fetchone()
        assert row is not None
        assert row["slug"] == "reviewer"
        assert row["tools"] == '["read", "comment", "write"]'
        assert row["lifecycle_status"] == AgentStatus.PENDING_PR.value
        assert row["github_pr_number"] == 88

    async def test_update_agent_embeds_selected_mcp_servers_into_agent_frontmatter(self, mock_db):
        await _insert_mcp_tool(mock_db, tool_id="tool-123")

        service = AgentsService(mock_db)
        mock_github_service = AsyncMock()
        mock_github_service.get_directory_contents.return_value = [_repo_entry("reviewer")]
        workflow = AsyncMock(return_value=_workflow_result(pr_number=89, issue_number=67))

        with (
            patch("src.services.agents.service.github_projects_service", mock_github_service),
            patch("src.services.agents.service.commit_files_workflow", workflow),
        ):
            result = await service.update_agent(
                project_id=PROJECT_ID,
                owner=OWNER,
                repo=REPO,
                agent_id="repo:reviewer",
                body=SimpleNamespace(
                    name="Reviewer",
                    description=None,
                    icon_name=None,
                    system_prompt="Review pull requests carefully.",
                    tools=["tool-123"],
                    default_model_id=None,
                    default_model_name=None,
                ),
                access_token=ACCESS_TOKEN,
                github_user_id=GITHUB_USER_ID,
            )

        assert result.pr_number == 89
        assert result.agent.tools == ["tool-123"]

        files = workflow.await_args.kwargs["files"]
        agent_file = next(file for file in files if file["path"].endswith(".agent.md"))
        content = agent_file["content"]

        assert "mcp-servers:" in content
        assert "context7:" in content
        assert "url: https://example.com/mcp" in content
        assert "solune-tool-ids: tool-123" in content
        assert "tool-123" not in content.split("mcp-servers:", 1)[0]


# ---------------------------------------------------------------------------
# New coverage tests
# ---------------------------------------------------------------------------


def _make_repo_agent(slug: str = "reviewer", **overrides) -> Agent:
    defaults = {
        "id": f"repo:{slug}",
        "name": slug.replace("-", " ").title(),
        "slug": slug,
        "description": "A test agent",
        "system_prompt": "Do things.",
        "default_model_id": "",
        "default_model_name": "",
        "status": AgentStatus.ACTIVE,
        "tools": ["read"],
        "status_column": None,
        "github_issue_number": None,
        "github_pr_number": None,
        "branch_name": None,
        "source": AgentSource.REPO,
        "created_at": None,
    }
    defaults.update(overrides)
    return Agent(**defaults)


async def _insert_agent_row_with_prefs(
    db,
    *,
    agent_id: str,
    slug: str,
    default_model_id: str = "",
    default_model_name: str = "",
    icon_name: str | None = None,
    lifecycle_status: str = "active",
) -> None:
    """Insert an agent_configs row that includes model/icon preferences."""
    await db.execute(
        """INSERT INTO agent_configs
           (id, name, slug, description, system_prompt, status_column,
            tools, project_id, owner, repo, created_by,
            default_model_id, default_model_name, icon_name,
            created_at, lifecycle_status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), ?)""",
        (
            agent_id,
            slug.title(),
            slug,
            "desc",
            "prompt",
            "",
            "[]",
            PROJECT_ID,
            OWNER,
            REPO,
            GITHUB_USER_ID,
            default_model_id,
            default_model_name,
            icon_name,
            lifecycle_status,
        ),
    )
    await db.commit()


# ── T035 / T036: list_agents preference overlay + stale fallback ─────────


class TestListAgentsPreferenceOverlay:
    @pytest.fixture(autouse=True)
    def clear_cache(self):
        cache.clear()
        yield
        cache.clear()

    async def test_list_agents_overlays_local_preferences_on_cached_repo_agents(self, mock_db):
        # Insert a local agent row with saved model prefs
        await _insert_agent_row_with_prefs(
            mock_db,
            agent_id="local-rev",
            slug="reviewer",
            default_model_id="model-x",
            default_model_name="Model X",
            icon_name="star",
        )

        # Seed the cache with a repo agent (no model prefs)
        cache_key = get_repo_agents_cache_key(OWNER, REPO)
        repo_agent = _make_repo_agent("reviewer")
        cache.set(cache_key, [repo_agent])

        service = AgentsService(mock_db)
        agents = await service.list_agents(
            project_id=PROJECT_ID,
            owner=OWNER,
            repo=REPO,
            access_token=ACCESS_TOKEN,
        )

        assert len(agents) == 1
        assert agents[0].default_model_id == "model-x"
        assert agents[0].default_model_name == "Model X"
        assert agents[0].icon_name == "star"

    async def test_list_agents_stale_fallback_when_repo_unavailable(self, mock_db):
        # Seed cache, then expire it so only get_stale returns data
        cache_key = get_repo_agents_cache_key(OWNER, REPO)
        repo_agent = _make_repo_agent("reviewer")
        cache.set(cache_key, [repo_agent], ttl_seconds=0)

        mock_github_service = AsyncMock()
        mock_github_service.get_directory_contents.side_effect = RuntimeError("offline")

        service = AgentsService(mock_db)
        with patch("src.services.agents.service.github_projects_service", mock_github_service):
            agents = await service.list_agents(
                project_id=PROJECT_ID,
                owner=OWNER,
                repo=REPO,
                access_token=ACCESS_TOKEN,
            )

        # Stale data should still be returned
        assert len(agents) == 1
        assert agents[0].slug == "reviewer"

    async def test_list_agents_empty_when_no_cache_and_repo_fails(self, mock_db):
        mock_github_service = AsyncMock()
        mock_github_service.get_directory_contents.side_effect = RuntimeError("offline")

        service = AgentsService(mock_db)
        with patch("src.services.agents.service.github_projects_service", mock_github_service):
            agents = await service.list_agents(
                project_id=PROJECT_ID,
                owner=OWNER,
                repo=REPO,
                access_token=ACCESS_TOKEN,
            )

        assert agents == []


# ── T041-T043: YAML frontmatter parsing ─────────────────────────────────


class TestYAMLFrontmatterParsing:
    @pytest.fixture(autouse=True)
    def clear_cache(self):
        cache.clear()
        yield
        cache.clear()

    async def test_missing_yaml_fields_uses_defaults(self, mock_db):
        # Frontmatter with only an unrelated key — name/description/tools all absent
        content_minimal = "---\ncustom_key: value\n---\nJust a prompt."
        mock_github_service = AsyncMock()
        mock_github_service.get_directory_contents.return_value = [
            {"name": "helper.agent.md", "content": content_minimal}
        ]

        service = AgentsService(mock_db)
        with patch("src.services.agents.service.github_projects_service", mock_github_service):
            agents, available = await service._list_repo_agents(
                owner=OWNER, repo=REPO, access_token=ACCESS_TOKEN
            )

        assert available is True
        assert len(agents) == 1
        agent = agents[0]
        assert agent.slug == "helper"
        assert agent.description == ""
        assert agent.tools == []
        assert agent.system_prompt == "Just a prompt."
        # Name falls back to titlecased slug
        assert agent.name == "Helper"

    async def test_yaml_parse_error_falls_back_to_basic_agent(self, mock_db):
        bad_yaml = "---\n: invalid: yaml: [[[broken\n---\nSome prompt."
        mock_github_service = AsyncMock()
        mock_github_service.get_directory_contents.return_value = [
            {"name": "bad.agent.md", "content": bad_yaml}
        ]

        service = AgentsService(mock_db)
        with patch("src.services.agents.service.github_projects_service", mock_github_service):
            agents, available = await service._list_repo_agents(
                owner=OWNER, repo=REPO, access_token=ACCESS_TOKEN
            )

        assert available is True
        assert len(agents) == 1
        assert agents[0].slug == "bad"
        assert agents[0].system_prompt == "Some prompt."

    async def test_no_frontmatter_uses_content_as_system_prompt(self, mock_db):
        raw_content = "This is just a raw system prompt with no YAML."
        mock_github_service = AsyncMock()
        mock_github_service.get_directory_contents.return_value = [
            {"name": "simple.agent.md", "content": raw_content}
        ]

        service = AgentsService(mock_db)
        with patch("src.services.agents.service.github_projects_service", mock_github_service):
            agents, available = await service._list_repo_agents(
                owner=OWNER, repo=REPO, access_token=ACCESS_TOKEN
            )

        assert available is True
        assert len(agents) == 1
        assert agents[0].system_prompt == raw_content
        assert agents[0].description == ""
        assert agents[0].tools == []

    async def test_full_frontmatter_parsed_correctly(self, mock_db):
        mock_github_service = AsyncMock()
        mock_github_service.get_directory_contents.return_value = [
            {"name": "reviewer.agent.md", "content": AGENT_FILE_CONTENT}
        ]

        service = AgentsService(mock_db)
        with patch("src.services.agents.service.github_projects_service", mock_github_service):
            agents, available = await service._list_repo_agents(
                owner=OWNER, repo=REPO, access_token=ACCESS_TOKEN
            )

        assert available is True
        assert len(agents) == 1
        agent = agents[0]
        assert agent.name == "Reviewer"
        assert agent.description == "Reviews pull requests"
        assert agent.tools == ["read", "comment"]
        assert agent.system_prompt == "Review pull requests carefully."


# ── T044-T046: _normalize_mcp_server_config ──────────────────────────────


class TestNormalizeMCPServerConfig:
    def test_stdio_type_becomes_local(self):
        result = AgentsService._normalize_mcp_server_config({"type": "stdio", "command": "npx foo"})
        assert result is not None
        assert result["type"] == "local"

    def test_dict_with_command_infers_local_type(self):
        result = AgentsService._normalize_mcp_server_config({"command": "node server.js"})
        assert result is not None
        assert result["type"] == "local"

    def test_dict_with_url_infers_http_type(self):
        result = AgentsService._normalize_mcp_server_config({"url": "https://example.com/mcp"})
        assert result is not None
        assert result["type"] == "http"

    def test_explicit_type_preserved(self):
        result = AgentsService._normalize_mcp_server_config(
            {"type": "http", "url": "https://example.com/mcp", "tools": ["search"]}
        )
        assert result is not None
        assert result["type"] == "http"
        assert result["tools"] == ["search"]

    def test_empty_tools_defaults_to_wildcard(self):
        result = AgentsService._normalize_mcp_server_config(
            {"type": "http", "url": "https://example.com/mcp"}
        )
        assert result is not None
        assert result["tools"] == ["*"]

    def test_non_dict_returns_none(self):
        assert AgentsService._normalize_mcp_server_config("just a string") is None
        assert AgentsService._normalize_mcp_server_config(42) is None
        assert AgentsService._normalize_mcp_server_config(None) is None

    def test_empty_tools_list_defaults_to_wildcard(self):
        result = AgentsService._normalize_mcp_server_config(
            {"type": "http", "url": "https://x.com", "tools": []}
        )
        assert result is not None
        assert result["tools"] == ["*"]


# ── Tool resolution ──────────────────────────────────────────────────────


class TestToolResolution:
    @pytest.fixture(autouse=True)
    def clear_cache(self):
        cache.clear()
        yield
        cache.clear()

    async def test_empty_tools_returns_empty(self, mock_db):
        service = AgentsService(mock_db)
        display, allowlist, ids, mcp = await service._resolve_agent_tool_selection(
            project_id=PROJECT_ID,
            github_user_id=GITHUB_USER_ID,
            requested_tools=[],
        )
        assert display == []
        assert allowlist == []
        assert ids == []
        assert mcp == {}

    async def test_mcp_tool_lookup_from_db(self, mock_db):
        await _insert_mcp_tool(mock_db, tool_id="tool-abc")
        service = AgentsService(mock_db)

        display, _allowlist, ids, mcp = await service._resolve_agent_tool_selection(
            project_id=PROJECT_ID,
            github_user_id=GITHUB_USER_ID,
            requested_tools=["tool-abc"],
        )

        assert "Context7" in display
        assert "tool-abc" in ids
        assert "context7" in mcp

    async def test_unknown_tool_treated_as_explicit(self, mock_db):
        service = AgentsService(mock_db)
        display, allowlist, ids, mcp = await service._resolve_agent_tool_selection(
            project_id=PROJECT_ID,
            github_user_id=GITHUB_USER_ID,
            requested_tools=["read"],
        )

        assert display == ["read"]
        assert "read" in allowlist
        assert ids == []
        assert mcp == {}

    async def test_duplicate_tools_deduped(self, mock_db):
        service = AgentsService(mock_db)
        display, allowlist, _ids, _mcp = await service._resolve_agent_tool_selection(
            project_id=PROJECT_ID,
            github_user_id=GITHUB_USER_ID,
            requested_tools=["read", "read"],
        )

        assert display == ["read"]
        assert allowlist == ["read"]


# ── T047-T049: create_agent ──────────────────────────────────────────────


class TestCreateAgent:
    @pytest.fixture(autouse=True)
    def clear_cache(self):
        cache.clear()
        yield
        cache.clear()

    async def test_slug_from_special_chars(self, mock_db):
        service = AgentsService(mock_db)
        mock_github_service = AsyncMock()
        mock_github_service.get_file_content.side_effect = FileNotFoundError()

        body = SimpleNamespace(
            name="My Cool Agent!",
            description="test",
            icon_name=None,
            system_prompt="Do stuff.",
            tools=[],
            status_column="",
            default_model_id="",
            default_model_name="",
            raw=True,
        )

        with (
            patch("src.services.agents.service.github_projects_service", mock_github_service),
            patch(
                "src.services.agents.service.commit_files_workflow",
                AsyncMock(return_value=_workflow_result(pr_number=100, issue_number=70)),
            ),
        ):
            result = await service.create_agent(
                project_id=PROJECT_ID,
                owner=OWNER,
                repo=REPO,
                body=body,
                access_token=ACCESS_TOKEN,
                github_user_id=GITHUB_USER_ID,
            )

        assert result.agent.slug == "my-cool-agent"
        assert result.pr_number == 100

    async def test_ai_failure_fallback_to_raw_input(self, mock_db):
        service = AgentsService(mock_db)
        mock_github_service = AsyncMock()
        mock_github_service.get_file_content.side_effect = FileNotFoundError()

        body = SimpleNamespace(
            name="Fallback Agent",
            description="",
            icon_name=None,
            system_prompt="Help users.",
            tools=[],
            status_column="",
            default_model_id="",
            default_model_name="",
            raw=False,
        )

        with (
            patch("src.services.agents.service.github_projects_service", mock_github_service),
            patch.object(
                service, "_enhance_agent_content", AsyncMock(side_effect=RuntimeError("AI down"))
            ),
            patch.object(
                service,
                "_generate_rich_descriptions",
                AsyncMock(side_effect=RuntimeError("AI down")),
            ),
            patch(
                "src.services.agents.service.commit_files_workflow",
                AsyncMock(return_value=_workflow_result(pr_number=101, issue_number=71)),
            ),
        ):
            result = await service.create_agent(
                project_id=PROJECT_ID,
                owner=OWNER,
                repo=REPO,
                body=body,
                access_token=ACCESS_TOKEN,
                github_user_id=GITHUB_USER_ID,
            )

        # Fallback: description defaults to name, system_prompt stays original
        assert result.agent.description == "Fallback Agent"
        assert result.agent.system_prompt == "Help users."

    async def test_raw_mode_skips_ai_enhancement(self, mock_db):
        service = AgentsService(mock_db)
        mock_github_service = AsyncMock()
        mock_github_service.get_file_content.side_effect = FileNotFoundError()

        enhance_mock = AsyncMock()

        body = SimpleNamespace(
            name="Raw Agent",
            description="My desc",
            icon_name=None,
            system_prompt="Exact prompt.",
            tools=["read"],
            status_column="",
            default_model_id="",
            default_model_name="",
            raw=True,
        )

        with (
            patch("src.services.agents.service.github_projects_service", mock_github_service),
            patch.object(service, "_enhance_agent_content", enhance_mock),
            patch(
                "src.services.agents.service.commit_files_workflow",
                AsyncMock(return_value=_workflow_result(pr_number=102, issue_number=72)),
            ),
        ):
            result = await service.create_agent(
                project_id=PROJECT_ID,
                owner=OWNER,
                repo=REPO,
                body=body,
                access_token=ACCESS_TOKEN,
                github_user_id=GITHUB_USER_ID,
            )

        enhance_mock.assert_not_awaited()
        assert result.agent.system_prompt == "Exact prompt."
        assert result.agent.description == "My desc"


# ── T039: bulk_update_models partial failure ─────────────────────────────


class TestBulkUpdatePartialFailure:
    @pytest.fixture(autouse=True)
    def clear_cache(self):
        cache.clear()
        yield
        cache.clear()

    async def test_partial_failure_continues_and_reports(self, mock_db):
        service = AgentsService(mock_db)

        good_agent = SimpleNamespace(
            id="repo:good",
            slug="good",
            icon_name=None,
            default_model_id="old",
            default_model_name="Old",
            status=AgentStatus.ACTIVE,
        )
        bad_agent = SimpleNamespace(
            id="repo:bad",
            slug="bad",
            icon_name=None,
            default_model_id="old",
            default_model_name="Old",
            status=AgentStatus.ACTIVE,
        )
        body = SimpleNamespace(target_model_id="model-1", target_model_name="GPT-5")

        call_count = 0

        async def _side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            if kwargs["agent"].slug == "bad":
                raise RuntimeError("DB failure")

        with (
            patch.object(service, "list_agents", AsyncMock(return_value=[good_agent, bad_agent])),
            patch.object(service, "list_pending_agents", AsyncMock(return_value=[])),
            patch.object(service, "_save_runtime_preferences", AsyncMock(side_effect=_side_effect)),
        ):
            result = await service.bulk_update_models(
                project_id=PROJECT_ID,
                owner=OWNER,
                repo=REPO,
                github_user_id=GITHUB_USER_ID,
                body=body,
                access_token=ACCESS_TOKEN,
            )

        assert result.success is False
        assert result.updated_count == 1
        assert result.failed_count == 1
        assert "good" in result.updated_agents
        assert "bad" in result.failed_agents


# ── get_agent_preferences ────────────────────────────────────────────────


class TestGetAgentPreferences:
    @pytest.fixture(autouse=True)
    def clear_cache(self):
        cache.clear()
        yield
        cache.clear()

    async def test_returns_slug_to_prefs_mapping(self, mock_db):
        await _insert_agent_row_with_prefs(
            mock_db,
            agent_id="pref-1",
            slug="reviewer",
            default_model_id="m-1",
            default_model_name="Model One",
            icon_name="star",
        )
        await _insert_agent_row_with_prefs(
            mock_db,
            agent_id="pref-2",
            slug="writer",
        )

        service = AgentsService(mock_db)
        prefs = await service.get_agent_preferences(PROJECT_ID)

        assert "reviewer" in prefs
        assert prefs["reviewer"]["default_model_id"] == "m-1"
        assert prefs["reviewer"]["default_model_name"] == "Model One"
        assert prefs["reviewer"]["icon_name"] == "star"
        # Writer has no prefs set → not in result
        assert "writer" not in prefs


# ── T037: session pruning ────────────────────────────────────────────────


class TestSessionPruning:
    @pytest.fixture(autouse=True)
    def _clean_sessions(self):
        _chat_sessions.clear()
        _chat_session_timestamps.clear()
        yield
        _chat_sessions.clear()
        _chat_session_timestamps.clear()

    def test_prune_removes_expired_sessions(self):
        now = time.monotonic()
        _chat_sessions["old"] = [{"role": "user", "content": "hi"}]
        _chat_session_timestamps["old"] = now - _SESSION_TTL_SECONDS - 1

        _chat_sessions["fresh"] = [{"role": "user", "content": "hello"}]
        _chat_session_timestamps["fresh"] = now

        _prune_expired_sessions()

        assert "old" not in _chat_sessions
        assert "old" not in _chat_session_timestamps
        assert "fresh" in _chat_sessions
        assert "fresh" in _chat_session_timestamps

    def test_prune_no_op_when_all_fresh(self):
        now = time.monotonic()
        _chat_sessions["a"] = []
        _chat_session_timestamps["a"] = now

        _prune_expired_sessions()

        assert "a" in _chat_sessions


# ── Import (catalog → project DB snapshot) ───────────────────────────────


class TestImportAgent:
    """Tests for AgentsService.import_agent — DB-only catalog import."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        cache.clear()
        yield
        cache.clear()

    async def test_import_stores_agent_in_db(self, mock_db):
        """Import creates a new agent row with imported status and raw content."""
        from src.models.agents import ImportAgentRequest

        service = AgentsService(mock_db)

        with patch(
            "src.services.agents.catalog.fetch_agent_raw_content",
            AsyncMock(return_value="---\nname: Test\n---\nContent"),
        ):
            result = await service.import_agent(
                project_id=PROJECT_ID,
                owner=OWNER,
                repo=REPO,
                body=ImportAgentRequest(
                    catalog_agent_id="test-agent",
                    name="Test Agent",
                    description="A test agent",
                    source_url="https://example.com/test.md",
                ),
                github_user_id=GITHUB_USER_ID,
            )

        assert result.agent.status == AgentStatus.IMPORTED
        assert result.agent.agent_type == "imported"
        assert result.agent.catalog_agent_id == "test-agent"
        assert result.message == "Agent 'Test Agent' imported successfully."

        # Verify persisted in DB
        cursor = await mock_db.execute(
            "SELECT raw_source_content, lifecycle_status FROM agent_configs WHERE id = ?",
            (result.agent.id,),
        )
        row = await cursor.fetchone()
        assert row is not None
        assert row[0] == "---\nname: Test\n---\nContent"
        assert row[1] == "imported"

    async def test_import_rejects_duplicate(self, mock_db):
        """Import raises ValueError if the catalog agent is already imported."""
        from src.models.agents import ImportAgentRequest

        # Pre-insert an agent with the same catalog_agent_id
        await mock_db.execute(
            """INSERT INTO agent_configs
               (id, name, slug, description, system_prompt, status_column,
                tools, project_id, owner, repo, created_by,
                created_at, lifecycle_status, catalog_agent_id, agent_type)
               VALUES ('a1', 'Test', 'test', 'desc', '', '', '[]',
                       ?, ?, ?, ?, datetime('now'), 'imported', 'test-agent', 'imported')""",
            (PROJECT_ID, OWNER, REPO, GITHUB_USER_ID),
        )
        await mock_db.commit()

        service = AgentsService(mock_db)
        with pytest.raises(ValueError, match="already imported"):
            await service.import_agent(
                project_id=PROJECT_ID,
                owner=OWNER,
                repo=REPO,
                body=ImportAgentRequest(
                    catalog_agent_id="test-agent",
                    name="Test Agent",
                    description="dup",
                    source_url="https://example.com/test.md",
                ),
                github_user_id=GITHUB_USER_ID,
            )

    async def test_import_raises_on_fetch_failure(self, mock_db):
        """Import raises RuntimeError when raw content fetch fails."""
        from src.models.agents import ImportAgentRequest

        service = AgentsService(mock_db)

        with (
            patch(
                "src.services.agents.catalog.fetch_agent_raw_content",
                AsyncMock(side_effect=Exception("network error")),
            ),
            pytest.raises(RuntimeError, match="Could not fetch agent content"),
        ):
            await service.import_agent(
                project_id=PROJECT_ID,
                owner=OWNER,
                repo=REPO,
                body=ImportAgentRequest(
                    catalog_agent_id="fetch-fail",
                    name="Fail Agent",
                    description="will fail",
                    source_url="https://example.com/fail.md",
                ),
                github_user_id=GITHUB_USER_ID,
            )


# ── Install (imported agent → GitHub issue + PR) ─────────────────────────


class TestInstallAgent:
    """Tests for AgentsService.install_agent — creates GitHub issue + PR."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        cache.clear()
        yield
        cache.clear()

    async def _insert_imported_agent(self, db, agent_id: str = "imp-1") -> None:
        await db.execute(
            """INSERT INTO agent_configs
               (id, name, slug, description, system_prompt, status_column,
                tools, project_id, owner, repo, created_by,
                created_at, lifecycle_status, agent_type,
                catalog_agent_id, catalog_source_url, raw_source_content, imported_at)
               VALUES (?, 'Test Agent', 'test-agent', 'A test agent', '', '', '[]',
                       ?, ?, ?, ?, datetime('now'), 'imported', 'imported',
                       'test-agent', 'https://example.com/test.md',
                       '---\nname: Test\n---\nContent', datetime('now'))""",
            (agent_id, PROJECT_ID, OWNER, REPO, GITHUB_USER_ID),
        )
        await db.commit()

    async def test_install_creates_pr_and_updates_status(self, mock_db):
        """Install creates a GitHub PR and transitions agent to installed."""
        await self._insert_imported_agent(mock_db)
        service = AgentsService(mock_db)

        wf_result = SimpleNamespace(
            success=True,
            pr_url=f"https://github.com/{OWNER}/{REPO}/pull/10",
            pr_number=10,
            issue_number=5,
            branch_name="agent/test-agent",
            errors=[],
        )

        with patch(
            "src.services.agents.service.commit_files_workflow",
            AsyncMock(return_value=wf_result),
        ) as mock_commit:
            result = await service.install_agent(
                project_id=PROJECT_ID,
                owner=OWNER,
                repo=REPO,
                agent_id="imp-1",
                access_token=ACCESS_TOKEN,
            )

        assert result.agent.status == AgentStatus.INSTALLED
        assert result.pr_number == 10
        assert result.issue_number == 5

        # Verify commit_files_workflow was called with the raw content
        call_kwargs = mock_commit.call_args.kwargs
        files = call_kwargs["files"]
        assert files == [
            {
                "path": ".github/agents/test-agent.agent.md",
                "content": "---\nname: Test\n---\nContent",
            },
            {
                "path": ".github/prompts/test-agent.prompt.md",
                "content": "```prompt\n---\nagent: test-agent\n---\n```\n",
            },
        ]
        assert call_kwargs["issue_title"] == "Install agent: Test Agent"
        assert "https://example.com/test.md" in call_kwargs["issue_body"]
        assert "Raw agent definition (verbatim from catalog)" in call_kwargs["pr_body"]

        # Verify DB updated
        cursor = await mock_db.execute(
            "SELECT lifecycle_status, github_pr_number FROM agent_configs WHERE id = 'imp-1'",
        )
        row = await cursor.fetchone()
        assert row[0] == "installed"
        assert row[1] == 10

    async def test_install_raises_for_non_imported_agent(self, mock_db):
        """Install raises ValueError if agent is not in imported state."""
        await _insert_agent_row(
            mock_db, agent_id="active-1", slug="active-agent", lifecycle_status="pending_pr"
        )
        service = AgentsService(mock_db)

        with pytest.raises(ValueError, match="not in imported state"):
            await service.install_agent(
                project_id=PROJECT_ID,
                owner=OWNER,
                repo=REPO,
                agent_id="active-1",
                access_token=ACCESS_TOKEN,
            )

    async def test_install_raises_for_missing_agent(self, mock_db):
        """Install raises LookupError if agent doesn't exist."""
        service = AgentsService(mock_db)

        with pytest.raises(LookupError, match="not found"):
            await service.install_agent(
                project_id=PROJECT_ID,
                owner=OWNER,
                repo=REPO,
                agent_id="nonexistent",
                access_token=ACCESS_TOKEN,
            )

    async def test_install_raises_on_workflow_failure(self, mock_db):
        """Install raises RuntimeError when the GitHub workflow fails."""
        await self._insert_imported_agent(mock_db)
        service = AgentsService(mock_db)

        wf_result = SimpleNamespace(
            success=False,
            pr_url=None,
            pr_number=None,
            issue_number=None,
            branch_name=None,
            errors=["branch conflict"],
        )

        with (
            patch(
                "src.services.agents.service.commit_files_workflow",
                AsyncMock(return_value=wf_result),
            ),
            pytest.raises(RuntimeError, match="Install failed"),
        ):
            await service.install_agent(
                project_id=PROJECT_ID,
                owner=OWNER,
                repo=REPO,
                agent_id="imp-1",
                access_token=ACCESS_TOKEN,
            )


# ---------------------------------------------------------------------------
# NEW COVERAGE TESTS — gap areas
# ---------------------------------------------------------------------------


# ── _extract_agent_preview ───────────────────────────────────────────────


class TestExtractAgentPreview:
    """Tests for the static ``_extract_agent_preview`` method."""

    def test_valid_agent_config_block_returns_preview(self):
        text = (
            'Here is your config:\n```agent-config\n'
            '{"name": "Security Bot", "description": "Scans for vulns", '
            '"system_prompt": "You are a security bot.", "tools": ["read"]}\n```'
        )
        preview = AgentsService._extract_agent_preview(text)
        assert preview is not None
        assert preview.name == "Security Bot"
        assert preview.slug == "security-bot"
        assert preview.description == "Scans for vulns"
        assert preview.system_prompt == "You are a security bot."
        assert preview.tools == ["read"]

    def test_no_agent_config_block_returns_none(self):
        text = "Just some regular text without any config block."
        assert AgentsService._extract_agent_preview(text) is None

    def test_invalid_json_in_block_returns_none(self):
        text = "```agent-config\n{not valid json}\n```"
        assert AgentsService._extract_agent_preview(text) is None

    def test_empty_name_returns_none(self):
        text = '```agent-config\n{"name": "", "description": "test"}\n```'
        assert AgentsService._extract_agent_preview(text) is None

    def test_missing_name_key_returns_none(self):
        text = '```agent-config\n{"description": "no name field"}\n```'
        assert AgentsService._extract_agent_preview(text) is None

    def test_minimal_valid_config(self):
        text = '```agent-config\n{"name": "Bot"}\n```'
        preview = AgentsService._extract_agent_preview(text)
        assert preview is not None
        assert preview.name == "Bot"
        assert preview.description == ""
        assert preview.tools == []


# ── _coerce_agent_status ─────────────────────────────────────────────────


class TestCoerceAgentStatus:
    """Tests for AgentsService._coerce_agent_status."""

    def _svc(self):
        """Return an AgentsService with a stub db (not used by the method)."""
        return AgentsService(AsyncMock())

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("active", AgentStatus.ACTIVE),
            ("pending_pr", AgentStatus.PENDING_PR),
            ("pending_deletion", AgentStatus.PENDING_DELETION),
            ("imported", AgentStatus.IMPORTED),
            ("installed", AgentStatus.INSTALLED),
        ],
    )
    def test_valid_statuses(self, raw, expected):
        assert self._svc()._coerce_agent_status(raw) == expected

    def test_none_defaults_to_pending_pr(self):
        assert self._svc()._coerce_agent_status(None) == AgentStatus.PENDING_PR

    def test_empty_string_defaults_to_pending_pr(self):
        assert self._svc()._coerce_agent_status("") == AgentStatus.PENDING_PR

    def test_unknown_value_defaults_to_pending_pr(self):
        assert self._svc()._coerce_agent_status("bogus_state") == AgentStatus.PENDING_PR


# ── _resolve_agent ───────────────────────────────────────────────────────


class TestResolveAgent:
    """Tests for AgentsService._resolve_agent (local DB lookup)."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        cache.clear()
        yield
        cache.clear()

    async def test_resolve_by_id(self, mock_db):
        await _insert_agent_row(mock_db, agent_id="agent-x", slug="my-agent")
        service = AgentsService(mock_db)
        agent = await service._resolve_agent(PROJECT_ID, "agent-x")
        assert agent is not None
        assert agent.id == "agent-x"
        assert agent.slug == "my-agent"

    async def test_resolve_by_slug_fallback(self, mock_db):
        await _insert_agent_row(mock_db, agent_id="agent-y", slug="slug-lookup")
        service = AgentsService(mock_db)
        agent = await service._resolve_agent(PROJECT_ID, "slug-lookup")
        assert agent is not None
        assert agent.id == "agent-y"

    async def test_resolve_returns_none_when_not_found(self, mock_db):
        service = AgentsService(mock_db)
        agent = await service._resolve_agent(PROJECT_ID, "nonexistent")
        assert agent is None

    async def test_resolve_handles_invalid_tools_json(self, mock_db):
        """If tools JSON is corrupt, agent still resolves with empty tools."""
        await _insert_agent_row(mock_db, agent_id="bad-tools", slug="bad-tools-agent")
        # Corrupt the tools column
        await mock_db.execute(
            "UPDATE agent_configs SET tools = 'NOT-JSON' WHERE id = 'bad-tools'"
        )
        await mock_db.commit()

        service = AgentsService(mock_db)
        agent = await service._resolve_agent(PROJECT_ID, "bad-tools")
        assert agent is not None
        assert agent.tools == []


# ── _resolve_listed_agent ────────────────────────────────────────────────


class TestResolveListedAgent:
    """Tests for AgentsService._resolve_listed_agent."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        cache.clear()
        yield
        cache.clear()

    async def test_resolve_from_local_db(self, mock_db):
        await _insert_agent_row(mock_db, agent_id="local-1", slug="local-agent")
        service = AgentsService(mock_db)
        mock_github_service = AsyncMock()
        mock_github_service.get_directory_contents.return_value = []

        with patch("src.services.agents.service.github_projects_service", mock_github_service):
            agent = await service._resolve_listed_agent(
                project_id=PROJECT_ID,
                owner=OWNER,
                repo=REPO,
                access_token=ACCESS_TOKEN,
                agent_id="local-1",
            )

        assert agent is not None
        assert agent.id == "local-1"

    async def test_resolve_from_repo_agents(self, mock_db):
        """When not in local DB, falls back to repo listing."""
        service = AgentsService(mock_db)
        mock_github_service = AsyncMock()
        mock_github_service.get_directory_contents.return_value = [_repo_entry("reviewer")]

        with patch("src.services.agents.service.github_projects_service", mock_github_service):
            agent = await service._resolve_listed_agent(
                project_id=PROJECT_ID,
                owner=OWNER,
                repo=REPO,
                access_token=ACCESS_TOKEN,
                agent_id="repo:reviewer",
            )

        assert agent is not None
        assert agent.slug == "reviewer"
        assert agent.source == AgentSource.REPO

    async def test_resolve_returns_none_when_not_anywhere(self, mock_db):
        service = AgentsService(mock_db)
        mock_github_service = AsyncMock()
        mock_github_service.get_directory_contents.return_value = []

        with patch("src.services.agents.service.github_projects_service", mock_github_service):
            agent = await service._resolve_listed_agent(
                project_id=PROJECT_ID,
                owner=OWNER,
                repo=REPO,
                access_token=ACCESS_TOKEN,
                agent_id="does-not-exist",
            )

        assert agent is None


# ── chat() ───────────────────────────────────────────────────────────────


class TestChat:
    """Tests for AgentsService.chat — multi-turn agent refinement."""

    @pytest.fixture(autouse=True)
    def _clean_sessions(self):
        _chat_sessions.clear()
        _chat_session_timestamps.clear()
        yield
        _chat_sessions.clear()
        _chat_session_timestamps.clear()

    async def test_chat_first_message_creates_session(self, mock_db):
        service = AgentsService(mock_db)
        mock_ai = AsyncMock()
        mock_ai._call_completion = AsyncMock(return_value="What should the agent do?")

        with patch("src.services.ai_agent.get_ai_agent_service", return_value=mock_ai):
            resp = await service.chat(
                project_id=PROJECT_ID,
                message="I want a code reviewer",
                session_id=None,
                access_token=ACCESS_TOKEN,
            )

        assert resp.reply == "What should the agent do?"
        assert resp.session_id  # non-empty
        assert resp.is_complete is False
        assert resp.preview is None
        assert resp.session_id in _chat_sessions

    async def test_chat_continues_existing_session(self, mock_db):
        # Pre-seed session
        sid = "existing-session"
        _chat_sessions[sid] = [
            {"role": "system", "content": "system prompt"},
            {"role": "user", "content": "first message"},
            {"role": "assistant", "content": "follow up question"},
        ]
        _chat_session_timestamps[sid] = time.monotonic()

        service = AgentsService(mock_db)
        mock_ai = AsyncMock()
        mock_ai._call_completion = AsyncMock(return_value="Got it, what tools?")

        with patch("src.services.ai_agent.get_ai_agent_service", return_value=mock_ai):
            resp = await service.chat(
                project_id=PROJECT_ID,
                message="It should review PRs",
                session_id=sid,
                access_token=ACCESS_TOKEN,
            )

        assert resp.session_id == sid
        assert resp.is_complete is False
        # History should have grown
        assert len(_chat_sessions[sid]) == 5  # system + user + assistant + user + assistant

    async def test_chat_complete_response_cleans_session(self, mock_db):
        service = AgentsService(mock_db)
        complete_reply = (
            'Here is your config:\n```agent-config\n'
            '{"name": "PR Reviewer", "description": "Reviews PRs", '
            '"system_prompt": "You review PRs.", "tools": ["read"]}\n```'
        )
        mock_ai = AsyncMock()
        mock_ai._call_completion = AsyncMock(return_value=complete_reply)

        with patch("src.services.ai_agent.get_ai_agent_service", return_value=mock_ai):
            resp = await service.chat(
                project_id=PROJECT_ID,
                message="Create a PR reviewer",
                session_id=None,
                access_token=ACCESS_TOKEN,
            )

        assert resp.is_complete is True
        assert resp.preview is not None
        assert resp.preview.name == "PR Reviewer"
        assert resp.preview.slug == "pr-reviewer"
        # Session should be cleaned up after completion
        assert resp.session_id not in _chat_sessions

    async def test_chat_ai_failure_propagates(self, mock_db):
        service = AgentsService(mock_db)
        mock_ai = AsyncMock()
        mock_ai._call_completion = AsyncMock(side_effect=RuntimeError("AI offline"))

        with (
            patch("src.services.ai_agent.get_ai_agent_service", return_value=mock_ai),
            pytest.raises(RuntimeError, match="AI offline"),
        ):
            await service.chat(
                project_id=PROJECT_ID,
                message="hello",
                session_id=None,
                access_token=ACCESS_TOKEN,
            )

    async def test_chat_evicts_oldest_when_at_capacity(self, mock_db):
        """When session limit is reached, the oldest session is evicted."""
        # Fill up to the max
        for i in range(_MAX_CHAT_SESSIONS):
            sid = f"session-{i}"
            _chat_sessions[sid] = [{"role": "user", "content": "hi"}]
            _chat_session_timestamps[sid] = time.monotonic() + i

        # The oldest is session-0
        assert "session-0" in _chat_sessions

        service = AgentsService(mock_db)
        mock_ai = AsyncMock()
        mock_ai._call_completion = AsyncMock(return_value="hello")

        with patch("src.services.ai_agent.get_ai_agent_service", return_value=mock_ai):
            await service.chat(
                project_id=PROJECT_ID,
                message="new session",
                session_id="brand-new-session",
                access_token=ACCESS_TOKEN,
            )

        # Oldest should have been evicted
        assert "session-0" not in _chat_sessions
        assert "brand-new-session" in _chat_sessions

    async def test_chat_non_string_response_converted(self, mock_db):
        """If AI returns non-string, it should be converted via str()."""
        service = AgentsService(mock_db)
        mock_ai = AsyncMock()
        mock_ai._call_completion = AsyncMock(return_value=12345)

        with patch("src.services.ai_agent.get_ai_agent_service", return_value=mock_ai):
            resp = await service.chat(
                project_id=PROJECT_ID,
                message="test",
                session_id=None,
                access_token=ACCESS_TOKEN,
            )

        assert resp.reply == "12345"


# ── _enhance_agent_content ───────────────────────────────────────────────


class TestEnhanceAgentContent:
    """Tests for AgentsService._enhance_agent_content."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        cache.clear()
        yield
        cache.clear()

    async def test_successful_enhancement(self, mock_db):
        service = AgentsService(mock_db)
        ai_response = (
            '{"system_prompt": "Enhanced prompt.", "description": "A smart bot", '
            '"tools": ["read", "search"]}'
        )
        mock_ai = AsyncMock()
        mock_ai._call_completion = AsyncMock(return_value=ai_response)

        with (
            patch("src.services.ai_agent.get_ai_agent_service", return_value=mock_ai),
            patch.object(service, "_gather_agent_examples", AsyncMock(return_value=[])),
        ):
            result = await service._enhance_agent_content(
                name="Test Agent",
                system_prompt="Do stuff",
                owner=OWNER,
                repo=REPO,
                access_token=ACCESS_TOKEN,
            )

        assert result["system_prompt"] == "Enhanced prompt."
        assert result["description"] == "A smart bot"
        assert result["tools"] == ["read", "search"]

    async def test_enhancement_strips_markdown_fences(self, mock_db):
        service = AgentsService(mock_db)
        ai_response = (
            '```json\n{"system_prompt": "Prompt.", "description": "Desc", "tools": []}\n```'
        )
        mock_ai = AsyncMock()
        mock_ai._call_completion = AsyncMock(return_value=ai_response)

        with (
            patch("src.services.ai_agent.get_ai_agent_service", return_value=mock_ai),
            patch.object(service, "_gather_agent_examples", AsyncMock(return_value=[])),
        ):
            result = await service._enhance_agent_content(
                name="Test",
                system_prompt="raw",
                owner=OWNER,
                repo=REPO,
                access_token=ACCESS_TOKEN,
            )

        assert result["system_prompt"] == "Prompt."

    async def test_enhancement_invalid_json_raises(self, mock_db):
        service = AgentsService(mock_db)
        mock_ai = AsyncMock()
        mock_ai._call_completion = AsyncMock(return_value="not json at all")

        with (
            patch("src.services.ai_agent.get_ai_agent_service", return_value=mock_ai),
            patch.object(service, "_gather_agent_examples", AsyncMock(return_value=[])),
            pytest.raises((json.JSONDecodeError, AttributeError)),
        ):
            await service._enhance_agent_content(
                name="Test",
                system_prompt="raw",
                owner=OWNER,
                repo=REPO,
                access_token=ACCESS_TOKEN,
            )

    async def test_enhancement_with_examples(self, mock_db):
        service = AgentsService(mock_db)
        ai_response = '{"system_prompt": "EP", "description": "D", "tools": []}'
        mock_ai = AsyncMock()
        mock_ai._call_completion = AsyncMock(return_value=ai_response)

        examples = ["### reviewer.agent.md\n```\ncontent\n```"]

        with (
            patch("src.services.ai_agent.get_ai_agent_service", return_value=mock_ai),
            patch.object(service, "_gather_agent_examples", AsyncMock(return_value=examples)),
        ):
            result = await service._enhance_agent_content(
                name="Test",
                system_prompt="raw",
                owner=OWNER,
                repo=REPO,
                access_token=ACCESS_TOKEN,
            )

        # Verify examples were included in the system message
        call_args = mock_ai._call_completion.call_args
        messages = call_args.kwargs["messages"]
        system_msg = messages[0]["content"]
        assert "Reference" in system_msg
        assert "reviewer.agent.md" in system_msg
        assert result["system_prompt"] == "EP"

    async def test_enhancement_non_list_tools_returns_empty_list(self, mock_db):
        service = AgentsService(mock_db)
        ai_response = '{"system_prompt": "P", "description": "D", "tools": "not-a-list"}'
        mock_ai = AsyncMock()
        mock_ai._call_completion = AsyncMock(return_value=ai_response)

        with (
            patch("src.services.ai_agent.get_ai_agent_service", return_value=mock_ai),
            patch.object(service, "_gather_agent_examples", AsyncMock(return_value=[])),
        ):
            result = await service._enhance_agent_content(
                name="Test",
                system_prompt="raw",
                owner=OWNER,
                repo=REPO,
                access_token=ACCESS_TOKEN,
            )

        assert result["tools"] == []


# ── _gather_agent_examples ───────────────────────────────────────────────


class TestGatherAgentExamples:
    """Tests for AgentsService._gather_agent_examples."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        cache.clear()
        yield
        cache.clear()

    async def test_gathers_up_to_three_examples(self, mock_db):
        service = AgentsService(mock_db)
        entries = [
            {"name": f"agent-{i}.agent.md"} for i in range(5)
        ]
        mock_github = AsyncMock()
        mock_github.get_directory_contents = AsyncMock(return_value=entries)
        mock_github.get_file_content = AsyncMock(
            return_value={"content": "---\nname: Test\n---\nPrompt content here."}
        )

        with patch("src.services.agents.service.github_projects_service", mock_github):
            examples = await service._gather_agent_examples(OWNER, REPO, ACCESS_TOKEN)

        assert len(examples) == 3
        assert all("agent-" in ex for ex in examples)

    async def test_skips_non_agent_md_files(self, mock_db):
        service = AgentsService(mock_db)
        entries = [
            {"name": "copilot-instructions.md"},
            {"name": "readme.md"},
            {"name": "valid.agent.md"},
        ]
        mock_github = AsyncMock()
        mock_github.get_directory_contents = AsyncMock(return_value=entries)
        mock_github.get_file_content = AsyncMock(return_value={"content": "content"})

        with patch("src.services.agents.service.github_projects_service", mock_github):
            examples = await service._gather_agent_examples(OWNER, REPO, ACCESS_TOKEN)

        assert len(examples) == 1
        assert "valid.agent.md" in examples[0]

    async def test_returns_empty_on_directory_failure(self, mock_db):
        service = AgentsService(mock_db)
        mock_github = AsyncMock()
        mock_github.get_directory_contents = AsyncMock(side_effect=RuntimeError("fail"))

        with patch("src.services.agents.service.github_projects_service", mock_github):
            examples = await service._gather_agent_examples(OWNER, REPO, ACCESS_TOKEN)

        assert examples == []

    async def test_skips_file_on_read_failure(self, mock_db):
        service = AgentsService(mock_db)
        entries = [{"name": "a.agent.md"}, {"name": "b.agent.md"}]
        mock_github = AsyncMock()
        mock_github.get_directory_contents = AsyncMock(return_value=entries)

        call_count = 0

        async def _file_content(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("read error")
            return {"content": "good content"}

        mock_github.get_file_content = AsyncMock(side_effect=_file_content)

        with patch("src.services.agents.service.github_projects_service", mock_github):
            examples = await service._gather_agent_examples(OWNER, REPO, ACCESS_TOKEN)

        assert len(examples) == 1


# ── _auto_generate_metadata ──────────────────────────────────────────────


class TestAutoGenerateMetadata:
    """Tests for AgentsService._auto_generate_metadata."""

    async def test_successful_metadata_generation(self, mock_db):
        service = AgentsService(mock_db)
        mock_ai = AsyncMock()
        mock_ai._call_completion = AsyncMock(
            return_value='{"description": "Reviews PRs", "tools": ["read", "github/*"]}'
        )

        with patch("src.services.ai_agent.get_ai_agent_service", return_value=mock_ai):
            result = await service._auto_generate_metadata(
                name="PR Reviewer",
                system_prompt="Review pull requests.",
                access_token=ACCESS_TOKEN,
            )

        assert result["description"] == "Reviews PRs"
        assert result["tools"] == ["read", "github/*"]

    async def test_metadata_strips_markdown_fences(self, mock_db):
        service = AgentsService(mock_db)
        mock_ai = AsyncMock()
        mock_ai._call_completion = AsyncMock(
            return_value='```json\n{"description": "Desc", "tools": []}\n```'
        )

        with patch("src.services.ai_agent.get_ai_agent_service", return_value=mock_ai):
            result = await service._auto_generate_metadata(
                name="Bot",
                system_prompt="Do things.",
                access_token=ACCESS_TOKEN,
            )

        assert result["description"] == "Desc"

    async def test_metadata_invalid_json_returns_fallback(self, mock_db):
        service = AgentsService(mock_db)
        mock_ai = AsyncMock()
        mock_ai._call_completion = AsyncMock(return_value="garbage response")

        with patch("src.services.ai_agent.get_ai_agent_service", return_value=mock_ai):
            result = await service._auto_generate_metadata(
                name="Fallback Bot",
                system_prompt="stuff",
                access_token=ACCESS_TOKEN,
            )

        assert result["description"] == "Fallback Bot"
        assert result["tools"] == []

    async def test_metadata_non_list_tools_returns_empty(self, mock_db):
        service = AgentsService(mock_db)
        mock_ai = AsyncMock()
        mock_ai._call_completion = AsyncMock(
            return_value='{"description": "D", "tools": "string-not-list"}'
        )

        with patch("src.services.ai_agent.get_ai_agent_service", return_value=mock_ai):
            result = await service._auto_generate_metadata(
                name="X",
                system_prompt="Y",
                access_token=ACCESS_TOKEN,
            )

        assert result["tools"] == []


# ── _generate_rich_descriptions ──────────────────────────────────────────


class TestGenerateRichDescriptions:
    """Tests for AgentsService._generate_rich_descriptions."""

    async def test_successful_description_generation(self, mock_db):
        service = AgentsService(mock_db)
        mock_ai = AsyncMock()
        mock_ai._call_completion = AsyncMock(
            return_value='{"issue_body": "## Issue\\nDetails", "pr_body": "## PR\\nChanges"}'
        )

        with patch("src.services.ai_agent.get_ai_agent_service", return_value=mock_ai):
            result = await service._generate_rich_descriptions(
                name="Bot",
                slug="bot",
                description="A bot",
                system_prompt="You are a bot.",
                tools=["read"],
                access_token=ACCESS_TOKEN,
            )

        assert "Issue" in result["issue_body"]
        assert "PR" in result["pr_body"]

    async def test_description_strips_markdown_fences(self, mock_db):
        service = AgentsService(mock_db)
        mock_ai = AsyncMock()
        mock_ai._call_completion = AsyncMock(
            return_value='```json\n{"issue_body": "issue", "pr_body": "pr"}\n```'
        )

        with patch("src.services.ai_agent.get_ai_agent_service", return_value=mock_ai):
            result = await service._generate_rich_descriptions(
                name="Bot",
                slug="bot",
                description="A bot",
                system_prompt="You are a bot.",
                tools=[],
                access_token=ACCESS_TOKEN,
            )

        assert result["issue_body"] == "issue"
        assert result["pr_body"] == "pr"

    async def test_description_invalid_json_raises(self, mock_db):
        service = AgentsService(mock_db)
        mock_ai = AsyncMock()
        mock_ai._call_completion = AsyncMock(return_value="not json")

        with (
            patch("src.services.ai_agent.get_ai_agent_service", return_value=mock_ai),
            pytest.raises((json.JSONDecodeError, AttributeError)),
        ):
            await service._generate_rich_descriptions(
                name="Bot",
                slug="bot",
                description="A bot",
                system_prompt="You are a bot.",
                tools=[],
                access_token=ACCESS_TOKEN,
            )


# ── Error paths: create_agent ────────────────────────────────────────────


class TestCreateAgentErrors:
    """Error-path tests for AgentsService.create_agent."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        cache.clear()
        yield
        cache.clear()

    async def test_empty_slug_raises_value_error(self, mock_db):
        service = AgentsService(mock_db)
        body = SimpleNamespace(
            name="!!!",
            description="test",
            icon_name=None,
            system_prompt="Do stuff.",
            tools=[],
            status_column="",
            default_model_id="",
            default_model_name="",
            raw=True,
        )
        with pytest.raises(ValueError, match="empty slug"):
            await service.create_agent(
                project_id=PROJECT_ID,
                owner=OWNER,
                repo=REPO,
                body=body,
                access_token=ACCESS_TOKEN,
                github_user_id=GITHUB_USER_ID,
            )

    async def test_duplicate_slug_in_db_raises_value_error(self, mock_db):
        await _insert_agent_row(mock_db, agent_id="existing-1", slug="reviewer")
        service = AgentsService(mock_db)
        mock_github_service = AsyncMock()
        mock_github_service.get_file_content.side_effect = FileNotFoundError()

        body = SimpleNamespace(
            name="Reviewer",
            description="test",
            icon_name=None,
            system_prompt="Do stuff.",
            tools=[],
            status_column="",
            default_model_id="",
            default_model_name="",
            raw=True,
        )

        with (
            patch("src.services.agents.service.github_projects_service", mock_github_service),
            pytest.raises(ValueError, match="already exists"),
        ):
            await service.create_agent(
                project_id=PROJECT_ID,
                owner=OWNER,
                repo=REPO,
                body=body,
                access_token=ACCESS_TOKEN,
                github_user_id=GITHUB_USER_ID,
            )

    async def test_duplicate_file_in_repo_raises_value_error(self, mock_db):
        service = AgentsService(mock_db)
        mock_github_service = AsyncMock()
        mock_github_service.get_file_content.return_value = {"content": "existing"}

        body = SimpleNamespace(
            name="Reviewer",
            description="test",
            icon_name=None,
            system_prompt="Do stuff.",
            tools=[],
            status_column="",
            default_model_id="",
            default_model_name="",
            raw=True,
        )

        with (
            patch("src.services.agents.service.github_projects_service", mock_github_service),
            pytest.raises(ValueError, match="already exists in the repository"),
        ):
            await service.create_agent(
                project_id=PROJECT_ID,
                owner=OWNER,
                repo=REPO,
                body=body,
                access_token=ACCESS_TOKEN,
                github_user_id=GITHUB_USER_ID,
            )

    async def test_commit_workflow_failure_raises_runtime_error(self, mock_db):
        service = AgentsService(mock_db)
        mock_github_service = AsyncMock()
        mock_github_service.get_file_content.side_effect = FileNotFoundError()

        body = SimpleNamespace(
            name="Failure Agent",
            description="test",
            icon_name=None,
            system_prompt="Do stuff.",
            tools=[],
            status_column="",
            default_model_id="",
            default_model_name="",
            raw=True,
        )

        wf_result = SimpleNamespace(
            success=False,
            pr_url=None,
            pr_number=None,
            issue_number=None,
            errors=["branch conflict"],
        )

        with (
            patch("src.services.agents.service.github_projects_service", mock_github_service),
            patch(
                "src.services.agents.service.commit_files_workflow",
                AsyncMock(return_value=wf_result),
            ),
            pytest.raises(RuntimeError, match="Agent creation pipeline failed"),
        ):
            await service.create_agent(
                project_id=PROJECT_ID,
                owner=OWNER,
                repo=REPO,
                body=body,
                access_token=ACCESS_TOKEN,
                github_user_id=GITHUB_USER_ID,
            )


# ── Error paths: delete_agent ────────────────────────────────────────────


class TestDeleteAgentErrors:
    """Error-path tests for AgentsService.delete_agent."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        cache.clear()
        yield
        cache.clear()

    async def test_delete_not_found_raises_lookup_error(self, mock_db):
        service = AgentsService(mock_db)
        mock_github_service = AsyncMock()
        mock_github_service.get_directory_contents.return_value = []

        with (
            patch("src.services.agents.service.github_projects_service", mock_github_service),
            pytest.raises(LookupError, match="not found"),
        ):
            await service.delete_agent(
                project_id=PROJECT_ID,
                owner=OWNER,
                repo=REPO,
                agent_id="nonexistent",
                access_token=ACCESS_TOKEN,
                github_user_id=GITHUB_USER_ID,
            )

    async def test_delete_already_pending_raises_value_error(self, mock_db):
        await _insert_agent_row(
            mock_db,
            agent_id="del-1",
            slug="to-delete",
            lifecycle_status=AgentStatus.PENDING_DELETION.value,
        )
        service = AgentsService(mock_db)
        mock_github_service = AsyncMock()
        mock_github_service.get_directory_contents.return_value = []

        with (
            patch("src.services.agents.service.github_projects_service", mock_github_service),
            pytest.raises(ValueError, match="already pending deletion"),
        ):
            await service.delete_agent(
                project_id=PROJECT_ID,
                owner=OWNER,
                repo=REPO,
                agent_id="del-1",
                access_token=ACCESS_TOKEN,
                github_user_id=GITHUB_USER_ID,
            )

    async def test_delete_pipeline_failure_raises_runtime_error(self, mock_db):
        await _insert_agent_row(mock_db, agent_id="del-2", slug="fail-delete")
        service = AgentsService(mock_db)
        mock_github_service = AsyncMock()
        mock_github_service.get_directory_contents.return_value = []

        wf_result = SimpleNamespace(
            success=False,
            pr_url=None,
            pr_number=None,
            issue_number=None,
            errors=["permission denied"],
        )

        with (
            patch("src.services.agents.service.github_projects_service", mock_github_service),
            patch(
                "src.services.agents.service.commit_files_workflow",
                AsyncMock(return_value=wf_result),
            ),
            pytest.raises(RuntimeError, match="Agent deletion pipeline failed"),
        ):
            await service.delete_agent(
                project_id=PROJECT_ID,
                owner=OWNER,
                repo=REPO,
                agent_id="del-2",
                access_token=ACCESS_TOKEN,
                github_user_id=GITHUB_USER_ID,
            )


# ── Error paths: update_agent ────────────────────────────────────────────


class TestUpdateAgentErrors:
    """Error-path tests for AgentsService.update_agent."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        cache.clear()
        yield
        cache.clear()

    async def test_update_not_found_raises_lookup_error(self, mock_db):
        service = AgentsService(mock_db)
        mock_github_service = AsyncMock()
        mock_github_service.get_directory_contents.return_value = []

        body = SimpleNamespace(
            name="Updated",
            description="new desc",
            icon_name=None,
            system_prompt="New prompt.",
            tools=["read"],
            default_model_id=None,
            default_model_name=None,
        )

        with (
            patch("src.services.agents.service.github_projects_service", mock_github_service),
            pytest.raises(LookupError, match="not found"),
        ):
            await service.update_agent(
                project_id=PROJECT_ID,
                owner=OWNER,
                repo=REPO,
                agent_id="nonexistent",
                body=body,
                access_token=ACCESS_TOKEN,
                github_user_id=GITHUB_USER_ID,
            )

    async def test_update_pending_deletion_raises_value_error(self, mock_db):
        await _insert_agent_row(
            mock_db,
            agent_id="upd-del-1",
            slug="pending-del-agent",
            lifecycle_status=AgentStatus.PENDING_DELETION.value,
        )
        service = AgentsService(mock_db)
        mock_github_service = AsyncMock()
        mock_github_service.get_directory_contents.return_value = []

        body = SimpleNamespace(
            name="Updated",
            description="new desc",
            icon_name=None,
            system_prompt="New prompt.",
            tools=["read"],
            default_model_id=None,
            default_model_name=None,
        )

        with (
            patch("src.services.agents.service.github_projects_service", mock_github_service),
            pytest.raises(ValueError, match="pending deletion"),
        ):
            await service.update_agent(
                project_id=PROJECT_ID,
                owner=OWNER,
                repo=REPO,
                agent_id="upd-del-1",
                body=body,
                access_token=ACCESS_TOKEN,
                github_user_id=GITHUB_USER_ID,
            )

    async def test_update_runtime_preference_only(self, mock_db):
        """When only model/icon fields are set, no PR is created."""
        await _insert_agent_row(mock_db, agent_id="upd-pref-1", slug="pref-agent")
        service = AgentsService(mock_db)
        mock_github_service = AsyncMock()
        mock_github_service.get_directory_contents.return_value = []

        body = SimpleNamespace(
            name=None,
            description=None,
            icon_name="rocket",
            system_prompt=None,
            tools=None,
            default_model_id="model-new",
            default_model_name="New Model",
        )

        with patch("src.services.agents.service.github_projects_service", mock_github_service):
            result = await service.update_agent(
                project_id=PROJECT_ID,
                owner=OWNER,
                repo=REPO,
                agent_id="upd-pref-1",
                body=body,
                access_token=ACCESS_TOKEN,
                github_user_id=GITHUB_USER_ID,
            )

        # No PR created
        assert result.pr_number == 0
        assert result.pr_url == ""
        assert result.agent.default_model_id == "model-new"
        assert result.agent.default_model_name == "New Model"
        assert result.agent.icon_name == "rocket"

    async def test_update_pipeline_failure_raises_runtime_error(self, mock_db):
        await _insert_agent_row(mock_db, agent_id="upd-fail-1", slug="fail-update")
        service = AgentsService(mock_db)
        mock_github_service = AsyncMock()
        mock_github_service.get_directory_contents.return_value = []

        body = SimpleNamespace(
            name="Updated",
            description="new desc",
            icon_name=None,
            system_prompt="New prompt.",
            tools=["read"],
            default_model_id=None,
            default_model_name=None,
        )

        wf_result = SimpleNamespace(
            success=False,
            pr_url=None,
            pr_number=None,
            issue_number=None,
            errors=["merge conflict"],
        )

        with (
            patch("src.services.agents.service.github_projects_service", mock_github_service),
            patch(
                "src.services.agents.service.commit_files_workflow",
                AsyncMock(return_value=wf_result),
            ),
            pytest.raises(RuntimeError, match="Agent update pipeline failed"),
        ):
            await service.update_agent(
                project_id=PROJECT_ID,
                owner=OWNER,
                repo=REPO,
                agent_id="upd-fail-1",
                body=body,
                access_token=ACCESS_TOKEN,
                github_user_id=GITHUB_USER_ID,
            )


# ── _cleanup_resolved_pending_agents ─────────────────────────────────────


class TestCleanupResolvedPendingAgents:
    """Tests for the reconciliation logic that removes stale local rows."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        cache.clear()
        yield
        cache.clear()

    async def test_pending_pr_cleaned_when_slug_appears_in_repo(self, mock_db):
        await _insert_agent_row(
            mock_db,
            agent_id="pending-1",
            slug="merged-agent",
            lifecycle_status=AgentStatus.PENDING_PR.value,
        )
        repo_agents = [_make_repo_agent("merged-agent")]
        service = AgentsService(mock_db)

        await service._cleanup_resolved_pending_agents(
            project_id=PROJECT_ID, repo_agents=repo_agents
        )

        cursor = await mock_db.execute(
            "SELECT COUNT(*) AS count FROM agent_configs WHERE id = 'pending-1'"
        )
        row = await cursor.fetchone()
        assert row["count"] == 0

    async def test_pending_deletion_cleaned_when_slug_gone_from_repo(self, mock_db):
        await _insert_agent_row(
            mock_db,
            agent_id="del-tombstone-1",
            slug="removed-agent",
            lifecycle_status=AgentStatus.PENDING_DELETION.value,
        )
        repo_agents = []  # Agent file gone from repo
        service = AgentsService(mock_db)

        await service._cleanup_resolved_pending_agents(
            project_id=PROJECT_ID, repo_agents=repo_agents
        )

        cursor = await mock_db.execute(
            "SELECT COUNT(*) AS count FROM agent_configs WHERE id = 'del-tombstone-1'"
        )
        row = await cursor.fetchone()
        assert row["count"] == 0

    async def test_active_agent_not_cleaned(self, mock_db):
        await _insert_agent_row(
            mock_db,
            agent_id="active-1",
            slug="active-agent",
            lifecycle_status=AgentStatus.ACTIVE.value,
        )
        repo_agents = [_make_repo_agent("active-agent")]
        service = AgentsService(mock_db)

        await service._cleanup_resolved_pending_agents(
            project_id=PROJECT_ID, repo_agents=repo_agents
        )

        cursor = await mock_db.execute(
            "SELECT COUNT(*) AS count FROM agent_configs WHERE id = 'active-1'"
        )
        row = await cursor.fetchone()
        assert row["count"] == 1

    async def test_no_deletions_when_nothing_resolved(self, mock_db):
        # Pending PR agent, but slug NOT in repo yet → not cleaned
        await _insert_agent_row(
            mock_db,
            agent_id="still-pending",
            slug="waiting-agent",
            lifecycle_status=AgentStatus.PENDING_PR.value,
        )
        repo_agents = []
        service = AgentsService(mock_db)

        await service._cleanup_resolved_pending_agents(
            project_id=PROJECT_ID, repo_agents=repo_agents
        )

        cursor = await mock_db.execute(
            "SELECT COUNT(*) AS count FROM agent_configs WHERE id = 'still-pending'"
        )
        row = await cursor.fetchone()
        assert row["count"] == 1


# ── import_agent additional error paths ──────────────────────────────────


class TestImportAgentErrors:
    """Additional error-path tests for import_agent."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        cache.clear()
        yield
        cache.clear()

    async def test_import_missing_catalog_agent_id_raises(self, mock_db):
        from src.models.agents import ImportAgentRequest

        service = AgentsService(mock_db)
        with pytest.raises(ValueError, match="catalog_agent_id is required"):
            await service.import_agent(
                project_id=PROJECT_ID,
                owner=OWNER,
                repo=REPO,
                body=ImportAgentRequest(
                    catalog_agent_id="",
                    name="Test",
                    description="d",
                    source_url="https://example.com/test.md",
                ),
                github_user_id=GITHUB_USER_ID,
            )


# ── install_agent additional error paths ─────────────────────────────────


class TestInstallAgentErrors:
    """Additional error-path tests for install_agent."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        cache.clear()
        yield
        cache.clear()

    async def test_install_non_imported_type_raises(self, mock_db):
        """Agent with correct lifecycle_status but wrong agent_type is rejected."""
        await mock_db.execute(
            """INSERT INTO agent_configs
               (id, name, slug, description, system_prompt, status_column,
                tools, project_id, owner, repo, created_by,
                created_at, lifecycle_status, agent_type)
               VALUES ('wrong-type-1', 'Test', 'test', 'desc', '', '', '[]',
                       ?, ?, ?, ?, datetime('now'), 'imported', 'custom')""",
            (PROJECT_ID, OWNER, REPO, GITHUB_USER_ID),
        )
        await mock_db.commit()

        service = AgentsService(mock_db)
        with pytest.raises(ValueError, match="Only imported agents"):
            await service.install_agent(
                project_id=PROJECT_ID,
                owner=OWNER,
                repo=REPO,
                agent_id="wrong-type-1",
                access_token=ACCESS_TOKEN,
            )

    async def test_install_no_raw_content_raises(self, mock_db):
        """Agent with no raw_source_content cannot be installed."""
        await mock_db.execute(
            """INSERT INTO agent_configs
               (id, name, slug, description, system_prompt, status_column,
                tools, project_id, owner, repo, created_by,
                created_at, lifecycle_status, agent_type,
                catalog_agent_id, raw_source_content)
               VALUES ('no-content-1', 'Test', 'test', 'desc', '', '', '[]',
                       ?, ?, ?, ?, datetime('now'), 'imported', 'imported',
                       'test-agent', '')""",
            (PROJECT_ID, OWNER, REPO, GITHUB_USER_ID),
        )
        await mock_db.commit()

        service = AgentsService(mock_db)
        with pytest.raises(ValueError, match="no raw source content"):
            await service.install_agent(
                project_id=PROJECT_ID,
                owner=OWNER,
                repo=REPO,
                agent_id="no-content-1",
                access_token=ACCESS_TOKEN,
            )


# ── _default_pr_body ─────────────────────────────────────────────────────


class TestDefaultPRBody:
    """Test the static _default_pr_body fallback."""

    def test_returns_formatted_markdown(self):
        from src.models.agent_creator import AgentPreview

        preview = AgentPreview(
            name="My Agent",
            slug="my-agent",
            description="Does things",
            system_prompt="Be helpful",
            status_column="",
            tools=["read"],
        )
        body = AgentsService._default_pr_body(preview, "my-agent")
        assert "## Agent: My Agent" in body
        assert "Does things" in body
        assert ".github/agents/my-agent.agent.md" in body
        assert ".github/prompts/my-agent.prompt.md" in body


# ── get_model_preferences alias ──────────────────────────────────────────


class TestGetModelPreferencesAlias:
    """Test that get_model_preferences delegates to get_agent_preferences."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        cache.clear()
        yield
        cache.clear()

    async def test_alias_returns_same_result(self, mock_db):
        await _insert_agent_row_with_prefs(
            mock_db,
            agent_id="alias-1",
            slug="test-agent",
            default_model_id="m-1",
            default_model_name="Model One",
        )
        service = AgentsService(mock_db)

        alias_result = await service.get_model_preferences(PROJECT_ID)
        direct_result = await service.get_agent_preferences(PROJECT_ID)

        assert alias_result == direct_result


# ── _list_repo_agents edge cases ─────────────────────────────────────────


class TestListRepoAgentsEdgeCases:
    """Edge cases for _list_repo_agents."""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        cache.clear()
        yield
        cache.clear()

    async def test_fetches_content_individually_when_not_in_tree(self, mock_db):
        """When tree entry has no content, fetches file individually."""
        service = AgentsService(mock_db)
        mock_github = AsyncMock()
        mock_github.get_directory_contents = AsyncMock(
            return_value=[{"name": "lazy.agent.md", "content": ""}]
        )
        mock_github.get_file_content = AsyncMock(
            return_value={"content": AGENT_FILE_CONTENT}
        )

        with patch("src.services.agents.service.github_projects_service", mock_github):
            agents, available = await service._list_repo_agents(
                owner=OWNER, repo=REPO, access_token=ACCESS_TOKEN
            )

        assert available is True
        assert len(agents) == 1
        assert agents[0].name == "Reviewer"
        mock_github.get_file_content.assert_awaited_once()

    async def test_skips_non_agent_md_files(self, mock_db):
        service = AgentsService(mock_db)
        mock_github = AsyncMock()
        mock_github.get_directory_contents = AsyncMock(
            return_value=[
                {"name": "readme.md", "content": "not an agent"},
                {"name": "valid.agent.md", "content": AGENT_FILE_CONTENT},
            ]
        )

        with patch("src.services.agents.service.github_projects_service", mock_github):
            agents, _available = await service._list_repo_agents(
                owner=OWNER, repo=REPO, access_token=ACCESS_TOKEN
            )

        assert len(agents) == 1
        assert agents[0].slug == "valid"

    async def test_icon_name_parsed_from_frontmatter(self, mock_db):
        content = "---\nname: Bot\nicon: rocket\n---\nPrompt."
        service = AgentsService(mock_db)
        mock_github = AsyncMock()
        mock_github.get_directory_contents = AsyncMock(
            return_value=[{"name": "bot.agent.md", "content": content}]
        )

        with patch("src.services.agents.service.github_projects_service", mock_github):
            agents, _ = await service._list_repo_agents(
                owner=OWNER, repo=REPO, access_token=ACCESS_TOKEN
            )

        assert agents[0].icon_name == "rocket"

    async def test_metadata_tool_ids_override_raw_tools(self, mock_db):
        content = (
            "---\nname: Bot\ntools:\n  - read\nmetadata:\n"
            "  solune-tool-ids: tool-1, tool-2\n---\nPrompt."
        )
        service = AgentsService(mock_db)
        mock_github = AsyncMock()
        mock_github.get_directory_contents = AsyncMock(
            return_value=[{"name": "bot.agent.md", "content": content}]
        )

        with patch("src.services.agents.service.github_projects_service", mock_github):
            agents, _ = await service._list_repo_agents(
                owner=OWNER, repo=REPO, access_token=ACCESS_TOKEN
            )

        assert agents[0].tools == ["tool-1", "tool-2"]

    async def test_individual_fetch_failure_yields_empty_content(self, mock_db):
        service = AgentsService(mock_db)
        mock_github = AsyncMock()
        mock_github.get_directory_contents = AsyncMock(
            return_value=[{"name": "fail.agent.md", "content": ""}]
        )
        mock_github.get_file_content = AsyncMock(side_effect=RuntimeError("not found"))

        with patch("src.services.agents.service.github_projects_service", mock_github):
            agents, available = await service._list_repo_agents(
                owner=OWNER, repo=REPO, access_token=ACCESS_TOKEN
            )

        assert available is True
        assert len(agents) == 1
        assert agents[0].system_prompt == ""
