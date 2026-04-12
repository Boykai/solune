"""ProposalOrchestrator — extracted from the confirm_proposal() god function.

Each step of the proposal confirmation workflow is an independently testable
method.  The public entry point is :meth:`confirm`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.constants import GITHUB_ISSUE_BODY_MAX_LENGTH
from src.exceptions import NotFoundError, ValidationError
from src.logging_utils import get_logger, handle_service_error
from src.models.chat import ActionType, ChatMessage, SenderType
from src.models.recommendation import ProposalStatus
from src.models.workflow import WorkflowConfiguration
from src.services.cache import cache, get_project_items_cache_key
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

if TYPE_CHECKING:
    from src.models.recommendation import AITaskProposal, ProposalConfirmRequest
    from src.models.user import UserSession

logger = get_logger(__name__)


class ProposalOrchestrator:
    """Orchestrates the proposal confirmation workflow.

    Extracted from the monolithic ``confirm_proposal()`` endpoint so that
    each step is an independently testable method.
    """

    def __init__(self, chat_state_manager: Any, chat_store_module: Any) -> None:
        self._state = chat_state_manager
        self._chat_store = chat_store_module

    # ── Public entry point ───────────────────────────────────────────────

    async def confirm(
        self,
        proposal_id: str,
        request: ProposalConfirmRequest | None,
        session: UserSession,
        github_service: Any,
        connection_manager: Any,
    ) -> AITaskProposal:
        """Full confirmation flow.

        Raises NotFoundError, ValidationError (same as the original endpoint).
        """
        from src.api.chat.helpers import (
            _resolve_repository,
            _trigger_signal_delivery,
            add_message,
        )
        from src.dependencies import require_selected_project

        proposal = await self._validate_proposal(proposal_id, session)
        self._apply_edits(proposal, request)

        owner, repo = await _resolve_repository(session)
        project_id = require_selected_project(session)

        body = self._build_body(proposal)

        try:
            (
                issue_url,
                issue_number,
                issue_node_id,
                issue_database_id,
            ) = await self._create_github_issue(
                proposal, session, github_service, owner, repo, body
            )

            item_id = await self._add_to_project(
                issue_node_id, issue_database_id, session, github_service, project_id
            )

            await self._persist_status(proposal_id, proposal)

            cache.delete(get_project_items_cache_key(project_id))

            await self._broadcast_update(
                proposal, session, connection_manager, project_id, item_id, issue_number, issue_url
            )

            # Add confirmation message
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

            await self._setup_workflow(
                proposal,
                proposal_id,
                session,
                github_service,
                connection_manager,
                owner,
                repo,
                project_id,
                item_id,
                issue_node_id,
                issue_number,
            )

            return proposal

        except ValidationError:
            raise
        except Exception as e:
            handle_service_error(e, "create issue from proposal", ValidationError)

    # ── Private step methods ─────────────────────────────────────────────

    async def _validate_proposal(self, proposal_id: str, session: UserSession) -> AITaskProposal:
        """Retrieve and validate proposal ownership + expiration + status."""
        from src.api.chat.helpers import get_proposal

        proposal = await get_proposal(proposal_id)

        if not proposal:
            raise NotFoundError(f"Proposal not found: {proposal_id}")

        if str(proposal.session_id) != str(session.session_id):
            raise NotFoundError(f"Proposal not found: {proposal_id}")

        if proposal.is_expired:
            proposal.status = ProposalStatus.CANCELLED
            try:
                db = get_db()
                await self._chat_store.update_proposal_status(
                    db, proposal_id, ProposalStatus.CANCELLED.value
                )
            except Exception:
                logger.warning("Failed to update expired proposal status in SQLite", exc_info=True)
            raise ValidationError("Proposal has expired")

        if proposal.status != ProposalStatus.PENDING:
            raise ValidationError(f"Proposal already {proposal.status.value}")

        return proposal

    def _apply_edits(
        self, proposal: AITaskProposal, request: ProposalConfirmRequest | None
    ) -> None:
        """Apply user-provided title/description edits (mutates proposal in place)."""
        if not request:
            return
        if request.edited_title:
            proposal.edited_title = request.edited_title
            proposal.status = ProposalStatus.EDITED
        if request.edited_description:
            proposal.edited_description = request.edited_description
            if proposal.status != ProposalStatus.EDITED:
                proposal.status = ProposalStatus.EDITED

    def _build_body(self, proposal: AITaskProposal) -> str:
        """Build issue body with attachments and validate length."""
        from src.attachment_formatter import format_attachments_markdown

        body = proposal.final_description or ""
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
        return body

    async def _create_github_issue(
        self,
        proposal: AITaskProposal,
        session: UserSession,
        github_service: Any,
        owner: str,
        repo: str,
        body: str,
    ) -> tuple[str, int, str, int]:
        """Create a GitHub issue. Returns (issue_url, issue_number, issue_node_id, issue_database_id)."""
        issue = await github_service.create_issue(
            access_token=session.access_token,
            owner=owner,
            repo=repo,
            title=proposal.final_title,
            body=body,
            labels=[],
        )
        return (
            issue["html_url"],
            issue["number"],
            issue["node_id"],
            issue["id"],
        )

    async def _add_to_project(
        self,
        issue_node_id: str,
        issue_database_id: int,
        session: UserSession,
        github_service: Any,
        project_id: str,
    ) -> str:
        """Add the created issue to the project board. Returns the project item ID."""
        return await github_service.add_issue_to_project(
            access_token=session.access_token,
            project_id=project_id,
            issue_node_id=issue_node_id,
            issue_database_id=issue_database_id,
        )

    async def _persist_status(self, proposal_id: str, proposal: AITaskProposal) -> None:
        """Update proposal status to CONFIRMED in SQLite."""
        proposal.status = ProposalStatus.CONFIRMED
        try:
            db = get_db()
            await self._chat_store.update_proposal_status(
                db,
                proposal_id,
                ProposalStatus.CONFIRMED.value,
                edited_title=proposal.edited_title,
                edited_description=proposal.edited_description,
            )
        except Exception:
            logger.warning("Failed to update proposal status in SQLite", exc_info=True)

    async def _broadcast_update(
        self,
        proposal: AITaskProposal,
        session: UserSession,
        connection_manager: Any,
        project_id: str,
        item_id: str,
        issue_number: int,
        issue_url: str,
    ) -> None:
        """Send task_created WebSocket broadcast."""
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

    async def _setup_workflow(
        self,
        proposal: AITaskProposal,
        proposal_id: str,
        session: UserSession,
        github_service: Any,
        connection_manager: Any,
        owner: str,
        repo: str,
        project_id: str,
        item_id: str,
        issue_node_id: str,
        issue_number: int,
    ) -> None:
        """Set up workflow config, resolve pipeline, assign agent, start polling.

        Failures are logged but do not cause the endpoint to fail — the issue
        has already been created successfully at this point.
        """
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
                await set_workflow_config(project_id, config)
            else:
                config.repository_owner = owner
                config.repository_name = repo
                if not config.copilot_assignee:
                    config.copilot_assignee = settings.default_assignee

            # Resolve pipeline mappings
            pipeline_result = await self._resolve_pipeline(
                proposal, proposal_id, project_id, session.github_user_id
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

            # Set issue status to Backlog
            backlog_status = config.status_backlog
            await github_service.update_item_status_by_name(
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

            # Assign the first Backlog agent
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

            # Create all sub-issues upfront
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

            # Send agent_assigned WebSocket notification
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

            # Ensure Copilot polling is running
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

    async def _resolve_pipeline(
        self,
        proposal: AITaskProposal,
        proposal_id: str,
        project_id: str,
        github_user_id: str,
    ) -> Any:
        """Resolve pipeline mappings — selected pipeline or project/user/default fallback."""
        from src.services.workflow_orchestrator.config import (
            PipelineResolutionResult,
            load_pipeline_as_agent_mappings,
            resolve_project_pipeline_mappings,
        )

        if proposal.selected_pipeline_id:
            selected_pipeline = await load_pipeline_as_agent_mappings(
                project_id,
                proposal.selected_pipeline_id,
                github_user_id=github_user_id,
            )
            if selected_pipeline is not None:
                (
                    selected_mappings,
                    selected_pipeline_name,
                    selected_exec_modes,
                    selected_grp_mappings,
                ) = selected_pipeline
                return PipelineResolutionResult(
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
                return await resolve_project_pipeline_mappings(project_id, github_user_id)
        else:
            return await resolve_project_pipeline_mappings(project_id, github_user_id)
