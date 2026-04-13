from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

from src.services.fleet_dispatch import FleetDispatchService


class TestFleetDispatchService:
    def test_eligibility_excludes_human_and_copilot_review(self) -> None:
        assert FleetDispatchService.is_fleet_eligible("speckit.specify") is True
        assert FleetDispatchService.is_fleet_eligible("tester") is True
        assert FleetDispatchService.is_fleet_eligible("human") is False
        assert FleetDispatchService.is_fleet_eligible("copilot-review") is False

    def test_build_dispatch_payload_uses_assignment_overrides(self) -> None:
        service = FleetDispatchService()
        payload = service.build_dispatch_payload(
            issue_data={"title": "Add caching", "body": "Use Redis.", "comments": []},
            agent_slug="custom.agent",
            owner="Boykai",
            repo="solune",
            base_ref="copilot/test-branch",
            parent_issue_number=1555,
            assignment_config={
                "customAgent": "repo-special-agent",
                "instructionTemplate": "solune/scripts/pipelines/templates/generic.md",
            },
            existing_pr={"head_ref": "copilot/test-branch"},
        )

        assert payload.custom_agent == "repo-special-agent"
        assert payload.template_path.name == "generic.md"
        assert "## Issue Title\nAdd caching" in payload.custom_instructions
        assert "## Issue Description\nUse Redis." in payload.custom_instructions
        assert (
            "commit all changes to the PR branch (`copilot/test-branch`)"
            in payload.custom_instructions
        )

    def test_unknown_agent_falls_back_to_generic_template(self) -> None:
        service = FleetDispatchService()
        payload = service.build_dispatch_payload(
            issue_data={
                "title": "Unknown agent task",
                "body": "Do the work.",
                "comments": [
                    {
                        "author": "alice",
                        "body": "Please handle edge cases.",
                        "created_at": "2026-04-12T10:00:00Z",
                    }
                ],
            },
            agent_slug="repo.custom-agent",
            owner="Boykai",
            repo="solune",
            base_ref="main",
            parent_issue_number=1555,
        )

        assert payload.custom_agent == "repo.custom-agent"
        assert payload.template_path.name == "generic.md"
        assert "## Comments and Discussion" in payload.custom_instructions
        assert "Please handle edge cases." in payload.custom_instructions

    @pytest.mark.asyncio
    async def test_resolve_task_id_prefers_latest_matching_task(self) -> None:
        service = FleetDispatchService()
        github = Mock()
        github.list_agent_tasks = AsyncMock(
            return_value=[
                {
                    "id": "task-1",
                    "name": "[speckit.specify] Parent Title",
                    "createdAt": "2026-04-12T09:00:00Z",
                },
                {
                    "id": "task-2",
                    "name": "[speckit.specify] Parent Title",
                    "createdAt": "2026-04-12T10:00:00Z",
                },
            ]
        )

        task_id = await service.resolve_task_id(
            github_service=github,
            access_token="tok",
            owner="Boykai",
            repo="solune",
            agent_slug="speckit.specify",
            issue_title="Parent Title",
        )

        assert task_id == "task-2"

    @pytest.mark.asyncio
    async def test_resolve_task_id_ignores_slug_only_match_when_title_is_available(self) -> None:
        service = FleetDispatchService()
        github = Mock()
        github.list_agent_tasks = AsyncMock(
            return_value=[
                {
                    "id": "task-1",
                    "name": "[speckit.specify] Parent Title",
                    "createdAt": "2026-04-12T09:00:00Z",
                },
                {
                    "id": "task-2",
                    "name": "[speckit.specify] Different Title",
                    "createdAt": "2026-04-12T10:00:00Z",
                },
            ]
        )

        task_id = await service.resolve_task_id(
            github_service=github,
            access_token="tok",
            owner="Boykai",
            repo="solune",
            agent_slug="speckit.specify",
            issue_title="Parent Title",
        )

        assert task_id == "task-1"

    @pytest.mark.asyncio
    async def test_resolve_task_id_falls_back_to_slug_when_title_is_empty(self) -> None:
        service = FleetDispatchService()
        github = Mock()
        github.list_agent_tasks = AsyncMock(
            return_value=[
                {
                    "id": "task-1",
                    "name": "[speckit.specify] Parent Title",
                    "createdAt": "2026-04-12T09:00:00Z",
                },
                {
                    "id": "task-2",
                    "name": "[speckit.specify] Different Title",
                    "createdAt": "2026-04-12T10:00:00Z",
                },
            ]
        )

        task_id = await service.resolve_task_id(
            github_service=github,
            access_token="tok",
            owner="Boykai",
            repo="solune",
            agent_slug="speckit.specify",
            issue_title="",
        )

        assert task_id == "task-2"

    @pytest.mark.asyncio
    async def test_get_task_status_normalizes_state(self) -> None:
        service = FleetDispatchService()
        github = Mock()
        github.get_agent_task = AsyncMock(return_value={"id": "task-1", "state": "SUCCEEDED"})

        status = await service.get_task_status(
            github_service=github,
            access_token="tok",
            owner="Boykai",
            repo="solune",
            task_id="task-1",
        )

        assert status == "completed"

    def test_copilot_slug_is_fleet_eligible(self) -> None:
        assert FleetDispatchService.is_fleet_eligible("copilot") is True

    def test_resolve_custom_agent_returns_empty_for_copilot(self) -> None:
        service = FleetDispatchService()
        assert service.resolve_custom_agent("copilot") == ""

    def test_resolve_template_path_returns_none_for_copilot(self) -> None:
        service = FleetDispatchService()
        assert service.resolve_template_path("copilot") is None

    def test_build_dispatch_payload_copilot_uses_issue_body(self) -> None:
        service = FleetDispatchService()
        issue_body = "Apply all Dependabot updates that pass tests."
        payload = service.build_dispatch_payload(
            issue_data={"title": "Dependabot Updates", "body": issue_body, "comments": []},
            agent_slug="copilot",
            owner="Boykai",
            repo="solune",
            base_ref="main",
            parent_issue_number=1708,
        )

        assert payload.custom_agent == ""
        assert payload.template_path is None
        assert payload.custom_instructions == issue_body
