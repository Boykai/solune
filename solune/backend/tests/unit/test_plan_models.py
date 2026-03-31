"""Unit tests for Plan and PlanStep models.

Covers:
- Plan / PlanStep construction and field validation
- PlanStatus enum values
- PlanResponse / PlanStepResponse / PlanApprovalResponse serialization
- PlanUpdateRequest optional fields
- Edge cases: max lengths, empty dependencies, default factories
"""

import pytest
from pydantic import ValidationError

from src.models.plan import (
    Plan,
    PlanApprovalResponse,
    PlanExitResponse,
    PlanResponse,
    PlanStatus,
    PlanStep,
    PlanStepResponse,
    PlanUpdateRequest,
)

# =============================================================================
# PlanStatus
# =============================================================================


class TestPlanStatus:
    """PlanStatus enum lifecycle values."""

    def test_all_statuses(self):
        assert set(PlanStatus) == {"draft", "approved", "completed", "failed"}

    def test_draft_is_default(self):
        plan = Plan(
            session_id="s-1",
            title="T",
            summary="S",
            project_id="p-1",
            project_name="P",
            repo_owner="owner",
            repo_name="repo",
        )
        assert plan.status == PlanStatus.DRAFT


# =============================================================================
# PlanStep
# =============================================================================


class TestPlanStep:
    """PlanStep field validation."""

    def test_valid_step(self):
        step = PlanStep(
            plan_id="plan-1",
            position=0,
            title="Implement auth",
            description="Add OAuth flow",
        )
        assert step.plan_id == "plan-1"
        assert step.position == 0
        assert step.dependencies == []
        assert step.issue_number is None
        assert step.issue_url is None
        assert step.step_id  # auto-generated UUID

    def test_step_id_auto_generated(self):
        s1 = PlanStep(plan_id="p", position=0, title="A", description="D")
        s2 = PlanStep(plan_id="p", position=1, title="B", description="D")
        assert s1.step_id != s2.step_id

    def test_position_must_be_non_negative(self):
        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            PlanStep(plan_id="p", position=-1, title="A", description="D")

    def test_title_cannot_be_empty(self):
        with pytest.raises(ValidationError):
            PlanStep(plan_id="p", position=0, title="", description="D")

    def test_title_max_length(self):
        step = PlanStep(plan_id="p", position=0, title="X" * 256, description="D")
        assert len(step.title) == 256
        with pytest.raises(ValidationError):
            PlanStep(plan_id="p", position=0, title="X" * 257, description="D")

    def test_description_cannot_be_empty(self):
        with pytest.raises(ValidationError):
            PlanStep(plan_id="p", position=0, title="A", description="")

    def test_dependencies_default_empty(self):
        step = PlanStep(plan_id="p", position=0, title="A", description="D")
        assert step.dependencies == []

    def test_dependencies_preserved(self):
        step = PlanStep(
            plan_id="p",
            position=1,
            title="B",
            description="D",
            dependencies=["step-a", "step-c"],
        )
        assert step.dependencies == ["step-a", "step-c"]

    def test_issue_fields_optional(self):
        step = PlanStep(
            plan_id="p",
            position=0,
            title="A",
            description="D",
            issue_number=42,
            issue_url="https://github.com/owner/repo/issues/42",
        )
        assert step.issue_number == 42
        assert step.issue_url == "https://github.com/owner/repo/issues/42"


# =============================================================================
# Plan
# =============================================================================


