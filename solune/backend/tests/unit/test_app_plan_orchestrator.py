"""Unit tests for AppPlanOrchestrator — orchestration flow, status transitions, error handling."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.app_plan_orchestrator import AppPlanOrchestrator, OrchestrationResult
from src.services.plan_parser import PlanPhase

# ── Sample plan.md for testing ──────────────────────────────────────────

SAMPLE_PLAN_MD = """\
## Implementation Phases

### Phase 1 — Foundation

**Depends on**: Nothing

**Step 1.1**: Create schema

### Phase 2 — Backend

**Depends on**: Phase 1

**Step 2.1**: Implement services

### Phase 3 — Frontend

**Depends on**: Phase 1

**Step 3.1**: Create UI
"""


# ── Fixtures ────────────────────────────────────────────────────────────


def _make_orchestrator(
    *,
    github_service: AsyncMock | None = None,
    connection_manager: AsyncMock | None = None,
    db: AsyncMock | None = None,
) -> AppPlanOrchestrator:
    """Create an AppPlanOrchestrator with mocked dependencies."""
    if github_service is None:
        github_service = AsyncMock()
        github_service.create_issue = AsyncMock(
            side_effect=lambda **kw: {
                "number": 100 + hash(kw.get("title", "")) % 900,
                "node_id": f"node_{hash(kw.get('title', '')) % 1000}",
                "html_url": f"https://github.com/test/repo/issues/{100 + hash(kw.get('title', '')) % 900}",
            }
        )
        github_service.assign_copilot_to_issue = AsyncMock(return_value=True)
        github_service.check_agent_completion_comment = AsyncMock(return_value=True)
        github_service.get_file_content_from_ref = AsyncMock(return_value=SAMPLE_PLAN_MD)
        github_service.close_issue = AsyncMock()
        github_service.list_pull_requests_for_issue = AsyncMock(
            return_value=[{"head": {"ref": "test-branch"}}]
        )
        github_service.add_issue_to_project = AsyncMock(return_value="item-1")

    if connection_manager is None:
        connection_manager = AsyncMock()
        connection_manager.broadcast_to_project = AsyncMock()

    if db is None:
        db = AsyncMock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()

    return AppPlanOrchestrator(
        github_service=github_service,
        connection_manager=connection_manager,
        db=db,
    )


# ── Tests for orchestrate_app_creation() happy path ─────────────────────


class TestOrchestrateAppCreation:
    """Tests for the main orchestration flow."""

    @pytest.mark.asyncio
    async def test_happy_path_returns_success(self) -> None:
        orchestrator = _make_orchestrator()

        with patch.object(
            orchestrator,
            "_run_plan_agent",
            new_callable=AsyncMock,
            return_value="Plan summary text",
        ):
            result = await orchestrator.orchestrate_app_creation(
                app_name="test-app",
                description="A test application",
                project_id="proj-1",
                pipeline_id="pipe-1",
                access_token="token",
                owner="test-owner",
                repo="test-repo",
                orchestration_id="orch-1",
                poll_interval=0,
            )

        assert isinstance(result, OrchestrationResult)
        assert result.success is True
        assert result.status == "active"
        assert result.phase_count == 3
        assert result.phase_issue_numbers is not None
        assert len(result.phase_issue_numbers) == 3
        assert result.error_message is None

    @pytest.mark.asyncio
    async def test_status_transitions_in_order(self) -> None:
        """Verify status transitions: planning → speckit_running → ... → active."""
        connection_manager = AsyncMock()
        connection_manager.broadcast_to_project = AsyncMock()

        orchestrator = _make_orchestrator(connection_manager=connection_manager)

        with patch.object(
            orchestrator,
            "_run_plan_agent",
            new_callable=AsyncMock,
            return_value="Plan summary",
        ):
            await orchestrator.orchestrate_app_creation(
                app_name="test-app",
                description="Test",
                project_id="proj-1",
                pipeline_id="pipe-1",
                access_token="token",
                owner="owner",
                repo="repo",
                orchestration_id="orch-1",
                poll_interval=0,
            )

        # Extract status updates from broadcast calls
        statuses = []
        for call in connection_manager.broadcast_to_project.call_args_list:
            payload = call[0][1] if len(call[0]) > 1 else call[1].get("message", {})
            if isinstance(payload, dict) and payload.get("type") == "plan_status_update":
                statuses.append(payload["status"])

        expected_order = [
            "planning",
            "speckit_running",
            "parsing_phases",
            "creating_issues",
            "launching_pipelines",
            "active",
        ]
        assert statuses == expected_order

    @pytest.mark.asyncio
    async def test_phase_issues_created_with_correct_titles(self) -> None:
        github_service = AsyncMock()
        issue_counter = {"count": 0}

        async def mock_create_issue(**kwargs: object) -> dict:
            issue_counter["count"] += 1
            return {
                "number": issue_counter["count"],
                "node_id": f"node_{issue_counter['count']}",
                "html_url": f"https://github.com/test/repo/issues/{issue_counter['count']}",
            }

        github_service.create_issue = AsyncMock(side_effect=mock_create_issue)
        github_service.assign_copilot_to_issue = AsyncMock(return_value=True)
        github_service.check_agent_completion_comment = AsyncMock(return_value=True)
        github_service.get_file_content_from_ref = AsyncMock(return_value=SAMPLE_PLAN_MD)
        github_service.close_issue = AsyncMock()
        github_service.list_pull_requests_for_issue = AsyncMock(
            return_value=[{"head": {"ref": "test-branch"}}]
        )
        github_service.add_issue_to_project = AsyncMock(return_value="item-1")

        orchestrator = _make_orchestrator(github_service=github_service)

        with patch.object(
            orchestrator,
            "_run_plan_agent",
            new_callable=AsyncMock,
            return_value="Plan summary",
        ):
            await orchestrator.orchestrate_app_creation(
                app_name="my-app",
                description="My app",
                project_id="proj-1",
                pipeline_id="pipe-1",
                access_token="token",
                owner="owner",
                repo="repo",
                orchestration_id="orch-1",
                poll_interval=0,
            )

        # Check create_issue was called for planning issue + 3 phase issues = 4 times
        assert github_service.create_issue.call_count == 4

        # Check phase issue titles (calls 2, 3, 4 — after the planning issue)
        for i, call in enumerate(github_service.create_issue.call_args_list[1:], start=1):
            title = call.kwargs.get("title", "")
            assert "my-app" in title
            assert f"Phase {i}/3" in title


# ── Tests for error handling ────────────────────────────────────────────


class TestOrchestrationErrorHandling:
    """Tests for error handling in orchestrate_app_creation."""

    @pytest.mark.asyncio
    async def test_speckit_timeout_returns_failed(self) -> None:
        github_service = AsyncMock()
        github_service.create_issue = AsyncMock(
            return_value={"number": 1, "node_id": "n1", "html_url": "url"}
        )
        github_service.assign_copilot_to_issue = AsyncMock(return_value=True)
        github_service.check_agent_completion_comment = AsyncMock(return_value=False)
        github_service.close_issue = AsyncMock()
        github_service.list_pull_requests_for_issue = AsyncMock(return_value=[])

        orchestrator = _make_orchestrator(github_service=github_service)

        with patch.object(
            orchestrator,
            "_run_plan_agent",
            new_callable=AsyncMock,
            return_value="Plan summary",
        ):
            result = await orchestrator.orchestrate_app_creation(
                app_name="test-app",
                description="Test",
                project_id="proj-1",
                pipeline_id="pipe-1",
                access_token="token",
                owner="owner",
                repo="repo",
                orchestration_id="orch-1",
                speckit_timeout=0,
                poll_interval=0,
            )

        assert result.success is False
        assert result.status == "failed"
        assert result.error_message is not None
        assert "timed out" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_plan_md_not_found_returns_failed(self) -> None:
        github_service = AsyncMock()
        github_service.create_issue = AsyncMock(
            return_value={"number": 1, "node_id": "n1", "html_url": "url"}
        )
        github_service.assign_copilot_to_issue = AsyncMock(return_value=True)
        github_service.check_agent_completion_comment = AsyncMock(return_value=True)
        github_service.get_file_content_from_ref = AsyncMock(return_value=None)
        github_service.close_issue = AsyncMock()
        github_service.list_pull_requests_for_issue = AsyncMock(
            return_value=[{"head": {"ref": "branch"}}]
        )

        orchestrator = _make_orchestrator(github_service=github_service)

        with patch.object(
            orchestrator,
            "_run_plan_agent",
            new_callable=AsyncMock,
            return_value="Plan summary",
        ):
            result = await orchestrator.orchestrate_app_creation(
                app_name="test-app",
                description="Test",
                project_id="proj-1",
                pipeline_id="pipe-1",
                access_token="token",
                owner="owner",
                repo="repo",
                orchestration_id="orch-1",
                poll_interval=0,
            )

        assert result.success is False
        assert result.status == "failed"
        assert "not found" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_parse_failure_returns_failed(self) -> None:
        github_service = AsyncMock()
        github_service.create_issue = AsyncMock(
            return_value={"number": 1, "node_id": "n1", "html_url": "url"}
        )
        github_service.assign_copilot_to_issue = AsyncMock(return_value=True)
        github_service.check_agent_completion_comment = AsyncMock(return_value=True)
        github_service.get_file_content_from_ref = AsyncMock(return_value="No phases here")
        github_service.close_issue = AsyncMock()
        github_service.list_pull_requests_for_issue = AsyncMock(
            return_value=[{"head": {"ref": "branch"}}]
        )

        orchestrator = _make_orchestrator(github_service=github_service)

        with patch.object(
            orchestrator,
            "_run_plan_agent",
            new_callable=AsyncMock,
            return_value="Plan summary",
        ):
            result = await orchestrator.orchestrate_app_creation(
                app_name="test-app",
                description="Test",
                project_id="proj-1",
                pipeline_id="pipe-1",
                access_token="token",
                owner="owner",
                repo="repo",
                orchestration_id="orch-1",
                poll_interval=0,
            )

        assert result.success is False
        assert result.status == "failed"

    @pytest.mark.asyncio
    async def test_failed_status_broadcast_on_error(self) -> None:
        """Verify WebSocket broadcasts a failed status on error."""
        connection_manager = AsyncMock()
        connection_manager.broadcast_to_project = AsyncMock()

        github_service = AsyncMock()
        github_service.create_issue = AsyncMock(
            return_value={"number": 1, "node_id": "n1", "html_url": "url"}
        )
        github_service.assign_copilot_to_issue = AsyncMock(return_value=True)
        github_service.check_agent_completion_comment = AsyncMock(return_value=True)
        github_service.get_file_content_from_ref = AsyncMock(return_value="No phases")
        github_service.close_issue = AsyncMock()
        github_service.list_pull_requests_for_issue = AsyncMock(
            return_value=[{"head": {"ref": "branch"}}]
        )

        orchestrator = _make_orchestrator(
            github_service=github_service,
            connection_manager=connection_manager,
        )

        with patch.object(
            orchestrator,
            "_run_plan_agent",
            new_callable=AsyncMock,
            return_value="Plan summary",
        ):
            await orchestrator.orchestrate_app_creation(
                app_name="test-app",
                description="Test",
                project_id="proj-1",
                pipeline_id="pipe-1",
                access_token="token",
                owner="owner",
                repo="repo",
                orchestration_id="orch-1",
                poll_interval=0,
            )

        # Check that "failed" status was broadcast
        failed_broadcasts = [
            call
            for call in connection_manager.broadcast_to_project.call_args_list
            if isinstance(call[0][1], dict) and call[0][1].get("status") == "failed"
        ]
        assert len(failed_broadcasts) > 0


# ── Tests for _create_phase_issues ──────────────────────────────────────


class TestCreatePhaseIssues:
    """Tests for phase issue creation."""

    @pytest.mark.asyncio
    async def test_issues_added_to_project_board(self) -> None:
        github_service = AsyncMock()
        issue_counter = {"count": 0}

        async def mock_create_issue(**kwargs: object) -> dict:
            issue_counter["count"] += 1
            return {
                "number": issue_counter["count"],
                "node_id": f"node_{issue_counter['count']}",
                "html_url": f"url/{issue_counter['count']}",
            }

        github_service.create_issue = AsyncMock(side_effect=mock_create_issue)
        github_service.add_issue_to_project = AsyncMock(return_value="item-1")

        orchestrator = _make_orchestrator(github_service=github_service)

        phases = [
            PlanPhase(index=1, title="Foundation", description="Base setup"),
            PlanPhase(index=2, title="Backend", depends_on_phases=[1]),
        ]

        result = await orchestrator._create_phase_issues(
            phases=phases,
            app_name="test-app",
            description="Test app",
            project_id="proj-1",
            access_token="token",
            owner="owner",
            repo="repo",
        )

        assert len(result) == 2
        assert github_service.add_issue_to_project.call_count == 2

    @pytest.mark.asyncio
    async def test_issue_body_contains_phase_info(self) -> None:
        github_service = AsyncMock()
        github_service.create_issue = AsyncMock(
            return_value={"number": 1, "node_id": "n1", "html_url": "url"}
        )
        github_service.add_issue_to_project = AsyncMock(return_value="item-1")

        orchestrator = _make_orchestrator(github_service=github_service)

        phases = [PlanPhase(index=1, title="Only Phase", description="The description")]

        await orchestrator._create_phase_issues(
            phases=phases,
            app_name="my-app",
            description="My app desc",
            project_id="proj-1",
            access_token="token",
            owner="owner",
            repo="repo",
        )

        call_kwargs = github_service.create_issue.call_args.kwargs
        assert "Phase 1/1" in call_kwargs["title"]
        assert "my-app" in call_kwargs["title"]
        assert "Phase 1 of 1" in call_kwargs["body"]
        assert "The description" in call_kwargs["body"]


# ── Tests for _launch_phase_pipelines ───────────────────────────────────


class TestLaunchPhasePipelines:
    """Tests for wave-based pipeline launching."""

    @pytest.mark.asyncio
    async def test_launch_called_for_each_phase(self) -> None:
        orchestrator = _make_orchestrator()

        phases = [
            PlanPhase(index=1, title="A"),
            PlanPhase(index=2, title="B", depends_on_phases=[1]),
        ]

        with patch("src.api.pipelines.execute_pipeline_launch") as mock_launch:
            mock_launch.return_value = MagicMock(success=True)

            await orchestrator._launch_phase_pipelines(
                phases=phases,
                phase_issue_numbers=[10, 20],
                project_id="proj-1",
                pipeline_id="pipe-1",
                access_token="token",
            )

            assert mock_launch.call_count == 2

    @pytest.mark.asyncio
    async def test_wave2_phases_have_prerequisites(self) -> None:
        orchestrator = _make_orchestrator()

        phases = [
            PlanPhase(index=1, title="A"),
            PlanPhase(index=2, title="B", depends_on_phases=[1]),
        ]

        with patch("src.api.pipelines.execute_pipeline_launch") as mock_launch:
            mock_launch.return_value = MagicMock(success=True)

            await orchestrator._launch_phase_pipelines(
                phases=phases,
                phase_issue_numbers=[10, 20],
                project_id="proj-1",
                pipeline_id="pipe-1",
                access_token="token",
            )

            # Second call (Phase 2) should have prerequisite_issues
            second_call = mock_launch.call_args_list[1]
            assert second_call.kwargs.get("auto_merge") is True
            prereqs = second_call.kwargs.get("prerequisite_issues")
            assert prereqs == [10]  # Phase 2 depends on Phase 1 (issue #10)

    @pytest.mark.asyncio
    async def test_wave1_phases_have_no_prerequisites(self) -> None:
        orchestrator = _make_orchestrator()

        phases = [
            PlanPhase(index=1, title="A"),
            PlanPhase(index=2, title="B", depends_on_phases=[1]),
        ]

        with patch("src.api.pipelines.execute_pipeline_launch") as mock_launch:
            mock_launch.return_value = MagicMock(success=True)

            await orchestrator._launch_phase_pipelines(
                phases=phases,
                phase_issue_numbers=[10, 20],
                project_id="proj-1",
                pipeline_id="pipe-1",
                access_token="token",
            )

            # First call (Phase 1) should have no prerequisites
            first_call = mock_launch.call_args_list[0]
            assert first_call.kwargs.get("auto_merge") is True
            prereqs = first_call.kwargs.get("prerequisite_issues")
            assert prereqs is None  # No deps means None

    @pytest.mark.asyncio
    async def test_three_wave_pipeline_launch(self) -> None:
        """3-wave launch: wave 1 (no deps), wave 2 (depends on 1), wave 3 (depends on 2,3)."""
        orchestrator = _make_orchestrator()

        phases = [
            PlanPhase(index=1, title="A"),
            PlanPhase(index=2, title="B", depends_on_phases=[1]),
            PlanPhase(index=3, title="C", depends_on_phases=[1]),
            PlanPhase(index=4, title="D", depends_on_phases=[2, 3]),
        ]

        with patch("src.api.pipelines.execute_pipeline_launch") as mock_launch:
            mock_launch.return_value = MagicMock(success=True)

            await orchestrator._launch_phase_pipelines(
                phases=phases,
                phase_issue_numbers=[10, 20, 30, 40],
                project_id="proj-1",
                pipeline_id="pipe-1",
                access_token="token",
            )

            assert mock_launch.call_count == 4

            # Phase 1 (wave 1): no prereqs
            assert mock_launch.call_args_list[0].kwargs.get("prerequisite_issues") is None
            # Phase 2 (wave 2): depends on Phase 1 → issue #10
            assert mock_launch.call_args_list[1].kwargs.get("prerequisite_issues") == [10]
            # Phase 3 (wave 2): depends on Phase 1 → issue #10
            assert mock_launch.call_args_list[2].kwargs.get("prerequisite_issues") == [10]
            # Phase 4 (wave 3): depends on Phase 2, 3 → issues #20, #30
            prereqs_4 = mock_launch.call_args_list[3].kwargs.get("prerequisite_issues")
            assert sorted(prereqs_4) == [20, 30]

    @pytest.mark.asyncio
    async def test_pipeline_launch_failure_does_not_abort_other_phases(self) -> None:
        """If one phase pipeline launch fails, other phases still launch."""
        orchestrator = _make_orchestrator()

        phases = [
            PlanPhase(index=1, title="A"),
            PlanPhase(index=2, title="B"),
        ]

        call_count = {"n": 0}

        async def _failing_then_success(**kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise RuntimeError("launch failed")
            return MagicMock(success=True)

        with patch("src.api.pipelines.execute_pipeline_launch", side_effect=_failing_then_success):
            # Should not raise — error is caught internally
            await orchestrator._launch_phase_pipelines(
                phases=phases,
                phase_issue_numbers=[10, 20],
                project_id="proj-1",
                pipeline_id="pipe-1",
                access_token="token",
            )

        assert call_count["n"] == 2


# ── Tests for _discover_pr_branch ───────────────────────────────────────


class TestDiscoverPrBranch:
    """Tests for PR branch discovery fallback behavior."""

    @pytest.mark.asyncio
    async def test_returns_branch_from_pr(self) -> None:
        github_service = AsyncMock()
        github_service.list_pull_requests_for_issue = AsyncMock(
            return_value=[{"head": {"ref": "copilot/feature-branch"}}]
        )
        orchestrator = _make_orchestrator(github_service=github_service)

        branch = await orchestrator._discover_pr_branch(
            access_token="token",
            owner="owner",
            repo="repo",
            issue_number=1,
        )
        assert branch == "copilot/feature-branch"

    @pytest.mark.asyncio
    async def test_falls_back_to_main_when_no_prs(self) -> None:
        github_service = AsyncMock()
        github_service.list_pull_requests_for_issue = AsyncMock(return_value=[])
        orchestrator = _make_orchestrator(github_service=github_service)

        branch = await orchestrator._discover_pr_branch(
            access_token="token",
            owner="owner",
            repo="repo",
            issue_number=1,
        )
        assert branch == "main"

    @pytest.mark.asyncio
    async def test_falls_back_to_main_on_exception(self) -> None:
        github_service = AsyncMock()
        github_service.list_pull_requests_for_issue = AsyncMock(
            side_effect=RuntimeError("API error")
        )
        orchestrator = _make_orchestrator(github_service=github_service)

        branch = await orchestrator._discover_pr_branch(
            access_token="token",
            owner="owner",
            repo="repo",
            issue_number=1,
        )
        assert branch == "main"


# ── Tests for _save_orchestration ───────────────────────────────────────


class TestSaveOrchestration:
    """Tests for DB persistence of orchestration state."""

    @pytest.mark.asyncio
    async def test_save_calls_db_execute_and_commit(self) -> None:
        db = AsyncMock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()
        orchestrator = _make_orchestrator(db=db)

        await orchestrator._save_orchestration(
            "orch-1",
            app_name="test-app",
            project_id="proj-1",
            status="active",
            phase_count=3,
            phase_issue_numbers=[10, 20, 30],
        )

        db.execute.assert_called_once()
        db.commit.assert_called_once()
        # Verify the SQL includes the orchestration_id
        sql = db.execute.call_args[0][0]
        assert "app_plan_orchestrations" in sql

    @pytest.mark.asyncio
    async def test_save_serializes_phase_issue_numbers_as_json(self) -> None:
        db = AsyncMock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()
        orchestrator = _make_orchestrator(db=db)

        await orchestrator._save_orchestration(
            "orch-1",
            app_name="test-app",
            project_id="proj-1",
            status="active",
            phase_count=2,
            phase_issue_numbers=[10, 20],
        )

        params = db.execute.call_args[0][1]
        # Find the JSON-serialized phase_issue_numbers in the params tuple
        json_param = [p for p in params if isinstance(p, str) and p.startswith("[")]
        assert len(json_param) == 1
        assert json.loads(json_param[0]) == [10, 20]

    @pytest.mark.asyncio
    async def test_save_skips_when_no_db(self) -> None:
        """When db is None, _save_orchestration should not raise."""
        orchestrator = _make_orchestrator(db=None)
        # Should not raise
        await orchestrator._save_orchestration(
            "orch-1",
            app_name="test-app",
            project_id="proj-1",
            status="active",
        )

    @pytest.mark.asyncio
    async def test_save_handles_db_error_gracefully(self) -> None:
        """DB errors during save should be swallowed (logged, not raised)."""
        db = AsyncMock()
        db.execute = AsyncMock(side_effect=RuntimeError("DB write failed"))
        orchestrator = _make_orchestrator(db=db)

        # Should not raise
        await orchestrator._save_orchestration(
            "orch-1",
            app_name="test-app",
            project_id="proj-1",
            status="active",
        )


# ── Tests for plan agent failure ────────────────────────────────────────


class TestPlanAgentFailure:
    """Tests for _run_plan_agent failure propagation."""

    @pytest.mark.asyncio
    async def test_plan_agent_exception_returns_failed(self) -> None:
        """If the chat plan agent raises, orchestration returns failed."""
        orchestrator = _make_orchestrator()

        with patch.object(
            orchestrator,
            "_run_plan_agent",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Plan agent crashed"),
        ):
            result = await orchestrator.orchestrate_app_creation(
                app_name="test-app",
                description="Test",
                project_id="proj-1",
                pipeline_id="pipe-1",
                access_token="token",
                owner="owner",
                repo="repo",
                orchestration_id="orch-1",
                poll_interval=0,
            )

        assert result.success is False
        assert result.status == "failed"
        assert (
            "plan agent" in result.error_message.lower()
            or "crashed" in result.error_message.lower()
        )


# ── Tests for OrchestrationResult ───────────────────────────────────────


class TestOrchestrationResult:
    """Tests for the OrchestrationResult dataclass."""

    def test_defaults(self) -> None:
        result = OrchestrationResult(
            success=True,
            orchestration_id="orch-1",
            status="active",
        )
        assert result.phase_count == 0
        assert result.phase_issue_numbers is None
        assert result.error_message is None

    def test_failed_result(self) -> None:
        result = OrchestrationResult(
            success=False,
            orchestration_id="orch-2",
            status="failed",
            error_message="Something went wrong",
        )
        assert result.success is False
        assert result.error_message == "Something went wrong"
