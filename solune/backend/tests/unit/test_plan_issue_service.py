"""Unit tests for plan_issue_service formatting helpers."""

from src.services.plan_issue_service import format_plan_issue_markdown


def _make_plan_dict() -> dict:
    return {
        "plan_id": "plan-1",
        "title": "Test Plan",
        "summary": "Plan summary",
        "steps": [
            {
                "step_id": "step-1",
                "position": 0,
                "title": "Investigate current flow",
                "description": "Review the existing approval path.",
                "dependencies": [],
            },
            {
                "step_id": "step-2",
                "position": 1,
                "title": "Route approval through intake",
                "description": "Use the shared pipeline launch helper.",
                "dependencies": ["step-1"],
            },
        ],
    }


def test_format_plan_issue_markdown_renders_title_summary_and_steps():
    markdown = format_plan_issue_markdown(_make_plan_dict())

    assert markdown.startswith("# Test Plan")
    assert "Plan summary" in markdown
    assert "## Implementation Steps" in markdown
    assert "### Step 1: Investigate current flow" in markdown
    assert "Review the existing approval path." in markdown
    assert "### Step 2: Route approval through intake" in markdown


def test_format_plan_issue_markdown_includes_dependency_labels():
    markdown = format_plan_issue_markdown(_make_plan_dict())

    assert "Dependencies:" in markdown
    assert "- Step 1: Investigate current flow" in markdown


def test_format_plan_issue_markdown_skips_invalid_step_entries():
    plan = _make_plan_dict()
    plan["steps"] = [plan["steps"][0], "not-a-step", None]

    markdown = format_plan_issue_markdown(plan)

    assert "### Step 1: Investigate current flow" in markdown
    assert "not-a-step" not in markdown
