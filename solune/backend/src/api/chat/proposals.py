"""Proposal and recommendation state + confirm/cancel routes."""

from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends

from src.api.auth import get_session_dep
from src.constants import GITHUB_ISSUE_BODY_MAX_LENGTH
from src.dependencies import get_connection_manager, get_github_service, require_selected_project
from src.exceptions import NotFoundError, ValidationError
from src.logging_utils import get_logger, handle_service_error
from src.models.chat import (
    ActionType,
    ChatMessage,
    SenderType,
)
from src.models.recommendation import (
    AITaskProposal,
    IssueRecommendation,
    ProposalConfirmRequest,
    ProposalStatus,
    RecommendationStatus,
)
from src.models.user import UserSession
from src.models.workflow import WorkflowConfiguration
from src.services.cache import (
    cache,
    get_project_items_cache_key,
)
from src.services.database import get_db
from src.services.settings_store import get_effective_user_settings
from src.services.workflow_orchestrator import (
    WorkflowContext,
    get_agent_slugs,
    get_workflow_config,
    get_workflow_orchestrator,
    set_workflow_config,
)
from src.utils import utcnow

logger = get_logger(__name__)
router = APIRouter()

# ── Proposal / recommendation in-memory caches (SQLite-backed) ───────────

_proposals: dict[str, AITaskProposal] = {}
_recommendations: dict[str, IssueRecommendation] = {}

_PERSIST_MAX_RETRIES = 3
_PERSIST_BASE_DELAY = 0.1


async def _persist_proposal(proposal: AITaskProposal) -> None:
    """Persist a proposal to SQLite with retry."""
    from src.services import chat_store

    from src.api.chat.messages import _retry_persist

    db = get_db()
    await _retry_persist(
        chat_store.save_proposal,
        db,
        session_id=str(proposal.session_id),
        proposal_id=str(proposal.proposal_id),
        original_input=proposal.original_input,
        proposed_title=proposal.proposed_title,
        proposed_description=proposal.proposed_description,
        status=proposal.status.value,
        edited_title=proposal.edited_title,
        edited_description=proposal.edited_description,
        created_at=proposal.created_at.isoformat(),
        expires_at=proposal.expires_at.isoformat(),
        file_urls=proposal.file_urls or None,
        selected_pipeline_id=proposal.selected_pipeline_id,
        context=f"proposal:{proposal.proposal_id}",
    )


async def _persist_recommendation(recommendation: IssueRecommendation) -> None:
    """Persist a recommendation to SQLite with retry."""
    from src.services import chat_store

    from src.api.chat.messages import _retry_persist

    db = get_db()
    await _retry_persist(
        chat_store.save_recommendation,
        db,
        session_id=str(recommendation.session_id),
        recommendation_id=str(recommendation.recommendation_id),
        data=json.dumps(recommendation.model_dump(mode="json")),
        status=recommendation.status.value,
        file_urls=recommendation.file_urls or None,
        context=f"recommendation:{recommendation.recommendation_id}",
    )


async def store_proposal(proposal: AITaskProposal) -> None:
    """Persist a proposal to SQLite, then update cache."""
    await _persist_proposal(proposal)
    _proposals[str(proposal.proposal_id)] = proposal


async def store_recommendation(recommendation: IssueRecommendation) -> None:
    """Persist a recommendation to SQLite, then update cache."""
    await _persist_recommendation(recommendation)
    _recommendations[str(recommendation.recommendation_id)] = recommendation


async def get_proposal(proposal_id: str) -> AITaskProposal | None:
    """Get a proposal by ID from cache or SQLite."""
    proposal = _proposals.get(proposal_id)
    if proposal is not None:
        return proposal

    try:
        from src.services import chat_store

        db = get_db()
        row = await chat_store.get_proposal_by_id(db, proposal_id)
        if row is None:
            return None
        from datetime import datetime as _dt

        raw_expires = row["expires_at"] or _default_expires_at(row["created_at"])
        parsed_expires = (
            _dt.fromisoformat(raw_expires) if isinstance(raw_expires, str) else raw_expires
        )

        proposal = AITaskProposal(
            proposal_id=row["proposal_id"],
            session_id=row["session_id"],
            original_input=row["original_input"],
            proposed_title=row["proposed_title"],
            proposed_description=row["proposed_description"],
            status=ProposalStatus(row["status"]),
            edited_title=row.get("edited_title"),
            edited_description=row.get("edited_description"),
            file_urls=row.get("file_urls", []),
            selected_pipeline_id=row.get("selected_pipeline_id"),
            created_at=row["created_at"],
            expires_at=parsed_expires,
        )
        _proposals[proposal_id] = proposal
        return proposal
    except Exception:
        logger.warning("Failed to load proposal from SQLite", exc_info=True)
        return None


