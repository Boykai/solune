"""Unit tests for plan_issue_service.create_plan_issues().

Covers:
- Happy path: parent issue + sub-issues created successfully
- Partial failure: some sub-issues fail
- Dependency references in sub-issue bodies
- Plan status transitions (completed / failed)
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.models.plan import Plan, PlanStep
from src.services.chat_store import get_plan, save_plan
from src.services.plan_issue_service import create_plan_issues

# =============================================================================
# Helpers
# =============================================================================


def _make_plan_dict(
    plan_id: str = "plan-1",
    session_id: str = "sess-1",
    title: str = "Test Plan",
    summary: str = "Plan summary",
    steps: list[dict] | None = None,
) -> dict:
    """Build a plan dict matching the shape returned by chat_store.get_plan()."""
    return {
        "plan_id": plan_id,
        "session_id": session_id,
        "title": title,
        "summary": summary,
        "status": "approved",
        "project_id": "proj-1",
        "project_name": "My Project",
        "repo_owner": "octocat",
        "repo_name": "hello-world",
        "parent_issue_number": None,
        "parent_issue_url": None,
        "steps": steps or [],
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }


def _make_step_dict(
    step_id: str = "step-1",
    position: int = 0,
    title: str = "Step",
    description: str = "Do something",
    dependencies: list[str] | None = None,
) -> dict:
    return {
        "step_id": step_id,
        "position": position,
        "title": title,
        "description": description,
        "dependencies": dependencies or [],
        "issue_number": None,
        "issue_url": None,
    }


# =============================================================================
# Tests
# =============================================================================


class TestCreatePlanIssues:
    """create_plan_issues GitHub issue creation."""

    @pytest.mark.anyio
    async def test_creates_parent_and_sub_issues(self, mock_db):
        """Happy path: parent + 2 sub-issues all created successfully."""
        # Seed the plan in DB so update calls succeed
        plan_model = Plan(
            plan_id="plan-1",
            session_id="sess-1",
            title="Test Plan",
            summary="Plan summary",
            status="approved",
            project_id="proj-1",
            project_name="My Project",
            repo_owner="octocat",
            repo_name="hello-world",
            steps=[
                PlanStep(
                    step_id="s-1", plan_id="plan-1", position=0, title="Step 1", description="D1"
                ),
                PlanStep(
                    step_id="s-2",
                    plan_id="plan-1",
                    position=1,
                    title="Step 2",
                    description="D2",
                    dependencies=["s-1"],
                ),
            ],
        )
        await save_plan(mock_db, plan_model)

        plan_dict = _make_plan_dict(
            steps=[
                _make_step_dict(step_id="s-1", position=0, title="Step 1", description="D1"),
                _make_step_dict(
                    step_id="s-2",
                    position=1,
                    title="Step 2",
                    description="D2",
                    dependencies=["s-1"],
                ),
            ]
        )

        issue_counter = {"n": 99}

        async def mock_create_issue(**kwargs):
            issue_counter["n"] += 1
            return {
                "number": issue_counter["n"],
                "html_url": f"https://github.com/octocat/hello-world/issues/{issue_counter['n']}",
            }

        mock_service = AsyncMock()
        mock_service.create_issue = AsyncMock(side_effect=mock_create_issue)

        with patch(
            "src.services.github_projects.service.GitHubProjectsService",
            return_value=mock_service,
        ):
            result = await create_plan_issues(
                access_token="token",
                plan=plan_dict,
                owner="octocat",
                repo="hello-world",
                db=mock_db,
            )

        # Parent issue created first
        assert result["parent_issue_number"] == 100
        assert "issues/100" in result["parent_issue_url"]

        # 2 sub-issues created
        assert len(result["created_issues"]) == 2
        assert result["created_issues"][0]["issue_number"] == 101
        assert result["created_issues"][1]["issue_number"] == 102
        assert result["failed_steps"] == []

        # Plan should be marked as completed
        stored = await get_plan(mock_db, "plan-1")
        assert stored is not None
        assert stored["status"] == "completed"
        assert stored["parent_issue_number"] == 100

    @pytest.mark.anyio
    async def test_partial_failure_marks_plan_as_failed(self, mock_db):
        """When one sub-issue fails, plan status should be 'failed'."""
        plan_model = Plan(
            plan_id="plan-2",
            session_id="sess-1",
            title="Plan",
            summary="S",
            status="approved",
            project_id="proj-1",
            project_name="P",
            repo_owner="o",
            repo_name="r",
            steps=[
                PlanStep(step_id="s-a", plan_id="plan-2", position=0, title="A", description="DA"),
                PlanStep(step_id="s-b", plan_id="plan-2", position=1, title="B", description="DB"),
            ],
        )
        await save_plan(mock_db, plan_model)

        plan_dict = _make_plan_dict(
            plan_id="plan-2",
            title="Plan",
            summary="S",
            steps=[
                _make_step_dict(step_id="s-a", position=0, title="A", description="DA"),
                _make_step_dict(step_id="s-b", position=1, title="B", description="DB"),
            ],
        )

        call_count = {"n": 0}

        async def mock_create_issue(**kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                # Parent issue succeeds
                return {"number": 50, "html_url": "https://github.com/o/r/issues/50"}
            if call_count["n"] == 2:
                # First sub-issue succeeds
                return {"number": 51, "html_url": "https://github.com/o/r/issues/51"}
            # Second sub-issue fails
            raise RuntimeError("GitHub API error")

        mock_service = AsyncMock()
        mock_service.create_issue = AsyncMock(side_effect=mock_create_issue)

        with patch(
            "src.services.github_projects.service.GitHubProjectsService",
            return_value=mock_service,
        ):
            result = await create_plan_issues(
                access_token="token",
                plan=plan_dict,
                owner="o",
                repo="r",
                db=mock_db,
            )

        assert len(result["created_issues"]) == 1
        assert len(result["failed_steps"]) == 1
        assert result["failed_steps"][0]["step_id"] == "s-b"

        stored = await get_plan(mock_db, "plan-2")
        assert stored is not None
        assert stored["status"] == "failed"

    @pytest.mark.anyio
    async def test_dependency_references_in_sub_issue_body(self, mock_db):
        """Sub-issue body should reference dependency issue numbers."""
        plan_model = Plan(
            plan_id="plan-3",
            session_id="sess-1",
            title="Plan",
            summary="S",
            status="approved",
            project_id="proj-1",
            project_name="P",
            repo_owner="o",
            repo_name="r",
            steps=[
                PlanStep(
                    step_id="dep-1", plan_id="plan-3", position=0, title="Base", description="D"
                ),
                PlanStep(
                    step_id="dep-2",
                    plan_id="plan-3",
                    position=1,
                    title="Depends",
                    description="D",
                    dependencies=["dep-1"],
                ),
            ],
        )
        await save_plan(mock_db, plan_model)

        plan_dict = _make_plan_dict(
            plan_id="plan-3",
            title="Plan",
            summary="S",
            steps=[
                _make_step_dict(step_id="dep-1", position=0, title="Base", description="Base desc"),
                _make_step_dict(
                    step_id="dep-2",
                    position=1,
                    title="Depends",
                    description="Dep desc",
                    dependencies=["dep-1"],
                ),
            ],
        )

        created_bodies: list[str] = []

        async def mock_create_issue(**kwargs):
            created_bodies.append(kwargs.get("body", ""))
            num = len(created_bodies) + 9
            return {"number": num, "html_url": f"https://github.com/o/r/issues/{num}"}

        mock_service = AsyncMock()
        mock_service.create_issue = AsyncMock(side_effect=mock_create_issue)

        with patch(
            "src.services.github_projects.service.GitHubProjectsService",
            return_value=mock_service,
        ):
            await create_plan_issues(
                access_token="token",
                plan=plan_dict,
                owner="o",
                repo="r",
                db=mock_db,
            )

        # created_bodies[0] = parent issue body
        # created_bodies[1] = first sub-issue (no deps)
        # created_bodies[2] = second sub-issue (depends on first)
        assert len(created_bodies) == 3
        assert "Part of #10" in created_bodies[1]  # references parent
        assert "Depends on #11" in created_bodies[2]  # references first sub-issue
        assert "Part of #10" in created_bodies[2]

    @pytest.mark.anyio
    async def test_parent_issue_body_has_checklist(self, mock_db):
        """Parent issue body should contain step checklist."""
        plan_model = Plan(
            plan_id="plan-4",
            session_id="sess-1",
            title="Plan",
            summary="My summary",
            status="approved",
            project_id="proj-1",
            project_name="P",
            repo_owner="o",
            repo_name="r",
            steps=[
                PlanStep(
                    step_id="x-1", plan_id="plan-4", position=0, title="Step A", description="D"
                ),
                PlanStep(
                    step_id="x-2", plan_id="plan-4", position=1, title="Step B", description="D"
                ),
            ],
        )
        await save_plan(mock_db, plan_model)

        plan_dict = _make_plan_dict(
            plan_id="plan-4",
            title="Plan",
            summary="My summary",
            steps=[
                _make_step_dict(step_id="x-1", position=0, title="Step A"),
                _make_step_dict(step_id="x-2", position=1, title="Step B"),
            ],
        )

        parent_body_ref: list[str] = []

        async def mock_create_issue(**kwargs):
            if not parent_body_ref:
                parent_body_ref.append(kwargs.get("body", ""))
            num = len(parent_body_ref) + 199
            return {"number": num, "html_url": f"https://github.com/o/r/issues/{num}"}

        mock_service = AsyncMock()
        mock_service.create_issue = AsyncMock(side_effect=mock_create_issue)

        with patch(
            "src.services.github_projects.service.GitHubProjectsService",
            return_value=mock_service,
        ):
            await create_plan_issues(
                access_token="token",
                plan=plan_dict,
                owner="o",
                repo="r",
                db=mock_db,
            )

        body = parent_body_ref[0]
        assert "My summary" in body
        assert "- [ ] **Step 1**: Step A" in body
        assert "- [ ] **Step 2**: Step B" in body
        assert "## Implementation Steps" in body
