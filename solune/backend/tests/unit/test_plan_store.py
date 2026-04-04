"""Unit tests for chat_store plan CRUD operations.

Covers:
- save_plan / get_plan round-trip
- update_plan (title / summary metadata)
- update_plan_status lifecycle transitions
- update_plan_step_issue / update_plan_parent_issue post-approval updates
- Edge cases: missing plan, empty steps, plan replacement
- Plan versioning: snapshot_plan_version, get_plan_versions
- Step CRUD: add_plan_step, update_plan_step, delete_plan_step
- DAG validation: validate_dag, reorder_plan_steps
- Step approval: update_step_approval
"""

import pytest

from src.models.plan import Plan, PlanStep
from src.services.chat_store import (
    add_plan_step,
    delete_plan_step,
    get_plan,
    get_plan_versions,
    reorder_plan_steps,
    save_plan,
    snapshot_plan_version,
    update_plan,
    update_plan_parent_issue,
    update_plan_status,
    update_plan_step,
    update_plan_step_issue,
    update_step_approval,
    validate_dag,
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


# =============================================================================
# Plan Versioning
# =============================================================================


class TestPlanVersioning:
    """Tests for snapshot_plan_version and get_plan_versions."""

    @pytest.mark.anyio
    async def test_snapshot_creates_version(self, mock_db):
        plan = _make_plan(steps=[_make_step()])
        await save_plan(mock_db, plan)

        version_id = await snapshot_plan_version(mock_db, "plan-1")
        assert version_id is not None

        versions = await get_plan_versions(mock_db, "plan-1")
        assert len(versions) == 1
        assert versions[0]["version"] == 1
        assert versions[0]["title"] == "Test Plan"

    @pytest.mark.anyio
    async def test_snapshot_increments_plan_version(self, mock_db):
        plan = _make_plan()
        await save_plan(mock_db, plan)

        await snapshot_plan_version(mock_db, "plan-1")
        result = await get_plan(mock_db, "plan-1")
        assert result is not None
        assert result["version"] == 2

    @pytest.mark.anyio
    async def test_multiple_snapshots(self, mock_db):
        plan = _make_plan()
        await save_plan(mock_db, plan)

        await snapshot_plan_version(mock_db, "plan-1")
        await snapshot_plan_version(mock_db, "plan-1")

        versions = await get_plan_versions(mock_db, "plan-1")
        assert len(versions) == 2
        # Ordered by version DESC
        assert versions[0]["version"] == 2
        assert versions[1]["version"] == 1

    @pytest.mark.anyio
    async def test_snapshot_nonexistent_plan(self, mock_db):
        result = await snapshot_plan_version(mock_db, "nonexistent")
        assert result is None

    @pytest.mark.anyio
    async def test_get_versions_empty(self, mock_db):
        plan = _make_plan()
        await save_plan(mock_db, plan)

        versions = await get_plan_versions(mock_db, "plan-1")
        assert versions == []

    @pytest.mark.anyio
    async def test_version_preserves_steps(self, mock_db):
        steps = [_make_step(step_id="s-1", position=0, title="Step A")]
        plan = _make_plan(steps=steps)
        await save_plan(mock_db, plan)

        await snapshot_plan_version(mock_db, "plan-1")
        versions = await get_plan_versions(mock_db, "plan-1")
        assert len(versions) == 1
        import json

        steps_data = json.loads(versions[0]["steps_json"])
        assert len(steps_data) == 1
        assert steps_data[0]["title"] == "Step A"


# =============================================================================
# DAG Validation
# =============================================================================


class TestDAGValidation:
    """Tests for validate_dag using Kahn's algorithm."""

    def test_valid_dag_no_dependencies(self):
        steps = [
            {"step_id": "a", "dependencies": []},
            {"step_id": "b", "dependencies": []},
        ]
        is_valid, err = validate_dag(steps)
        assert is_valid is True
        assert err == ""

    def test_valid_dag_with_dependencies(self):
        steps = [
            {"step_id": "a", "dependencies": []},
            {"step_id": "b", "dependencies": ["a"]},
            {"step_id": "c", "dependencies": ["a", "b"]},
        ]
        is_valid, err = validate_dag(steps)
        assert is_valid is True

    def test_circular_dependency_detected(self):
        steps = [
            {"step_id": "a", "dependencies": ["b"]},
            {"step_id": "b", "dependencies": ["a"]},
        ]
        is_valid, err = validate_dag(steps)
        assert is_valid is False
        assert "Circular dependency" in err

    def test_self_dependency_detected(self):
        steps = [
            {"step_id": "a", "dependencies": ["a"]},
        ]
        is_valid, err = validate_dag(steps)
        assert is_valid is False
        assert "Circular dependency" in err

    def test_unknown_dependency_detected(self):
        steps = [
            {"step_id": "a", "dependencies": ["nonexistent"]},
        ]
        is_valid, err = validate_dag(steps)
        assert is_valid is False
        assert "unknown step" in err

    def test_complex_dag(self):
        steps = [
            {"step_id": "a", "dependencies": []},
            {"step_id": "b", "dependencies": ["a"]},
            {"step_id": "c", "dependencies": ["a"]},
            {"step_id": "d", "dependencies": ["b", "c"]},
            {"step_id": "e", "dependencies": ["d"]},
        ]
        is_valid, err = validate_dag(steps)
        assert is_valid is True

    def test_three_node_cycle(self):
        steps = [
            {"step_id": "a", "dependencies": ["c"]},
            {"step_id": "b", "dependencies": ["a"]},
            {"step_id": "c", "dependencies": ["b"]},
        ]
        is_valid, err = validate_dag(steps)
        assert is_valid is False
        assert "Circular dependency" in err

    def test_empty_steps_valid(self):
        is_valid, err = validate_dag([])
        assert is_valid is True


# =============================================================================
# Step CRUD
# =============================================================================


class TestStepCRUD:
    """Tests for add_plan_step, update_plan_step, delete_plan_step."""

    @pytest.mark.anyio
    async def test_add_step(self, mock_db):
        plan = _make_plan()
        await save_plan(mock_db, plan)

        step = await add_plan_step(mock_db, "plan-1", "New Step", "Description")
        assert step is not None
        assert step["title"] == "New Step"
        assert step["position"] == 0

        result = await get_plan(mock_db, "plan-1")
        assert result is not None
        assert len(result["steps"]) == 1

    @pytest.mark.anyio
    async def test_add_step_auto_position(self, mock_db):
        steps = [_make_step(step_id="s-1", position=0)]
        plan = _make_plan(steps=steps)
        await save_plan(mock_db, plan)

        step = await add_plan_step(mock_db, "plan-1", "Step 2", "Desc")
        assert step is not None
        assert step["position"] == 1

    @pytest.mark.anyio
    async def test_add_step_with_dependencies(self, mock_db):
        steps = [_make_step(step_id="s-1", position=0)]
        plan = _make_plan(steps=steps)
        await save_plan(mock_db, plan)

        step = await add_plan_step(
            mock_db, "plan-1", "Step 2", "Desc", dependencies=["s-1"]
        )
        assert step is not None
        assert step["dependencies"] == ["s-1"]

    @pytest.mark.anyio
    async def test_add_step_dag_violation(self, mock_db):
        plan = _make_plan()
        await save_plan(mock_db, plan)

        with pytest.raises(ValueError, match="DAG validation failed"):
            await add_plan_step(
                mock_db, "plan-1", "Bad Step", "Desc", dependencies=["nonexistent"]
            )

    @pytest.mark.anyio
    async def test_add_step_non_draft_rejected(self, mock_db):
        plan = _make_plan()
        await save_plan(mock_db, plan)
        await update_plan_status(mock_db, "plan-1", "approved")

        with pytest.raises(ValueError, match="non-draft"):
            await add_plan_step(mock_db, "plan-1", "Step", "Desc")

    @pytest.mark.anyio
    async def test_add_step_nonexistent_plan(self, mock_db):
        result = await add_plan_step(mock_db, "nonexistent", "Step", "Desc")
        assert result is None

    @pytest.mark.anyio
    async def test_update_step_title(self, mock_db):
        steps = [_make_step(step_id="s-1", position=0, title="Old")]
        plan = _make_plan(steps=steps)
        await save_plan(mock_db, plan)

        updated = await update_plan_step(mock_db, "plan-1", "s-1", title="New Title")
        assert updated is not None
        assert updated["title"] == "New Title"

    @pytest.mark.anyio
    async def test_update_step_dependencies(self, mock_db):
        steps = [
            _make_step(step_id="s-1", position=0),
            _make_step(step_id="s-2", position=1),
        ]
        plan = _make_plan(steps=steps)
        await save_plan(mock_db, plan)

        updated = await update_plan_step(
            mock_db, "plan-1", "s-2", dependencies=["s-1"]
        )
        assert updated is not None
        assert updated["dependencies"] == ["s-1"]

    @pytest.mark.anyio
    async def test_update_step_dag_violation(self, mock_db):
        steps = [
            _make_step(step_id="s-1", position=0, dependencies=["s-2"]),
            _make_step(step_id="s-2", position=1),
        ]
        plan = _make_plan(steps=steps)
        await save_plan(mock_db, plan)

        with pytest.raises(ValueError, match="DAG validation failed"):
            await update_plan_step(
                mock_db, "plan-1", "s-2", dependencies=["s-1"]
            )

    @pytest.mark.anyio
    async def test_update_nonexistent_step(self, mock_db):
        plan = _make_plan()
        await save_plan(mock_db, plan)

        result = await update_plan_step(mock_db, "plan-1", "nonexistent", title="X")
        assert result is None

    @pytest.mark.anyio
    async def test_delete_step(self, mock_db):
        steps = [
            _make_step(step_id="s-1", position=0),
            _make_step(step_id="s-2", position=1),
        ]
        plan = _make_plan(steps=steps)
        await save_plan(mock_db, plan)

        deleted = await delete_plan_step(mock_db, "plan-1", "s-1")
        assert deleted is True

        result = await get_plan(mock_db, "plan-1")
        assert result is not None
        assert len(result["steps"]) == 1
        assert result["steps"][0]["step_id"] == "s-2"
        assert result["steps"][0]["position"] == 0  # Re-indexed

    @pytest.mark.anyio
    async def test_delete_step_cascades_deps(self, mock_db):
        steps = [
            _make_step(step_id="s-1", position=0),
            _make_step(step_id="s-2", position=1, dependencies=["s-1"]),
        ]
        plan = _make_plan(steps=steps)
        await save_plan(mock_db, plan)

        deleted = await delete_plan_step(mock_db, "plan-1", "s-1")
        assert deleted is True

        result = await get_plan(mock_db, "plan-1")
        assert result is not None
        assert result["steps"][0]["dependencies"] == []

    @pytest.mark.anyio
    async def test_delete_nonexistent_step(self, mock_db):
        plan = _make_plan()
        await save_plan(mock_db, plan)

        deleted = await delete_plan_step(mock_db, "plan-1", "nonexistent")
        assert deleted is False


# =============================================================================
# Step Reorder
# =============================================================================


class TestStepReorder:
    """Tests for reorder_plan_steps."""

    @pytest.mark.anyio
    async def test_reorder_steps(self, mock_db):
        steps = [
            _make_step(step_id="s-1", position=0),
            _make_step(step_id="s-2", position=1),
            _make_step(step_id="s-3", position=2),
        ]
        plan = _make_plan(steps=steps)
        await save_plan(mock_db, plan)

        ok = await reorder_plan_steps(mock_db, "plan-1", ["s-3", "s-1", "s-2"])
        assert ok is True

        result = await get_plan(mock_db, "plan-1")
        assert result is not None
        assert result["steps"][0]["step_id"] == "s-3"
        assert result["steps"][1]["step_id"] == "s-1"
        assert result["steps"][2]["step_id"] == "s-2"

    @pytest.mark.anyio
    async def test_reorder_mismatched_ids_rejected(self, mock_db):
        steps = [_make_step(step_id="s-1", position=0)]
        plan = _make_plan(steps=steps)
        await save_plan(mock_db, plan)

        with pytest.raises(ValueError, match="exactly the current step IDs"):
            await reorder_plan_steps(mock_db, "plan-1", ["s-1", "s-extra"])

    @pytest.mark.anyio
    async def test_reorder_non_draft_rejected(self, mock_db):
        steps = [_make_step(step_id="s-1", position=0)]
        plan = _make_plan(steps=steps)
        await save_plan(mock_db, plan)
        await update_plan_status(mock_db, "plan-1", "approved")

        with pytest.raises(ValueError, match="non-draft"):
            await reorder_plan_steps(mock_db, "plan-1", ["s-1"])


# =============================================================================
# Step Approval
# =============================================================================


class TestStepApproval:
    """Tests for update_step_approval."""

    @pytest.mark.anyio
    async def test_approve_step(self, mock_db):
        steps = [_make_step(step_id="s-1", position=0)]
        plan = _make_plan(steps=steps)
        await save_plan(mock_db, plan)

        ok = await update_step_approval(mock_db, "plan-1", "s-1", "approved")
        assert ok is True

        result = await get_plan(mock_db, "plan-1")
        assert result is not None
        assert result["steps"][0]["approval_status"] == "approved"

    @pytest.mark.anyio
    async def test_reject_step(self, mock_db):
        steps = [_make_step(step_id="s-1", position=0)]
        plan = _make_plan(steps=steps)
        await save_plan(mock_db, plan)

        ok = await update_step_approval(mock_db, "plan-1", "s-1", "rejected")
        assert ok is True

        result = await get_plan(mock_db, "plan-1")
        assert result is not None
        assert result["steps"][0]["approval_status"] == "rejected"

    @pytest.mark.anyio
    async def test_approve_non_draft_rejected(self, mock_db):
        steps = [_make_step(step_id="s-1", position=0)]
        plan = _make_plan(steps=steps)
        await save_plan(mock_db, plan)
        await update_plan_status(mock_db, "plan-1", "approved")

        with pytest.raises(ValueError, match="non-draft"):
            await update_step_approval(mock_db, "plan-1", "s-1", "approved")

    @pytest.mark.anyio
    async def test_approve_nonexistent_step(self, mock_db):
        plan = _make_plan()
        await save_plan(mock_db, plan)

        ok = await update_step_approval(mock_db, "plan-1", "nonexistent", "approved")
        assert ok is False