async def get_recommendation(recommendation_id: str) -> IssueRecommendation | None:
    """Get a recommendation by ID from cache or SQLite."""
    rec = _recommendations.get(recommendation_id)
    if rec is not None:
        return rec

    try:
        from src.services import chat_store

        db = get_db()
        row = await chat_store.get_recommendation_by_id(db, recommendation_id)
        if row is None:
            return None
        data = json.loads(row["data"]) if isinstance(row["data"], str) else row["data"]
        rec = IssueRecommendation.model_validate(data)
        rec.status = RecommendationStatus(chat_store.recommendation_status_from_db(row["status"]))
        _recommendations[str(rec.recommendation_id)] = rec
        return rec
    except Exception:
        logger.warning("Failed to load recommendation from SQLite", exc_info=True)
        return None


def _default_expires_at(created_at_str: str) -> str:
    """Compute a fallback expires_at when the stored value is NULL."""
    from datetime import datetime, timedelta

    try:
        created = datetime.fromisoformat(created_at_str)
        return (created + timedelta(minutes=10)).isoformat()
    except (ValueError, TypeError):
        return created_at_str


# ── Confirm / Cancel routes ──────────────────────────────────────────────


@router.post("/proposals/{proposal_id}/confirm", response_model=AITaskProposal)
async def confirm_proposal(
    proposal_id: str,
    request: ProposalConfirmRequest | None,
    session: Annotated[UserSession, Depends(get_session_dep)],
    github_projects_service=Depends(get_github_service),  # noqa: B008
    connection_manager=Depends(get_connection_manager),  # noqa: B008
) -> AITaskProposal:
    """Confirm an AI task proposal and create the task."""
    # Lazy imports to break circular dependency with messages.py
    from src.api.chat.messages import _resolve_repository, _trigger_signal_delivery, add_message

    proposal = await get_proposal(proposal_id)

    if not proposal:
        raise NotFoundError(f"Proposal not found: {proposal_id}")

    if str(proposal.session_id) != str(session.session_id):
        raise NotFoundError(f"Proposal not found: {proposal_id}")

    if proposal.is_expired:
        proposal.status = ProposalStatus.CANCELLED
        try:
            from src.services import chat_store

            db = get_db()
            await chat_store.update_proposal_status(db, proposal_id, ProposalStatus.CANCELLED.value)
        except Exception:
            logger.warning("Failed to update expired proposal status in SQLite", exc_info=True)
        raise ValidationError("Proposal has expired")

    if proposal.status != ProposalStatus.PENDING:
        raise ValidationError(f"Proposal already {proposal.status.value}")

    # Apply edits if provided
    if request:
        if request.edited_title:
            proposal.edited_title = request.edited_title
            proposal.status = ProposalStatus.EDITED
        if request.edited_description:
            proposal.edited_description = request.edited_description
            if proposal.status != ProposalStatus.EDITED:
                proposal.status = ProposalStatus.EDITED

    # Resolve repository info for issue creation
    owner, repo = await _resolve_repository(session)

    project_id = require_selected_project(session)

    # Validate description does not exceed GitHub API limit before attempting
    # issue creation.
    body = proposal.final_description or ""

    from src.attachment_formatter import format_attachments_markdown

    body += format_attachments_markdown(proposal.file_urls)

    if len(body) > GITHUB_ISSUE_BODY_MAX_LENGTH:
        raise ValidationError(
            f"Issue body is {len(body)} characters, which exceeds the "
            f"GitHub API limit of {GITHUB_ISSUE_BODY_MAX_LENGTH} characters. "
            "Please shorten the description.",
            details={
                "body_length": len(body),
                "max_length": GITHUB_ISSUE_BODY_MAX_LENGTH,
            },
        )

    # Create the issue in GitHub
    try:
        issue = await github_projects_service.create_issue(
            access_token=session.access_token,
            owner=owner,
            repo=repo,
            title=proposal.final_title,
            body=body,
            labels=[],
        )

        issue_number = issue["number"]
        issue_node_id = issue["node_id"]
        issue_url = issue["html_url"]
        issue_database_id = issue["id"]

        item_id = await github_projects_service.add_issue_to_project(
            access_token=session.access_token,
            project_id=project_id,
            issue_node_id=issue_node_id,
            issue_database_id=issue_database_id,
        )

        proposal.status = ProposalStatus.CONFIRMED
        try:
            from src.services import chat_store

            db = get_db()
            await chat_store.update_proposal_status(
                db,
                proposal_id,
                ProposalStatus.CONFIRMED.value,
                edited_title=proposal.edited_title,
                edited_description=proposal.edited_description,
            )
        except Exception:
            logger.warning("Failed to update proposal status in SQLite", exc_info=True)

        cache.delete(get_project_items_cache_key(project_id))

        await connection_manager.broadcast_to_project(
            project_id,
            {
                "type": "task_created",
                "task_id": item_id,
                "title": proposal.final_title,
                "issue_number": issue_number,
                "issue_url": issue_url,
            },
        )

        confirm_message = ChatMessage(
            session_id=session.session_id,
            sender_type=SenderType.SYSTEM,
            content=f"✅ Issue created: **{proposal.final_title}** ([#{issue_number}]({issue_url}))",
            action_type=ActionType.TASK_CREATE,
            action_data={
                "proposal_id": str(proposal.proposal_id),
                "task_id": item_id,
                "issue_number": issue_number,
                "issue_url": issue_url,
                "status": ProposalStatus.CONFIRMED.value,
            },
        )
        await add_message(session.session_id, confirm_message)
        _trigger_signal_delivery(session, confirm_message)

        logger.info(
            "Created issue #%d from proposal %s: %s",
            issue_number,
            proposal_id,
            proposal.final_title,
        )

        # Step 3: Set up workflow config and assign agent for Backlog status
        try:
            from src.config import get_settings

            settings = get_settings()

            config = await get_workflow_config(project_id)
            if not config:
                config = WorkflowConfiguration(
                    project_id=project_id,
                    repository_owner=owner,
                    repository_name=repo,
                    copilot_assignee=settings.default_assignee,
                )
                await set_workflow_config(
                    project_id,
                    config,
                )
            else:
                config.repository_owner = owner
                config.repository_name = repo
                if not config.copilot_assignee:
                    config.copilot_assignee = settings.default_assignee

            from src.services.workflow_orchestrator.config import (
                PipelineResolutionResult,
                load_pipeline_as_agent_mappings,
                resolve_project_pipeline_mappings,
            )

            if proposal.selected_pipeline_id:
                selected_pipeline = await load_pipeline_as_agent_mappings(
                    project_id,
                    proposal.selected_pipeline_id,
                    github_user_id=session.github_user_id,
                )
                if selected_pipeline is not None:
                    (
                        selected_mappings,
                        selected_pipeline_name,
                        selected_exec_modes,
                        selected_grp_mappings,
                    ) = selected_pipeline
                    pipeline_result = PipelineResolutionResult(
                        agent_mappings=selected_mappings,
                        source="pipeline",
                        pipeline_name=selected_pipeline_name,
                        pipeline_id=proposal.selected_pipeline_id,
                        stage_execution_modes=selected_exec_modes,
                        group_mappings=selected_grp_mappings,
                    )
                else:
                    logger.warning(
                        "Selected pipeline %s not found for proposal %s on project %s; falling back",
                        proposal.selected_pipeline_id,
                        proposal_id,
                        project_id,
                    )
                    pipeline_result = await resolve_project_pipeline_mappings(
                        project_id, session.github_user_id
                    )
            else:
                pipeline_result = await resolve_project_pipeline_mappings(
                    project_id, session.github_user_id
                )

            if pipeline_result.agent_mappings:
                logger.info(
                    "Applying %s agent pipeline mappings for project=%s (pipeline=%s)",
                    pipeline_result.source,
                    project_id,
                    pipeline_result.pipeline_name or "N/A",
                )
                config.agent_mappings = pipeline_result.agent_mappings
                await set_workflow_config(project_id, config)

            proposal.pipeline_name = pipeline_result.pipeline_name
            proposal.pipeline_source = pipeline_result.source

            backlog_status = config.status_backlog
            await github_projects_service.update_item_status_by_name(
                access_token=session.access_token,
                project_id=project_id,
                item_id=item_id,
                status_name=backlog_status,
            )
            logger.info(
                "Set issue #%d status to '%s' on project",
                issue_number,
                backlog_status,
            )

            try:
                effective_user_settings = await get_effective_user_settings(
                    get_db(), session.github_user_id
                )
                user_chat_model = effective_user_settings.ai.model
                user_agent_model = effective_user_settings.ai.agent_model
                user_reasoning_effort = effective_user_settings.ai.reasoning_effort
            except Exception:
                logger.warning(
                    "Could not load effective user settings for session %s; user_chat_model left empty",
                    session.session_id,
                )
                user_chat_model = ""
                user_agent_model = ""
                user_reasoning_effort = ""

            ctx = WorkflowContext(
                session_id=str(session.session_id),
                project_id=project_id,
                access_token=session.access_token,
                repository_owner=owner,
                repository_name=repo,
                selected_pipeline_id=proposal.selected_pipeline_id,
                config=config,
                user_chat_model=user_chat_model,
                user_agent_model=user_agent_model,
                user_reasoning_effort=user_reasoning_effort,
            )
            ctx.issue_id = issue_node_id
            ctx.issue_number = issue_number
            ctx.project_item_id = item_id

            orchestrator = get_workflow_orchestrator()

            agent_sub_issues = await orchestrator.create_all_sub_issues(ctx)
            if agent_sub_issues:
                from src.services.workflow_orchestrator import (
                    PipelineState,
                    set_pipeline_state,
                )

                initial_agents = get_agent_slugs(config, backlog_status)
                pipeline_state = PipelineState(
                    issue_number=issue_number,
                    project_id=project_id,
                    status=backlog_status,
                    agents=initial_agents,
                    agent_sub_issues=agent_sub_issues,
                    started_at=utcnow(),
                )
                set_pipeline_state(issue_number, pipeline_state)
                logger.info(
                    "Pre-created %d sub-issues for issue #%d",
                    len(agent_sub_issues),
                    issue_number,
                )

            await orchestrator.assign_agent_for_status(ctx, backlog_status, agent_index=0)

            backlog_slugs = get_agent_slugs(config, backlog_status)
            if backlog_slugs:
                await connection_manager.broadcast_to_project(
                    project_id,
                    {
                        "type": "agent_assigned",
                        "issue_number": issue_number,
                        "agent_name": backlog_slugs[0],
                        "status": backlog_status,
                    },
                )

            from src.services.copilot_polling import ensure_polling_started

            await ensure_polling_started(
                access_token=session.access_token,
                project_id=project_id,
                owner=owner,
                repo=repo,
                caller="confirm_proposal",
            )

        except Exception as e:
            logger.warning(
                "Issue #%d created but agent assignment failed: %s",
                issue_number,
                e,
            )

        return proposal

    except ValidationError:
        raise
    except Exception as e:
        handle_service_error(e, "create issue from proposal", ValidationError)


@router.delete("/proposals/{proposal_id}")
async def cancel_proposal(
    proposal_id: str,
    session: Annotated[UserSession, Depends(get_session_dep)],
) -> dict:
    """Cancel an AI task proposal."""
    from src.api.chat.messages import add_message

    proposal = await get_proposal(proposal_id)

    if not proposal:
        raise NotFoundError(f"Proposal not found: {proposal_id}")

    if str(proposal.session_id) != str(session.session_id):
        raise NotFoundError(f"Proposal not found: {proposal_id}")

    proposal.status = ProposalStatus.CANCELLED
    try:
        from src.services import chat_store

        db = get_db()
        await chat_store.update_proposal_status(db, proposal_id, ProposalStatus.CANCELLED.value)
    except Exception:
        logger.warning("Failed to update proposal status in SQLite", exc_info=True)

    cancel_message = ChatMessage(
        session_id=session.session_id,
        sender_type=SenderType.SYSTEM,
        content="Task creation cancelled.",
    )
    await add_message(session.session_id, cancel_message)

    return {"message": "Proposal cancelled"}
