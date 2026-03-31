"""Unit tests for chat_store plan CRUD operations.

Covers:
- save_plan / get_plan round-trip
- update_plan (title / summary metadata)
- update_plan_status lifecycle transitions
- update_plan_step_issue / update_plan_parent_issue post-approval updates
- Edge cases: missing plan, empty steps, plan replacement
"""

import pytest

from src.models.plan import Plan, PlanStep
from src.services.chat_store import (
    get_plan,
    save_plan,
    update_plan,
    update_plan_parent_issue,
    update_plan_status,
    update_plan_step_issue,
)

# =============================================================================
# Helpers
# =============================================================================


def _make_plan(
    plan_id: str = "plan-1",
    session_id: str = "sess-1",
    title: str = "Test Plan",
    summary: str = "Test summary",
    steps: list[PlanStep] | None = None,
    **kwargs,
) -> Plan:
    defaults = {
        "plan_id": plan_id,
        "session_id": session_id,
        "title": title,
        "summary": summary,
        "project_id": "proj-1",
        "project_name": "My Project",
        "repo_owner": "octocat",
        "repo_name": "hello-world",
        "steps": steps or [],
    }
    defaults.update(kwargs)
    return Plan(**defaults)


def _make_step(
    step_id: str = "step-1",
    plan_id: str = "plan-1",
    position: int = 0,
    title: str = "Step Title",
    description: str = "Step description",
    **kwargs,
) -> PlanStep:
    defaults = {
        "step_id": step_id,
        "plan_id": plan_id,
        "position": position,
        "title": title,
        "description": description,
    }
    defaults.update(kwargs)
    return PlanStep(**defaults)


# =============================================================================
# save_plan / get_plan
# =============================================================================


class TestSavePlanAndGetPlan:
    """Round-trip tests for plan persistence."""

    @pytest.mark.anyio
    async def test_save_and_retrieve_plan(self, mock_db):
        plan = _make_plan()
        await save_plan(mock_db, plan)

        result = await get_plan(mock_db, "plan-1")
        assert result is not None
        assert result["plan_id"] == "plan-1"
        assert result["session_id"] == "sess-1"
        assert result["title"] == "Test Plan"
        assert result["summary"] == "Test summary"
        assert result["status"] == "draft"
        assert result["project_id"] == "proj-1"
        assert result["project_name"] == "My Project"
        assert result["repo_owner"] == "octocat"
        assert result["repo_name"] == "hello-world"
        assert result["parent_issue_number"] is None
        assert result["parent_issue_url"] is None
        assert result["steps"] == []
        assert result["created_at"] is not None
        assert result["updated_at"] is not None

    @pytest.mark.anyio
    async def test_save_plan_with_steps(self, mock_db):
        steps = [
            _make_step(step_id="s-1", position=0, title="Setup DB"),
            _make_step(step_id="s-2", position=1, title="Add API", dependencies=["s-1"]),
        ]
        plan = _make_plan(steps=steps)
        await save_plan(mock_db, plan)

        result = await get_plan(mock_db, "plan-1")
        assert result is not None
        assert len(result["steps"]) == 2

        s0 = result["steps"][0]
        assert s0["step_id"] == "s-1"
        assert s0["position"] == 0
        assert s0["title"] == "Setup DB"
        assert s0["dependencies"] == []

        s1 = result["steps"][1]
        assert s1["step_id"] == "s-2"
        assert s1["position"] == 1
        assert s1["title"] == "Add API"
        assert s1["dependencies"] == ["s-1"]

    @pytest.mark.anyio
    async def test_get_plan_returns_none_for_missing(self, mock_db):
        result = await get_plan(mock_db, "nonexistent")
        assert result is None

    @pytest.mark.anyio
    async def test_save_plan_replaces_existing(self, mock_db):
        """INSERT OR REPLACE should update the plan and re-create steps."""
        plan_v1 = _make_plan(
            title="Version 1",
            steps=[
                _make_step(step_id="s-old", position=0, title="Old Step"),
            ],
        )
        await save_plan(mock_db, plan_v1)

        plan_v2 = _make_plan(
            title="Version 2",
            steps=[
                _make_step(step_id="s-new-1", position=0, title="New Step 1"),
                _make_step(step_id="s-new-2", position=1, title="New Step 2"),
            ],
        )
        await save_plan(mock_db, plan_v2)

        result = await get_plan(mock_db, "plan-1")
        assert result is not None
        assert result["title"] == "Version 2"
        assert len(result["steps"]) == 2
        assert result["steps"][0]["step_id"] == "s-new-1"
        assert result["steps"][1]["step_id"] == "s-new-2"

    @pytest.mark.anyio
    async def test_steps_ordered_by_position(self, mock_db):
        """Steps should be returned in position order regardless of insert order."""
        steps = [
            _make_step(step_id="s-2", position=2, title="Third"),
            _make_step(step_id="s-0", position=0, title="First"),
            _make_step(step_id="s-1", position=1, title="Second"),
        ]
        plan = _make_plan(steps=steps)
        await save_plan(mock_db, plan)

        result = await get_plan(mock_db, "plan-1")
        assert result is not None
        positions = [s["position"] for s in result["steps"]]
        assert positions == [0, 1, 2]

    @pytest.mark.anyio
    async def test_dependencies_serialized_as_json(self, mock_db):
        """Dependencies list should round-trip through JSON serialization."""
        steps = [
            _make_step(
                step_id="s-3",
                position=0,
                title="Complex deps",
                dependencies=["dep-a", "dep-b", "dep-c"],
            ),
        ]
        plan = _make_plan(steps=steps)
        await save_plan(mock_db, plan)

        result = await get_plan(mock_db, "plan-1")
        assert result is not None
        assert result["steps"][0]["dependencies"] == ["dep-a", "dep-b", "dep-c"]


