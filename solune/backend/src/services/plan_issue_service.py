"""Plan → GitHub Issues service.

On approval, creates a parent GitHub issue (checklist body) plus one
sub-issue per ``PlanStep``.  Updates the plan record with issue
numbers and URLs.
"""

from __future__ import annotations

import asyncio
from typing import Any

from src.logging_utils import get_logger

logger = get_logger(__name__)


async def create_plan_issues(
    access_token: str,
    plan: dict,
    owner: str,
    repo: str,
    db: Any,
) -> dict:
    """Create a parent GitHub issue and sub-issues for each plan step.

    Args:
        access_token: GitHub OAuth token with repo write access.
        plan: Plan dict as returned by ``chat_store.get_plan()``.
        owner: Repository owner (e.g. ``octocat``).
        repo: Repository name (e.g. ``my-app``).
        db: aiosqlite database connection.

    Returns:
        Dict with ``parent_issue_number``, ``parent_issue_url``, and
        ``steps`` (list of step dicts with issue links).

    Raises:
        RuntimeError: If the parent issue creation fails outright.
    """
    from src.services import chat_store
    from src.services.github_projects.service import GitHubProjectsService

    service = GitHubProjectsService()
    steps = plan.get("steps", [])

    # ── 1. Build parent issue body with step checklist ────────────────
    checklist_lines = [
        f"- [ ] **Step {step['position'] + 1}**: {step['title']}"
        for step in steps
    ]

    parent_body = (
        f"{plan['summary']}\n\n"
        f"## Implementation Steps\n\n"
        + "\n".join(checklist_lines)
    )

    # ── 2. Create parent issue ────────────────────────────────────────
    parent_issue = await service.create_issue(
        access_token=access_token,
        owner=owner,
        repo=repo,
        title=plan["title"],
        body=parent_body,
    )
    parent_number = parent_issue["number"]
    parent_url = parent_issue["html_url"]

    await chat_store.update_plan_parent_issue(db, plan["plan_id"], parent_number, parent_url)

    # ── 3. Create sub-issues sequentially ─────────────────────────────
    created_issues: list[dict] = []
    failed_steps: list[dict] = []
    step_issue_map: dict[str, int] = {}  # step_id → issue_number

    for step in steps:
        # Build dependency references
        dep_refs = []
        for dep_id in step.get("dependencies", []):
            dep_number = step_issue_map.get(dep_id)
            if dep_number:
                dep_refs.append(f"Depends on #{dep_number}")

        step_body_parts = [step["description"]]
        if dep_refs:
            step_body_parts.append("\n### Dependencies\n" + "\n".join(f"- {r}" for r in dep_refs))
        step_body_parts.append(f"\nPart of #{parent_number}")
        step_body = "\n".join(step_body_parts)

        try:
            issue = await service.create_issue(
                access_token=access_token,
                owner=owner,
                repo=repo,
                title=step["title"],
                body=step_body,
            )
            step_issue_map[step["step_id"]] = issue["number"]
            await chat_store.update_plan_step_issue(
                db, step["step_id"], issue["number"], issue["html_url"]
            )
            created_issues.append({
                "step_id": step["step_id"],
                "position": step["position"],
                "title": step["title"],
                "issue_number": issue["number"],
                "issue_url": issue["html_url"],
            })

            # Small delay to respect GitHub rate limits
            await asyncio.sleep(0.5)

        except Exception as e:
            logger.error(
                "Failed to create issue for step %s: %s",
                step["step_id"],
                e,
                exc_info=True,
            )
            failed_steps.append({
                "step_id": step["step_id"],
                "position": step["position"],
                "title": step["title"],
                "error": str(e),
            })

    # ── 4. Update plan status ─────────────────────────────────────────
    if failed_steps:
        await chat_store.update_plan_status(db, plan["plan_id"], "failed")
    else:
        await chat_store.update_plan_status(db, plan["plan_id"], "completed")

    return {
        "parent_issue_number": parent_number,
        "parent_issue_url": parent_url,
        "created_issues": created_issues,
        "failed_steps": failed_steps,
    }
