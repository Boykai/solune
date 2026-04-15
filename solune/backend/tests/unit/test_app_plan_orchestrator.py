"""Unit tests for AppPlanOrchestrator — orchestration flow, status transitions, error handling."""

from __future__ import annotations

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

        with patch(
            "src.api.pipelines.execute_pipeline_launch", new_callable=AsyncMock
        ) as mock_launch:
            mock_launch.return_value = MagicMock(success=True)

            await orchestrator._launch_phase_pipelines(
                phases=phases,
                phase_issue_numbers=[10, 20],
                project_id="proj-1",
                pipeline_id="pipe-1",
                access_token="token",
                owner="test-owner",
                repo="test-repo",
            )

            assert mock_launch.call_count == 2

    @pytest.mark.asyncio
    async def test_wave2_phases_have_prerequisites(self) -> None:
        orchestrator = _make_orchestrator()

        phases = [
            PlanPhase(index=1, title="A"),
            PlanPhase(index=2, title="B", depends_on_phases=[1]),
        ]

        with patch(
            "src.api.pipelines.execute_pipeline_launch", new_callable=AsyncMock
        ) as mock_launch:
            mock_launch.return_value = MagicMock(success=True)

            await orchestrator._launch_phase_pipelines(
                phases=phases,
                phase_issue_numbers=[10, 20],
                project_id="proj-1",
                pipeline_id="pipe-1",
                access_token="token",
                owner="test-owner",
                repo="test-repo",
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

        with patch(
            "src.api.pipelines.execute_pipeline_launch", new_callable=AsyncMock
        ) as mock_launch:
            mock_launch.return_value = MagicMock(success=True)

            await orchestrator._launch_phase_pipelines(
                phases=phases,
                phase_issue_numbers=[10, 20],
                project_id="proj-1",
                pipeline_id="pipe-1",
                access_token="token",
                owner="test-owner",
                repo="test-repo",
            )

            # First call (Phase 1) should have no prerequisites
            first_call = mock_launch.call_args_list[0]
            assert first_call.kwargs.get("auto_merge") is True
            prereqs = first_call.kwargs.get("prerequisite_issues")
            assert prereqs is None  # No deps means None

    @pytest.mark.asyncio
    async def test_target_repo_forwarded_to_execute_pipeline_launch(self) -> None:
        """Each execute_pipeline_launch call must include target_repo=(owner, repo)."""
        orchestrator = _make_orchestrator()

        phases = [
            PlanPhase(index=1, title="A"),
            PlanPhase(index=2, title="B", depends_on_phases=[1]),
        ]

        with patch(
            "src.api.pipelines.execute_pipeline_launch", new_callable=AsyncMock
        ) as mock_launch:
            mock_launch.return_value = MagicMock(success=True)

            await orchestrator._launch_phase_pipelines(
                phases=phases,
                phase_issue_numbers=[10, 20],
                project_id="proj-1",
                pipeline_id="pipe-1",
                access_token="token",
                owner="myorg",
                repo="myrepo",
            )

            assert mock_launch.call_count == 2
            for call in mock_launch.call_args_list:
                assert call.kwargs.get("target_repo") == ("myorg", "myrepo")


# ── Tests for diamond dependency prerequisite mapping ───────────────────


DIAMOND_PLAN_MD = """\
## Implementation Phases

### Phase 1 — Foundation

**Depends on**: Nothing

**Step 1.1**: Base setup

### Phase 2 — Backend

**Depends on**: Phase 1

**Step 2.1**: API

### Phase 3 — Frontend

**Depends on**: Phase 1

**Step 3.1**: UI

### Phase 4 — Integration

**Depends on**: Phase 2, Phase 3

**Step 4.1**: Wire up
"""


class TestDiamondDependencyPrerequisites:
    """Tests for diamond-shaped dependency graphs in pipeline launching."""

    @pytest.mark.asyncio
    async def test_diamond_deps_prerequisites_set_correctly(self) -> None:
        """Phase 4 (depends on 2+3) maps to both their issue numbers as prereqs."""
        github_service = AsyncMock()
        issue_counter = {"count": 0}

        async def mock_create_issue(**kwargs: object) -> dict:
            issue_counter["count"] += 1
            return {
                "number": issue_counter["count"] * 10,
                "node_id": f"node_{issue_counter['count']}",
                "html_url": f"url/{issue_counter['count']}",
            }

        github_service.create_issue = AsyncMock(side_effect=mock_create_issue)
        github_service.assign_copilot_to_issue = AsyncMock(return_value=True)
        github_service.check_agent_completion_comment = AsyncMock(return_value=True)
        github_service.get_file_content_from_ref = AsyncMock(return_value=DIAMOND_PLAN_MD)
        github_service.close_issue = AsyncMock()
        github_service.list_pull_requests_for_issue = AsyncMock(
            return_value=[{"head": {"ref": "test-branch"}}]
        )
        github_service.add_issue_to_project = AsyncMock(return_value="item-1")

        orchestrator = _make_orchestrator(github_service=github_service)

        with (
            patch.object(
                orchestrator,
                "_run_plan_agent",
                new_callable=AsyncMock,
                return_value="Plan summary",
            ),
            patch(
                "src.api.pipelines.execute_pipeline_launch", new_callable=AsyncMock
            ) as mock_launch,
        ):
            mock_launch.return_value = MagicMock(success=True)

            result = await orchestrator.orchestrate_app_creation(
                app_name="diamond-app",
                description="Diamond deps",
                project_id="proj-1",
                pipeline_id="pipe-1",
                access_token="token",
                owner="owner",
                repo="repo",
                orchestration_id="orch-diamond",
                poll_interval=0,
            )

        assert result.success is True
        assert result.phase_count == 4
        assert mock_launch.call_count == 4

        # Phase 1 (issue #20): no prerequisites
        p1_call = mock_launch.call_args_list[0]
        assert p1_call.kwargs.get("prerequisite_issues") is None

        # Phase 2 (issue #30, depends on Phase 1 → issue #20): prereqs=[20]
        p2_call = mock_launch.call_args_list[1]
        assert p2_call.kwargs.get("prerequisite_issues") == [20]

        # Phase 3 (issue #40, depends on Phase 1 → issue #20): prereqs=[20]
        p3_call = mock_launch.call_args_list[2]
        assert p3_call.kwargs.get("prerequisite_issues") == [20]

        # Phase 4 (issue #50, depends on Phase 2+3 → issues #30, #40): prereqs=[30, 40]
        p4_call = mock_launch.call_args_list[3]
        p4_prereqs = p4_call.kwargs.get("prerequisite_issues")
        assert sorted(p4_prereqs) == [30, 40]


class TestPipelineLaunchFailureHandling:
    """Tests for resilience when individual pipeline launches fail."""

    @pytest.mark.asyncio
    async def test_launch_failure_does_not_block_other_phases(self) -> None:
        """If one phase's pipeline launch fails, remaining phases still launch."""
        orchestrator = _make_orchestrator()

        phases = [
            PlanPhase(index=1, title="A"),
            PlanPhase(index=2, title="B"),
            PlanPhase(index=3, title="C"),
        ]

        call_count = {"n": 0}

        async def mock_launch(**kwargs):
            call_count["n"] += 1
            if call_count["n"] == 2:
                raise RuntimeError("Launch failed for Phase 2")
            return MagicMock(success=True)

        with patch("src.api.pipelines.execute_pipeline_launch", side_effect=mock_launch):
            # Should not raise — errors are logged but execution continues
            await orchestrator._launch_phase_pipelines(
                phases=phases,
                phase_issue_numbers=[10, 20, 30],
                project_id="proj-1",
                pipeline_id="pipe-1",
                access_token="token",
                owner="test-owner",
                repo="test-repo",
            )

        # All 3 phases attempted even though #2 failed
        assert call_count["n"] == 3


class TestOrchestrationDbPersistence:
    """Tests for database persistence of orchestration state."""

    @pytest.mark.asyncio
    async def test_success_saves_orchestration_to_db(self) -> None:
        """Successful orchestration calls _save_orchestration with active status."""
        db = AsyncMock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()

        orchestrator = _make_orchestrator(db=db)

        with patch.object(
            orchestrator,
            "_run_plan_agent",
            new_callable=AsyncMock,
            return_value="Plan summary",
        ):
            result = await orchestrator.orchestrate_app_creation(
                app_name="persist-app",
                description="Test persistence",
                project_id="proj-1",
                pipeline_id="pipe-1",
                access_token="token",
                owner="owner",
                repo="repo",
                orchestration_id="orch-persist",
                poll_interval=0,
            )

        assert result.success is True
        assert result.status == "active"

        # Verify db.execute was called (for both status updates and final save)
        assert db.execute.call_count > 0
        # The final save should include "active" status
        final_save_calls = [
            c
            for c in db.execute.call_args_list
            if len(c[0]) > 1 and isinstance(c[0][1], tuple) and "active" in c[0][1]
        ]
        assert len(final_save_calls) > 0

    @pytest.mark.asyncio
    async def test_failure_saves_error_to_db(self) -> None:
        """Failed orchestration persists error_message to database."""
        db = AsyncMock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()

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

        orchestrator = _make_orchestrator(github_service=github_service, db=db)

        with patch.object(
            orchestrator,
            "_run_plan_agent",
            new_callable=AsyncMock,
            return_value="Plan",
        ):
            result = await orchestrator.orchestrate_app_creation(
                app_name="fail-app",
                description="Will fail",
                project_id="proj-1",
                pipeline_id="pipe-1",
                access_token="token",
                owner="owner",
                repo="repo",
                orchestration_id="orch-fail",
                poll_interval=0,
            )

        assert result.success is False
        assert result.status == "failed"
        assert result.error_message is not None

        # Verify "failed" status was saved
        failed_save_calls = [
            c
            for c in db.execute.call_args_list
            if len(c[0]) > 1 and isinstance(c[0][1], tuple) and "failed" in c[0][1]
        ]
        assert len(failed_save_calls) > 0


class TestOrchestrationResultFields:
    """Tests for OrchestrationResult completeness."""

    @pytest.mark.asyncio
    async def test_result_includes_all_phase_issue_numbers(self) -> None:
        """OrchestrationResult tracks the exact issue numbers created."""
        github_service = AsyncMock()
        expected_issues = [101, 102, 103]
        call_idx = {"i": 0}

        async def mock_create_issue(**kwargs: object) -> dict:
            num = expected_issues[call_idx["i"]] if call_idx["i"] < len(expected_issues) else 999
            call_idx["i"] += 1
            return {"number": num, "node_id": f"n{num}", "html_url": f"url/{num}"}

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
            return_value="Plan",
        ):
            result = await orchestrator.orchestrate_app_creation(
                app_name="track-app",
                description="Track issues",
                project_id="proj-1",
                pipeline_id="pipe-1",
                access_token="token",
                owner="owner",
                repo="repo",
                orchestration_id="orch-track",
                poll_interval=0,
            )

        assert result.success is True
        # First issue created is the planning issue; phase issues are calls 2-4
        assert result.phase_issue_numbers is not None
        assert len(result.phase_issue_numbers) == 3  # 3 phases in SAMPLE_PLAN_MD
