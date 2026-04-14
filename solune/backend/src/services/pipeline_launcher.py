from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

from src.logging_utils import get_logger
from src.services.database import get_db
from src.utils import utcnow

if TYPE_CHECKING:
    from src.models.workflow import WorkflowConfiguration
    from src.services.workflow_orchestrator import WorkflowContext, WorkflowOrchestrator

logger = get_logger(__name__)


class CountActivePipelinesForProjectFn(Protocol):
    def __call__(self, project_id: str, *, exclude_issue: int | None = None) -> int: ...


@dataclass
class PipelineLaunchResult:
    """Outcome of bootstrapping a workflow pipeline after the parent issue exists."""

    status_name: str
    agent_sub_issues: dict[str, dict] = field(default_factory=dict)
    assigned_agents: list[str] = field(default_factory=list)
    queued: bool = False
    queue_position: int | None = None
    error: str | None = None

    @property
    def initial_agent(self) -> str | None:
        return self.assigned_agents[0] if self.assigned_agents else None


def _build_initial_groups(config: WorkflowConfiguration, status_name: str) -> list[Any]:
    from src.services.workflow_orchestrator import PipelineGroupInfo

    groups: list[PipelineGroupInfo] = []
    group_mappings = getattr(config, "group_mappings", None) or {}
    status_groups = group_mappings.get(status_name, [])
    groups.extend(
        PipelineGroupInfo(
            group_id=group.group_id,
            execution_mode=group.execution_mode,
            agents=[agent.slug for agent in group.agents],
            agent_statuses=(
                {agent.slug: "pending" for agent in group.agents}
                if group.execution_mode == "parallel"
                else {}
            ),
        )
        for group in sorted(status_groups, key=lambda item: item.order)
    )
    return groups


def _supports_full_status_order(config: WorkflowConfiguration) -> bool:
    return all(
        hasattr(config, attr)
        for attr in ("status_backlog", "status_ready", "status_in_progress", "status_in_review")
    )


def _safe_get_agent_configs(config: WorkflowConfiguration) -> dict[str, dict]:
    from src.services.workflow_orchestrator import get_agent_configs

    if not _supports_full_status_order(config):
        return {}
    try:
        return get_agent_configs(config)
    except AttributeError:
        return {}


