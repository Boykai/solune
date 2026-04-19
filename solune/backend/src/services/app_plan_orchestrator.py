"""App Plan Orchestrator — orchestrates multi-phase plan-driven app creation.

Coordinates the full flow: generate plan via chat agent → run speckit.plan →
parse phases from plan.md → create GitHub parent issues per phase → launch
pipelines with wave-based prerequisite queuing.
"""
# pyright: basic
# reason: Legacy service module; pending follow-up typing pass.

from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass
from typing import Any

from src.logging_utils import get_logger
from src.services.plan_parser import PlanPhase, group_into_waves, parse_plan

logger = get_logger(__name__)

# Status state machine for orchestration tracking
ORCHESTRATION_STATUSES = (
    "planning",
    "speckit_running",
    "parsing_phases",
    "creating_issues",
    "launching_pipelines",
    "active",
    "failed",
)


@dataclass
class OrchestrationResult:
    """Result of an orchestration step."""

    success: bool
    orchestration_id: str
    status: str
    phase_count: int = 0
    phase_issue_numbers: list[int] | None = None
    error_message: str | None = None


class AppPlanOrchestrator:
    """Orchestrates multi-phase plan-driven app creation.

    Coordinates: chat plan agent → speckit.plan → parse plan.md →
    create phase issues → launch pipelines with wave-based queuing.
    """

    def __init__(
        self,
        *,
        github_service: Any,
        connection_manager: Any | None = None,
        db: Any | None = None,
    ) -> None:
        self._github_service = github_service
        self._connection_manager = connection_manager
        self._db = db

    async def orchestrate_app_creation(
        self,
        *,
        app_name: str,
        description: str,
        project_id: str,
        pipeline_id: str,
        access_token: str,
        owner: str,
        repo: str,
        orchestration_id: str | None = None,
        speckit_timeout: int = 1200,
        poll_interval: int = 30,
        global_timeout: int | None = None,
    ) -> OrchestrationResult:
        """Orchestrate the full plan-driven app creation flow.

        Args:
            app_name: Name of the app being created.
            description: App description used for planning.
            project_id: GitHub project ID for issue tracking.
            pipeline_id: Pipeline configuration to use for phases.
            access_token: GitHub access token.
            owner: Repository owner.
            repo: Repository name.
            orchestration_id: Unique ID for this orchestration (auto-generated if omitted).
            speckit_timeout: Max seconds to wait for speckit.plan completion.
            poll_interval: Seconds between completion checks.
            global_timeout: Overall timeout for the entire orchestration.
                Defaults to ``Settings.orchestration_global_timeout_seconds``.

        Returns:
            OrchestrationResult with status and phase information.
        """
        if global_timeout is None:
            from src.config import get_settings

            global_timeout = get_settings().orchestration_global_timeout_seconds

        orch_id = orchestration_id or str(uuid.uuid4())

        try:
            async with asyncio.timeout(global_timeout):
                # Step 1: planning — generate structured plan via chat agent
                await self._update_status(orch_id, project_id, "planning", app_name=app_name)
                plan_summary = await self._run_plan_agent(description, project_id, access_token)

                # Step 2: speckit_running — launch speckit.plan on a temporary issue
                await self._update_status(orch_id, project_id, "speckit_running", app_name=app_name)
                plan_md_content = await self._run_speckit_plan(
                    plan_summary=plan_summary,
                    app_name=app_name,
                    project_id=project_id,
                    access_token=access_token,
                    owner=owner,
                    repo=repo,
                    speckit_max_wait=speckit_timeout,
                    poll_interval=poll_interval,
                )

                # Step 3: parsing_phases — parse plan.md into PlanPhase objects
                await self._update_status(orch_id, project_id, "parsing_phases", app_name=app_name)
                phases = parse_plan(plan_md_content)
                if not phases:
                    msg = "No phases found in plan.md"
                    raise ValueError(msg)  # noqa: TRY301 — reason: raise in except acceptable for this pattern

                # Step 4: creating_issues — create GitHub parent issues per phase
                await self._update_status(orch_id, project_id, "creating_issues", app_name=app_name)
                phase_issue_numbers = await self._create_phase_issues(
                    phases=phases,
                    app_name=app_name,
                    description=description,
                    project_id=project_id,
                    access_token=access_token,
                    owner=owner,
                    repo=repo,
                )

                # Step 5: launching_pipelines — launch with wave-based queuing
                await self._update_status(
                    orch_id, project_id, "launching_pipelines", app_name=app_name
                )
                await self._launch_phase_pipelines(
                    phases=phases,
                    phase_issue_numbers=phase_issue_numbers,
                    project_id=project_id,
                    pipeline_id=pipeline_id,
                    access_token=access_token,
                    owner=owner,
                    repo=repo,
                )

                # Step 6: active — orchestration complete
                await self._update_status(orch_id, project_id, "active", app_name=app_name)

                # Persist final state
                await self._save_orchestration(
                    orch_id,
                    app_name=app_name,
                    project_id=project_id,
                    status="active",
                    plan_md_content=plan_md_content,
                    phase_count=len(phases),
                    phase_issue_numbers=phase_issue_numbers,
                )

                # Broadcast terminal success event
                await self._broadcast(
                    project_id,
                    {
                        "type": "plan_orchestration_complete",
                        "orchestration_id": orch_id,
                        "app_name": app_name,
                        "phase_count": len(phases),
                    },
                )

                return OrchestrationResult(
                    success=True,
                    orchestration_id=orch_id,
                    status="active",
                    phase_count=len(phases),
                    phase_issue_numbers=phase_issue_numbers,
                )

        except TimeoutError:
            logger.error(
                "Orchestration %s timed out after %ds for app %s",
                orch_id,
                global_timeout,
                app_name,
            )
            error_msg = f"Orchestration timed out after {global_timeout}s"
            await self._update_status(
                orch_id, project_id, "failed", app_name=app_name, error=error_msg
            )
            await self._save_orchestration(
                orch_id,
                app_name=app_name,
                project_id=project_id,
                status="failed",
                error_message=error_msg,
            )
            await self._broadcast(
                project_id,
                {
                    "type": "plan_orchestration_failed",
                    "orchestration_id": orch_id,
                    "app_name": app_name,
                    "error": error_msg,
                },
            )
            return OrchestrationResult(
                success=False,
                orchestration_id=orch_id,
                status="failed",
                error_message=error_msg,
            )

        except Exception as exc:
            logger.error(
                "Orchestration %s failed for app %s: %s",
                orch_id,
                app_name,
                exc,
                exc_info=True,
            )
            await self._update_status(
                orch_id, project_id, "failed", app_name=app_name, error=str(exc)
            )
            await self._save_orchestration(
                orch_id,
                app_name=app_name,
                project_id=project_id,
                status="failed",
                error_message=str(exc),
            )

            # Broadcast terminal failure event
            await self._broadcast(
                project_id,
                {
                    "type": "plan_orchestration_failed",
                    "orchestration_id": orch_id,
                    "app_name": app_name,
                    "error": str(exc),
                },
            )

            return OrchestrationResult(
                success=False,
                orchestration_id=orch_id,
                status="failed",
                error_message=str(exc),
            )

    async def _run_plan_agent(
        self,
        description: str,
        project_id: str,
        access_token: str,
    ) -> str:
        """Run the chat plan agent to generate a structured plan summary."""
        from src.config import get_settings
        from src.services.chat_agent import get_chat_agent_service

        chat_agent = get_chat_agent_service()
        session_id = uuid.uuid4()
        timeout = get_settings().agent_copilot_timeout_seconds
        result = await asyncio.wait_for(
            chat_agent.run_plan(
                message=description,
                session_id=session_id,
                github_token=access_token,
                project_id=project_id,
            ),
            timeout=timeout,
        )
        return result.content if hasattr(result, "content") else str(result)

    async def _run_speckit_plan(
        self,
        *,
        plan_summary: str,
        app_name: str,
        project_id: str,
        access_token: str,
        owner: str,
        repo: str,
        speckit_max_wait: int = 1200,
        poll_interval: int = 30,
    ) -> str:
        """Create a temporary issue, assign speckit.plan, and fetch plan.md."""
        # Create temporary planning issue
        issue_title = f"[Planning] {app_name} — speckit.plan"
        issue_body = (
            f"## Automated Planning Issue\n\n"
            f"This issue was created automatically to run `speckit.plan` for **{app_name}**.\n\n"
            f"### Plan Summary\n\n{plan_summary}\n\n"
            f"---\n*This issue will be closed automatically after plan generation.*"
        )
        issue = await self._github_service.create_issue(
            access_token=access_token,
            owner=owner,
            repo=repo,
            title=issue_title,
            body=issue_body,
        )
        issue_number = issue["number"]
        issue_node_id = issue["node_id"]
        logger.info("Created planning issue #%d for app %s", issue_number, app_name)

        try:
            # Assign speckit.plan agent
            await self._github_service.assign_copilot_to_issue(
                access_token=access_token,
                owner=owner,
                repo=repo,
                issue_node_id=issue_node_id,
                issue_number=issue_number,
                custom_agent="speckit.plan",
                custom_instructions=plan_summary,
            )

            # Poll for completion
            elapsed = 0
            while elapsed < speckit_max_wait:
                if poll_interval > 0:
                    await asyncio.sleep(poll_interval)
                elapsed += max(poll_interval, 1)  # Ensure progress even with poll_interval=0

                done = await self._github_service.check_agent_completion_comment(
                    access_token=access_token,
                    owner=owner,
                    repo=repo,
                    issue_number=issue_number,
                    agent_name="speckit.plan",
                )
                if done:
                    logger.info("speckit.plan completed for issue #%d", issue_number)
                    break
            else:
                msg = f"speckit.plan timed out after {speckit_max_wait}s on issue #{issue_number}"
                raise TimeoutError(msg)

            # Discover PR branch from the issue
            pr_branch = await self._discover_pr_branch(
                access_token=access_token,
                owner=owner,
                repo=repo,
                issue_number=issue_number,
            )

            # Fetch plan.md from the PR branch
            plan_md = await self._github_service.get_file_content_from_ref(
                access_token=access_token,
                owner=owner,
                repo=repo,
                path="plan.md",
                ref=pr_branch,
            )
            if not plan_md:
                # Try alternative spec path
                plan_md = await self._github_service.get_file_content_from_ref(
                    access_token=access_token,
                    owner=owner,
                    repo=repo,
                    path=f"specs/001-{app_name}/plan.md",
                    ref=pr_branch,
                )
            if not plan_md:
                msg = f"plan.md not found on branch {pr_branch}"
                raise FileNotFoundError(msg)

            return plan_md

        finally:
            # Close the temporary planning issue
            try:
                await self._github_service.close_issue(
                    access_token=access_token,
                    owner=owner,
                    repo=repo,
                    issue_number=issue_number,
                )
                logger.info("Closed planning issue #%d", issue_number)
            except Exception:  # noqa: BLE001 — reason: orchestrator resilience; logs and continues
                logger.warning("Failed to close planning issue #%d", issue_number, exc_info=True)

    async def _discover_pr_branch(
        self,
        *,
        access_token: str,
        owner: str,
        repo: str,
        issue_number: int,
    ) -> str:
        """Discover the PR branch associated with an issue."""
        try:
            prs = await self._github_service.list_pull_requests_for_issue(
                access_token=access_token,
                owner=owner,
                repo=repo,
                issue_number=issue_number,
            )
            if prs:
                return prs[0].get("head", {}).get("ref", "main")
        except Exception:  # noqa: BLE001 — reason: orchestrator resilience; logs and continues
            logger.warning(
                "Could not discover PR branch for issue #%d, using main",
                issue_number,
                exc_info=True,
            )
        return "main"

    async def _create_phase_issues(
        self,
        *,
        phases: list[PlanPhase],
        app_name: str,
        description: str,
        project_id: str,
        access_token: str,
        owner: str,
        repo: str,
    ) -> list[int]:
        """Create a GitHub parent issue for each plan phase.

        Returns:
            List of issue numbers in phase order.
        """
        total = len(phases)
        issue_numbers: list[int] = []

        for phase in phases:
            title = f"Phase {phase.index}/{total}: {phase.title} — {app_name}"

            # Build issue body
            steps_text = "\n".join(f"  {s}" for s in phase.steps) if phase.steps else "*(no steps)*"
            deps_text = (
                ", ".join(f"Phase {d}" for d in phase.depends_on_phases)
                if phase.depends_on_phases
                else "None"
            )

            body = (
                f"## Phase {phase.index} of {total}: {phase.title}\n\n"
                f"This is Phase {phase.index} of {total} in building **{app_name}**: "
                f"{description}\n\n"
                f"### Description\n\n{phase.description}\n\n"
                f"### Steps\n\n{steps_text}\n\n"
                f"### Dependencies\n\n{deps_text}\n\n"
                f"### Execution Mode\n\n{phase.execution_mode}\n"
            )

            issue = await self._github_service.create_issue(
                access_token=access_token,
                owner=owner,
                repo=repo,
                title=title,
                body=body,
            )
            issue_number = issue["number"]
            issue_numbers.append(issue_number)

            # Add to project board
            try:
                issue_node_id = issue.get("node_id")
                if issue_node_id and project_id:
                    await self._github_service.add_issue_to_project(
                        access_token=access_token,
                        project_id=project_id,
                        issue_node_id=issue_node_id,
                        issue_database_id=issue.get("id"),
                    )
            except Exception:  # noqa: BLE001 — reason: orchestrator resilience; logs and continues
                logger.warning(
                    "Failed to add phase issue #%d to project board",
                    issue_number,
                    exc_info=True,
                )

            logger.info(
                "Created phase issue #%d: Phase %d/%d — %s",
                issue_number,
                phase.index,
                total,
                phase.title,
            )

            # Broadcast phase creation event
            await self._broadcast(
                project_id,
                {
                    "type": "plan_phase_created",
                    "app_name": app_name,
                    "phase_index": phase.index,
                    "phase_total": total,
                    "phase_title": phase.title,
                    "issue_number": issue_number,
                    "issue_url": issue.get("html_url", ""),
                },
            )

        return issue_numbers

    async def _launch_phase_pipelines(
        self,
        *,
        phases: list[PlanPhase],
        phase_issue_numbers: list[int],
        project_id: str,
        pipeline_id: str,
        access_token: str,
        owner: str,
        repo: str,
    ) -> None:
        """Launch pipelines for each phase using wave-based queuing.

        Wave 1 phases launch immediately with auto_merge=True.
        Wave 2+ phases are queued with prerequisite_issues pointing
        to prior wave issue numbers.
        """
        from src.api.pipelines import execute_pipeline_launch
        from src.models.user import UserSession

        waves = group_into_waves(phases)

        # Build phase_index → issue_number mapping
        phase_to_issue: dict[int, int] = {}
        for phase, issue_num in zip(phases, phase_issue_numbers, strict=True):
            phase_to_issue[phase.index] = issue_num

        # Create a system session for pipeline launches
        session = UserSession(
            access_token=access_token,
            github_user_id="orchestrator",
            github_username="orchestrator",
        )
        target_repo = (owner, repo) if owner and repo else None

        for wave_idx, wave in enumerate(waves):
            for phase in wave:
                issue_number = phase_to_issue.get(phase.index)
                if issue_number is None:
                    logger.warning("No issue number for Phase %d, skipping", phase.index)
                    continue

                # Compute prerequisite issue numbers from dependency graph
                prereq_issues = [
                    phase_to_issue[dep] for dep in phase.depends_on_phases if dep in phase_to_issue
                ]

                try:
                    await execute_pipeline_launch(
                        project_id=project_id,
                        issue_description=f"Phase {phase.index}: {phase.title}",
                        pipeline_id=pipeline_id,
                        session=session,
                        auto_merge=True,
                        prerequisite_issues=prereq_issues or None,
                        target_repo=target_repo,
                    )
                    logger.info(
                        "Launched pipeline for Phase %d (wave %d, prerequisites: %s)",
                        phase.index,
                        wave_idx + 1,
                        prereq_issues or "none",
                    )
                except Exception:
                    logger.error(
                        "Failed to launch pipeline for Phase %d",
                        phase.index,
                        exc_info=True,
                    )

    async def _update_status(
        self,
        orchestration_id: str,
        project_id: str,
        status: str,
        *,
        app_name: str | None = None,
        error: str | None = None,
    ) -> None:
        """Update orchestration status and broadcast via WebSocket."""
        logger.info("Orchestration %s: status → %s", orchestration_id, status)

        if self._db:
            try:
                from src.utils import utcnow

                await self._db.execute(
                    """UPDATE app_plan_orchestrations
                       SET status = ?, error_message = ?, updated_at = ?
                       WHERE id = ?""",
                    (status, error, utcnow().isoformat(), orchestration_id),
                )
                await self._db.commit()
            except Exception:  # noqa: BLE001 — reason: orchestrator resilience; logs and continues
                logger.warning("Failed to update orchestration status in DB", exc_info=True)

        payload: dict[str, Any] = {
            "type": "plan_status_update",
            "orchestration_id": orchestration_id,
            "status": status,
        }
        if app_name:
            payload["app_name"] = app_name
        if error:
            payload["error"] = error

        await self._broadcast(project_id, payload)

    async def _broadcast(self, project_id: str, payload: dict) -> None:
        """Broadcast a message to project WebSocket connections."""
        if self._connection_manager:
            try:
                await self._connection_manager.broadcast_to_project(project_id, payload)
            except Exception:  # noqa: BLE001 — reason: orchestrator resilience; logs and continues
                logger.warning("WebSocket broadcast failed", exc_info=True)

    async def _save_orchestration(
        self,
        orchestration_id: str,
        *,
        app_name: str,
        project_id: str,
        status: str,
        plan_md_content: str | None = None,
        phase_count: int | None = None,
        phase_issue_numbers: list[int] | None = None,
        error_message: str | None = None,
    ) -> None:
        """Persist orchestration state to the database."""
        if not self._db:
            return

        from src.utils import utcnow

        now = utcnow().isoformat()
        phase_numbers_json = json.dumps(phase_issue_numbers) if phase_issue_numbers else None

        try:
            await self._db.execute(
                """INSERT INTO app_plan_orchestrations
                   (id, app_name, project_id, status, plan_md_content,
                    phase_count, phase_issue_numbers, error_message, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET
                     status = excluded.status,
                     plan_md_content = COALESCE(excluded.plan_md_content, plan_md_content),
                     phase_count = COALESCE(excluded.phase_count, phase_count),
                     phase_issue_numbers = COALESCE(excluded.phase_issue_numbers, phase_issue_numbers),
                     error_message = excluded.error_message,
                     updated_at = excluded.updated_at""",
                (
                    orchestration_id,
                    app_name,
                    project_id,
                    status,
                    plan_md_content,
                    phase_count,
                    phase_numbers_json,
                    error_message,
                    now,
                    now,
                ),
            )
            await self._db.commit()
        except Exception:  # noqa: BLE001 — reason: orchestrator resilience; logs and continues
            logger.warning("Failed to save orchestration state", exc_info=True)