# =============================================================================
# update_plan
# =============================================================================


class TestUpdatePlan:
    """update_plan metadata updates."""

    @pytest.mark.anyio
    async def test_update_title(self, mock_db):
        await save_plan(mock_db, _make_plan())
        updated = await update_plan(mock_db, "plan-1", title="New Title")
        assert updated is True

        result = await get_plan(mock_db, "plan-1")
        assert result is not None
        assert result["title"] == "New Title"
        assert result["summary"] == "Test summary"  # unchanged

    @pytest.mark.anyio
    async def test_update_summary(self, mock_db):
        await save_plan(mock_db, _make_plan())
        updated = await update_plan(mock_db, "plan-1", summary="New Summary")
        assert updated is True

        result = await get_plan(mock_db, "plan-1")
        assert result is not None
        assert result["summary"] == "New Summary"
        assert result["title"] == "Test Plan"  # unchanged

    @pytest.mark.anyio
    async def test_update_both(self, mock_db):
        await save_plan(mock_db, _make_plan())
        updated = await update_plan(mock_db, "plan-1", title="T", summary="S")
        assert updated is True

        result = await get_plan(mock_db, "plan-1")
        assert result is not None
        assert result["title"] == "T"
        assert result["summary"] == "S"

    @pytest.mark.anyio
    async def test_update_no_fields_returns_false(self, mock_db):
        await save_plan(mock_db, _make_plan())
        result = await update_plan(mock_db, "plan-1")
        assert result is False

    @pytest.mark.anyio
    async def test_update_nonexistent_plan_returns_false(self, mock_db):
        result = await update_plan(mock_db, "nonexistent", title="T")
        assert result is False

    @pytest.mark.anyio
    async def test_update_changes_updated_at(self, mock_db):
        await save_plan(mock_db, _make_plan())
        before = await get_plan(mock_db, "plan-1")
        assert before is not None

        await update_plan(mock_db, "plan-1", title="Changed")
        after = await get_plan(mock_db, "plan-1")
        assert after is not None
        assert after["updated_at"] >= before["updated_at"]


# =============================================================================
# update_plan_status
# =============================================================================


class TestUpdatePlanStatus:
    """Plan lifecycle status transitions."""

    @pytest.mark.anyio
    async def test_transition_to_approved(self, mock_db):
        await save_plan(mock_db, _make_plan())
        ok = await update_plan_status(mock_db, "plan-1", "approved")
        assert ok is True

        result = await get_plan(mock_db, "plan-1")
        assert result is not None
        assert result["status"] == "approved"

    @pytest.mark.anyio
    async def test_transition_to_completed(self, mock_db):
        await save_plan(mock_db, _make_plan())
        ok = await update_plan_status(mock_db, "plan-1", "completed")
        assert ok is True

        result = await get_plan(mock_db, "plan-1")
        assert result is not None
        assert result["status"] == "completed"

    @pytest.mark.anyio
    async def test_transition_to_failed(self, mock_db):
        await save_plan(mock_db, _make_plan())
        ok = await update_plan_status(mock_db, "plan-1", "failed")
        assert ok is True

        result = await get_plan(mock_db, "plan-1")
        assert result is not None
        assert result["status"] == "failed"

    @pytest.mark.anyio
    async def test_nonexistent_plan_returns_false(self, mock_db):
        ok = await update_plan_status(mock_db, "nonexistent", "approved")
        assert ok is False


# =============================================================================
# update_plan_step_issue / update_plan_parent_issue
# =============================================================================


class TestUpdatePlanIssueLinks:
    """Post-approval issue link updates."""

    @pytest.mark.anyio
    async def test_update_step_issue(self, mock_db):
        steps = [_make_step(step_id="s-1", position=0)]
        await save_plan(mock_db, _make_plan(steps=steps))

        ok = await update_plan_step_issue(mock_db, "s-1", 42, "https://github.com/o/r/issues/42")
        assert ok is True

        result = await get_plan(mock_db, "plan-1")
        assert result is not None
        assert result["steps"][0]["issue_number"] == 42
        assert result["steps"][0]["issue_url"] == "https://github.com/o/r/issues/42"

    @pytest.mark.anyio
    async def test_update_step_issue_nonexistent(self, mock_db):
        ok = await update_plan_step_issue(mock_db, "nonexistent", 1, "https://example.com")
        assert ok is False

    @pytest.mark.anyio
    async def test_update_parent_issue(self, mock_db):
        await save_plan(mock_db, _make_plan())

        ok = await update_plan_parent_issue(
            mock_db, "plan-1", 100, "https://github.com/o/r/issues/100"
        )
        assert ok is True

        result = await get_plan(mock_db, "plan-1")
        assert result is not None
        assert result["parent_issue_number"] == 100
        assert result["parent_issue_url"] == "https://github.com/o/r/issues/100"

    @pytest.mark.anyio
    async def test_update_parent_issue_nonexistent(self, mock_db):
        ok = await update_plan_parent_issue(mock_db, "nonexistent", 1, "https://example.com")
        assert ok is False