async def start_pipeline(
    ctx: WorkflowContext,
    config: WorkflowConfiguration,
    orchestrator: WorkflowOrchestrator,
    *,
    caller: str,
    enable_queue_mode_gate: bool = False,
    use_app_scoped_polling: bool = False,
    register_project_monitoring: bool = False,
    auto_merge: bool = False,
    prerequisite_issues: list[int] | None = None,
    get_agent_slugs_fn: Callable[[WorkflowConfiguration, str], list[str]] | None = None,
    set_pipeline_state_fn: Callable[[int, Any], None] | None = None,
    count_active_pipelines_for_project_fn: CountActivePipelinesForProjectFn | None = None,
    get_project_launch_lock_fn: Callable[[str], asyncio.Lock] | None = None,
    get_queued_pipelines_for_project_fn: Callable[[str], list[Any]] | None = None,
) -> PipelineLaunchResult:
    """Create sub-issues, seed pipeline state, dispatch initial agents, and start polling."""

    from src.services.workflow_orchestrator import (
        PipelineState,
        find_next_actionable_status,
        get_agent_slugs,
        get_pipeline_state,
        set_pipeline_state,
    )

    get_agent_slugs_impl = get_agent_slugs_fn or get_agent_slugs
    set_pipeline_state_impl = set_pipeline_state_fn or set_pipeline_state

    status_name = config.status_backlog
    issue_number = ctx.issue_number
    if issue_number is None:
        msg = "Workflow context is missing issue number for pipeline launch"
        raise ValueError(msg)

    agent_sub_issues = await orchestrator.create_all_sub_issues(ctx)
    initial_agents = get_agent_slugs_impl(config, status_name)
    initial_groups = _build_initial_groups(config, status_name)

    if not initial_agents and _supports_full_status_order(config):
        next_status = find_next_actionable_status(config, status_name)
        if next_status and ctx.project_item_id:
            await orchestrator.github.update_item_status_by_name(
                access_token=ctx.access_token,
                project_id=ctx.project_id,
                item_id=ctx.project_item_id,
                status_name=next_status,
            )
            status_name = next_status
            initial_agents = get_agent_slugs_impl(config, status_name)
            initial_groups = _build_initial_groups(config, status_name)

    should_queue = False
    queue_position: int | None = None

    def _make_state(*, queued: bool) -> Any:
        return PipelineState(
            issue_number=issue_number,
            project_id=ctx.project_id,
            status=status_name,
            agents=initial_agents,
            agent_sub_issues=agent_sub_issues,
            started_at=utcnow(),
            groups=initial_groups,
            queued=queued,
            auto_merge=auto_merge,
            prerequisite_issues=prerequisite_issues or [],
            agent_configs=_safe_get_agent_configs(config),
            repository_owner=ctx.repository_owner,
            repository_name=ctx.repository_name,
        )

    if agent_sub_issues:
        if enable_queue_mode_gate:
            from src.services.pipeline_state_store import (
                count_active_pipelines_for_project,
                get_project_launch_lock,
                get_queued_pipelines_for_project,
            )
            from src.services.settings_store import is_queue_mode_enabled

            count_active_impl = (
                count_active_pipelines_for_project_fn or count_active_pipelines_for_project
            )
            get_lock_impl = get_project_launch_lock_fn or get_project_launch_lock
            get_queued_impl = (
                get_queued_pipelines_for_project_fn or get_queued_pipelines_for_project
            )

            queue_enabled = await is_queue_mode_enabled(get_db(), ctx.project_id)
            if queue_enabled:
                async with get_lock_impl(ctx.project_id):
                    active_count = count_active_impl(ctx.project_id, exclude_issue=issue_number)
                    should_queue = active_count > 0
                    set_pipeline_state_impl(issue_number, _make_state(queued=should_queue))
                    if should_queue:
                        queue_position = len(get_queued_impl(ctx.project_id))
            else:
                set_pipeline_state_impl(issue_number, _make_state(queued=False))
        else:
            set_pipeline_state_impl(issue_number, _make_state(queued=False))

        logger.info(
            "Pre-created %d sub-issues for issue #%d",
            len(agent_sub_issues),
            issue_number,
        )

    if should_queue:
        return PipelineLaunchResult(
            status_name=status_name,
            agent_sub_issues=agent_sub_issues,
            queued=True,
            queue_position=queue_position,
        )

    first_parallel_group = (
        agent_sub_issues
        and initial_groups
        and initial_groups[0].agents
        and initial_groups[0].execution_mode == "parallel"
        and len(initial_groups[0].agents) > 1
    )

    assigned_agents: list[str] = []
    initial_parallel_error: str | None = None
    if first_parallel_group:
        group = initial_groups[0]
        agent_indices: list[tuple[str, int]] = []
        for index, agent_slug in enumerate(group.agents):
            flat_index = initial_agents.index(agent_slug) if agent_slug in initial_agents else index
            agent_indices.append((agent_slug, flat_index))

        async def _assign_initial_parallel_agent(
            agent_slug: str, flat_index: int
        ) -> tuple[str, bool]:
            try:
                assigned = await orchestrator.assign_agent_for_status(
                    ctx, status_name, agent_index=flat_index
                )
                return agent_slug, bool(assigned)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception(
                    "Initial parallel assignment failed for agent '%s' on issue #%s",
                    agent_slug,
                    issue_number,
                )
                return agent_slug, False

        results = await asyncio.gather(
            *(
                _assign_initial_parallel_agent(agent_slug, flat_index)
                for agent_slug, flat_index in agent_indices
            )
        )

        failed_agents: list[str] = []
        for agent_slug, assigned in results:
            if assigned:
                assigned_agents.append(agent_slug)
                group.agent_statuses[agent_slug] = "active"
            else:
                failed_agents.append(agent_slug)
                group.agent_statuses[agent_slug] = "failed"

        for agent_slug in assigned_agents:
            try:
                await orchestrator._update_agent_tracking_state(ctx, agent_slug, "active")
            except Exception as e:
                logger.warning(
                    "Failed to reconcile tracking for initial parallel agent '%s' on issue #%s: %s",
                    agent_slug,
                    issue_number,
                    e,
                )

        if failed_agents:
            initial_parallel_error = (
                f"Failed to assign initial parallel agent '{failed_agents[0]}'"
                if len(failed_agents) == 1
                else "Failed to assign initial parallel agents: " + ", ".join(failed_agents)
            )
            logger.warning(
                "Initial parallel assignment had %d failed agent(s) on issue #%s: %s",
                len(failed_agents),
                issue_number,
                ", ".join(failed_agents),
            )

        pipeline = get_pipeline_state(issue_number)
        if pipeline:
            pipeline.started_at = utcnow()
            if pipeline.groups:
                first_group = pipeline.groups[0]
                for agent_slug in assigned_agents:
                    first_group.agent_statuses[agent_slug] = "active"
                for agent_slug in failed_agents:
                    first_group.agent_statuses[agent_slug] = "failed"
            for agent_slug in failed_agents:
                if agent_slug not in pipeline.failed_agents:
                    pipeline.failed_agents.append(agent_slug)
            pipeline.error = initial_parallel_error
            set_pipeline_state_impl(issue_number, pipeline)
    else:
        first_agent = initial_agents[0] if initial_agents else None
        success = await orchestrator.assign_agent_for_status(ctx, status_name, agent_index=0)
        if success and first_agent:
            assigned_agents.append(first_agent)

    from src.services.copilot_polling import ensure_app_pipeline_polling, ensure_polling_started
    from src.services.copilot_polling.state import register_project

    if use_app_scoped_polling:
        await ensure_app_pipeline_polling(
            access_token=ctx.access_token,
            project_id=ctx.project_id,
            owner=ctx.repository_owner,
            repo=ctx.repository_name,
            parent_issue_number=issue_number,
        )
    else:
        await ensure_polling_started(
            access_token=ctx.access_token,
            project_id=ctx.project_id,
            owner=ctx.repository_owner,
            repo=ctx.repository_name,
            caller=caller,
        )

    if register_project_monitoring:
        register_project(
            ctx.project_id,
            ctx.repository_owner,
            ctx.repository_name,
            ctx.access_token,
        )

    pipeline_error = initial_parallel_error
    pipeline = get_pipeline_state(issue_number)
    if pipeline and pipeline.error:
        pipeline_error = pipeline.error

    return PipelineLaunchResult(
        status_name=status_name,
        agent_sub_issues=agent_sub_issues,
        assigned_agents=assigned_agents,
        error=pipeline_error,
    )
