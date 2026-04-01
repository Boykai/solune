import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from src.models.agents import Agent, AgentSource, AgentStatus
from src.services.agents.service import (
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
        assert any(f["path"].endswith(".agent.md") for f in files)
        assert any(f["path"].endswith(".prompt.md") for f in files)

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