class TestPlan:
    """Plan model construction and validation."""

    def _make_plan(self, **overrides) -> Plan:
        defaults = {
            "session_id": "sess-1",
            "title": "My Plan",
            "summary": "Plan summary",
            "project_id": "proj-1",
            "project_name": "My Project",
            "repo_owner": "octocat",
            "repo_name": "hello-world",
        }
        defaults.update(overrides)
        return Plan(**defaults)

    def test_valid_plan(self):
        plan = self._make_plan()
        assert plan.status == PlanStatus.DRAFT
        assert plan.steps == []
        assert plan.parent_issue_number is None
        assert plan.parent_issue_url is None
        assert plan.plan_id  # auto-generated

    def test_plan_id_auto_generated(self):
        p1 = self._make_plan()
        p2 = self._make_plan()
        assert p1.plan_id != p2.plan_id

    def test_title_required_non_empty(self):
        with pytest.raises(ValidationError):
            self._make_plan(title="")

    def test_summary_required_non_empty(self):
        with pytest.raises(ValidationError):
            self._make_plan(summary="")

    def test_project_id_required_non_empty(self):
        with pytest.raises(ValidationError):
            self._make_plan(project_id="")

    def test_repo_owner_required_non_empty(self):
        with pytest.raises(ValidationError):
            self._make_plan(repo_owner="")

    def test_repo_name_required_non_empty(self):
        with pytest.raises(ValidationError):
            self._make_plan(repo_name="")

    def test_plan_with_steps(self):
        steps = [
            PlanStep(plan_id="plan-1", position=0, title="Step 1", description="Do first"),
            PlanStep(plan_id="plan-1", position=1, title="Step 2", description="Do second"),
        ]
        plan = self._make_plan(plan_id="plan-1", steps=steps)
        assert len(plan.steps) == 2
        assert plan.steps[0].title == "Step 1"
        assert plan.steps[1].position == 1

    def test_title_max_length(self):
        plan = self._make_plan(title="T" * 256)
        assert len(plan.title) == 256
        with pytest.raises(ValidationError):
            self._make_plan(title="T" * 257)


# =============================================================================
# Response models
# =============================================================================


class TestPlanStepResponse:
    """PlanStepResponse serialization."""

    def test_serialization(self):
        resp = PlanStepResponse(
            step_id="s-1",
            position=0,
            title="Step",
            description="Desc",
            dependencies=["s-0"],
            issue_number=10,
            issue_url="https://github.com/o/r/issues/10",
        )
        data = resp.model_dump()
        assert data["step_id"] == "s-1"
        assert data["issue_number"] == 10
        assert data["dependencies"] == ["s-0"]

    def test_optional_issue_fields(self):
        resp = PlanStepResponse(
            step_id="s-1", position=0, title="Step", description="Desc", dependencies=[]
        )
        assert resp.issue_number is None
        assert resp.issue_url is None


class TestPlanResponse:
    """PlanResponse serialization."""

    def test_full_response(self):
        resp = PlanResponse(
            plan_id="plan-1",
            session_id="sess-1",
            title="My Plan",
            summary="Summary",
            status="draft",
            project_id="p-1",
            project_name="P",
            repo_owner="owner",
            repo_name="repo",
            steps=[],
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
        )
        data = resp.model_dump()
        assert data["plan_id"] == "plan-1"
        assert data["status"] == "draft"
        assert data["steps"] == []


class TestPlanApprovalResponse:
    """PlanApprovalResponse serialization."""

    def test_with_issue_links(self):
        resp = PlanApprovalResponse(
            plan_id="plan-1",
            status="completed",
            parent_issue_number=100,
            parent_issue_url="https://github.com/o/r/issues/100",
            steps=[
                PlanStepResponse(
                    step_id="s-1",
                    position=0,
                    title="Step 1",
                    description="D",
                    dependencies=[],
                    issue_number=101,
                    issue_url="https://github.com/o/r/issues/101",
                )
            ],
        )
        assert resp.parent_issue_number == 100
        assert len(resp.steps) == 1

    def test_without_issue_links(self):
        resp = PlanApprovalResponse(plan_id="plan-1", status="failed", steps=[])
        assert resp.parent_issue_number is None
        assert resp.parent_issue_url is None


class TestPlanExitResponse:
    """PlanExitResponse serialization."""

    def test_exit_response(self):
        resp = PlanExitResponse(
            message="Plan mode deactivated",
            plan_id="plan-1",
            plan_status="draft",
        )
        assert resp.message == "Plan mode deactivated"
        assert resp.plan_status == "draft"


class TestPlanUpdateRequest:
    """PlanUpdateRequest optional fields."""

    def test_title_only(self):
        req = PlanUpdateRequest(title="New Title")
        assert req.title == "New Title"
        assert req.summary is None

    def test_summary_only(self):
        req = PlanUpdateRequest(summary="New Summary")
        assert req.title is None
        assert req.summary == "New Summary"

    def test_both_fields(self):
        req = PlanUpdateRequest(title="T", summary="S")
        assert req.title == "T"
        assert req.summary == "S"

    def test_empty_request(self):
        req = PlanUpdateRequest()
        assert req.title is None
        assert req.summary is None
