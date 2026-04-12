"""ProposalOrchestrator — encapsulates the 7-phase proposal confirmation workflow.

Extracted from the ``confirm_proposal`` endpoint in ``api/chat.py`` to improve
modularity, testability, and separation of concerns.  All external dependencies
are constructor-injected.

Phases:
    1. Validate proposal (ownership, expiry, pending status)
    2. Apply user edits (title / description)
    3. Resolve repository (owner / repo / project_id, body-length guard)
    4. Create GitHub issue + add to project
    5. Broadcast confirmation (WebSocket + chat message)
    6. Configure workflow (load/create WorkflowConfiguration + pipeline mapping)
    7. Assign agent and start polling
"""

from __future__ import annotations

import asyncio
from types import ModuleType
from typing import TYPE_CHECKING, Any

from src.attachment_formatter import format_attachments_markdown
from src.constants import GITHUB_ISSUE_BODY_MAX_LENGTH
from src.exceptions import NotFoundError, ValidationError
from src.logging_utils import get_logger, handle_service_error
from src.models.chat import ActionType, ChatMessage, SenderType
from src.models.recommendation import (
    AITaskProposal,
    ProposalConfirmRequest,
    ProposalStatus,
)
from src.models.workflow import WorkflowConfiguration
from src.services.cache import (
    cache,
    get_project_items_cache_key,
)
from src.utils import resolve_repository, utcnow

if TYPE_CHECKING:
    from src.models.user import UserSession
    from src.services.chat_state_manager import ChatStateManager
    from src.services.github_projects import GitHubProjectsService
    from src.services.websocket import ConnectionManager

logger = get_logger(__name__)


class ProposalOrchestrator:
    """Orchestrates the 7-phase proposal-confirmation workflow.

    All external services are constructor-injected so the class is
    straightforward to test in isolation.
    """

    def __init__(
        self,
        github_service: GitHubProjectsService,
        connection_manager: ConnectionManager,
        chat_state_manager: ChatStateManager,
        chat_store: ModuleType,
        settings_store: ModuleType,
    ) -> None:
        self._github = github_service
        self._ws = connection_manager
        self._state = chat_state_manager
        self._chat_store = chat_store
        self._settings_store = settings_store

    # ── Public API ───────────────────────────────────────────────────

    async def confirm(
        self,
        proposal_id: str,
        request: ProposalConfirmRequest | None,
        session: UserSession,
    ) -> AITaskProposal:
        """Execute the full 7-phase proposal confirmation workflow."""
        # Phase 1 — validate
        proposal = await self._validate_proposal(proposal_id, session)

        # Phase 2 — apply user edits
        await self._apply_user_edits(proposal, request)

        # Phase 3 — resolve repository + body-length guard
        owner, repo, project_id = await self._resolve_repository(proposal, session)

        # Phase 4 — create GitHub issue
        try:
            issue_data = await self._create_github_issue(
                proposal, owner, repo, project_id, session
            )
        except ValidationError:
            raise
        except Exception as e:
            handle_service_error(e, "create issue from proposal", ValidationError)

        # Phase 5 — broadcast confirmation
        await self._broadcast_confirmation(
            proposal, session, project_id, issue_data
        )

        # Phases 6 & 7 — configure workflow + assign agent (best-effort)
        try:
            workflow_config = await self._configure_workflow(
                proposal, project_id, owner, repo, session
            )
            await self._assign_agent_and_start(
                proposal,
                workflow_config,
                owner,
                repo,
                session,
                project_id,
                issue_data,
            )
        except Exception as e:
            logger.warning(
                "Issue #%d created but agent assignment failed: %s",
                issue_data["issue_number"],
                e,
            )

        return proposal

    # ── Phase 1: Validate proposal ───────────────────────────────────

    async def _validate_proposal(
        self, proposal_id: str, session: UserSession
    ) -> AITaskProposal:
        """Verify ownership, expiry, and pending status."""
        proposal = await self._state.get_proposal(proposal_id)

        if not proposal:
            raise NotFoundError(f"Proposal not found: {proposal_id}")

        if str(proposal.session_id) != str(session.session_id):
            raise NotFoundError(f"Proposal not found: {proposal_id}")

        if proposal.is_expired:
            proposal.status = ProposalStatus.CANCELLED
            try:
                await self._chat_store.update_proposal_status(
                    self._state._db, proposal_id, ProposalStatus.CANCELLED.value
                )
            except Exception:
                logger.warning(
                    "Failed to update expired proposal status in SQLite",
                    exc_info=True,
                )
            raise ValidationError("Proposal has expired")

        if proposal.status != ProposalStatus.PENDING:
            raise ValidationError(f"Proposal already {proposal.status.value}")

        return proposal

    # ── Phase 2: Apply user edits ────────────────────────────────────

    async def _apply_user_edits(
        self,
        proposal: AITaskProposal,
        request: ProposalConfirmRequest | None,
    ) -> None:
        """Apply edited_title and edited_description if provided."""
        if not request:
            return
        if request.edited_title:
            proposal.edited_title = request.edited_title
            proposal.status = ProposalStatus.EDITED
        if request.edited_description:
            proposal.edited_description = request.edited_description
            if proposal.status != ProposalStatus.EDITED:
                proposal.status = ProposalStatus.EDITED

    # ── Phase 3: Resolve repository ──────────────────────────────────

    async def _resolve_repository(
        self,
        proposal: AITaskProposal,
        session: UserSession,
    ) -> tuple[str, str, str]:
        """Get owner/repo/project_id and validate body length."""
        from src.dependencies import require_selected_project

        owner, repo = await resolve_repository(
            session.access_token, session.selected_project_id
        )

        project_id = require_selected_project(session)

        # Validate description length before attempting issue creation
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

        return owner, repo, project_id

    # ── Phase 4: Create GitHub issue ─────────────────────────────────

    async def _create_github_issue(
        self,
        proposal: AITaskProposal,
        owner: str,
        repo: str,
        project_id: str,
        session: UserSession,
    ) -> dict[str, Any]:
        """Create issue via GitHub REST API and add to project.

        Returns a dict with ``issue_number``, ``issue_node_id``,
        ``issue_url``, ``issue_database_id``, and ``item_id``.
        """
        body = proposal.final_description or ""
        body += format_attachments_markdown(proposal.file_urls)

        # Step 1: Create GitHub issue
        issue = await self._github.create_issue(
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

        # Step 2: Add issue to project
        item_id = await self._github.add_issue_to_project(
            access_token=session.access_token,
            project_id=project_id,
            issue_node_id=issue_node_id,
            issue_database_id=issue_database_id,
        )

        # Mark proposal confirmed and persist
        proposal.status = ProposalStatus.CONFIRMED
        try:
            await self._chat_store.update_proposal_status(
                self._state._db,
                str(proposal.proposal_id),
                ProposalStatus.CONFIRMED.value,
                edited_title=proposal.edited_title,
                edited_description=proposal.edited_description,
            )
        except Exception:
            logger.warning(
                "Failed to update proposal status in SQLite", exc_info=True
            )

        # Invalidate cache
        cache.delete(get_project_items_cache_key(project_id))

        logger.info(
            "Created issue #%d from proposal %s: %s",
            issue_number,
            proposal.proposal_id,
            proposal.final_title,
        )

        return {
            "issue_number": issue_number,
            "issue_node_id": issue_node_id,
            "issue_url": issue_url,
            "issue_database_id": issue_database_id,
            "item_id": item_id,
        }

    # ── Phase 5: Broadcast confirmation ──────────────────────────────

    async def _broadcast_confirmation(
        self,
        proposal: AITaskProposal,
        session: UserSession,
        project_id: str,
        issue_data: dict[str, Any],
    ) -> None:
        """Send WebSocket broadcast and persist confirmation chat message."""
        item_id = issue_data["item_id"]
        issue_number = issue_data["issue_number"]
        issue_url = issue_data["issue_url"]

        await self._ws.broadcast_to_project(
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
            content=(
                f"✅ Issue created: **{proposal.final_title}** "
                f"([#{issue_number}]({issue_url}))"
            ),
            action_type=ActionType.TASK_CREATE,
            action_data={
                "proposal_id": str(proposal.proposal_id),
                "task_id": item_id,
                "issue_number": issue_number,
                "issue_url": issue_url,
                "status": ProposalStatus.CONFIRMED.value,
            },
        )
        await self._state.add_message(str(session.session_id), confirm_message)
        self._trigger_signal_delivery(session, confirm_message)

    # ── Phase 6: Configure workflow ──────────────────────────────────

    async def _configure_workflow(
        self,
        proposal: AITaskProposal,
        project_id: str,
        owner: str,
        repo: str,
        session: UserSession,
    ) -> WorkflowConfiguration:
        """Load or create WorkflowConfiguration and resolve pipeline mappings."""
        from src.config import get_settings
        from src.services.workflow_orchestrator import (
            get_workflow_config,
            set_workflow_config,
        )
        from src.services.workflow_orchestrator.config import (
            PipelineResolutionResult,
            load_pipeline_as_agent_mappings,
            resolve_project_pipeline_mappings,
        )

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
                    proposal.proposal_id,
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

        # Populate pipeline metadata on the proposal response
        proposal.pipeline_name = pipeline_result.pipeline_name
        proposal.pipeline_source = pipeline_result.source

        return config

    # ── Phase 7: Assign agent and start polling ──────────────────────

    async def _assign_agent_and_start(
        self,
        proposal: AITaskProposal,
        workflow_config: WorkflowConfiguration,
        owner: str,
        repo: str,
        session: UserSession,
        project_id: str,
        issue_data: dict[str, Any],
    ) -> None:
        """Assign the first agent, create sub-issues, and start Copilot polling."""
        from src.services.workflow_orchestrator import (
            PipelineState,
            WorkflowContext,
            get_agent_slugs,
            get_workflow_orchestrator,
            set_pipeline_state,
        )

        issue_number = issue_data["issue_number"]
        issue_node_id = issue_data["issue_node_id"]
        item_id = issue_data["item_id"]
        backlog_status = workflow_config.status_backlog

        # Set issue status to Backlog on the project
        await self._github.update_item_status_by_name(
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

        # Resolve user settings for agent model configuration
        try:
            effective_user_settings = await self._settings_store.get_effective_user_settings(
                self._state._db, session.github_user_id
            )
            user_chat_model = effective_user_settings.ai.model
            user_agent_model = effective_user_settings.ai.agent_model
            user_reasoning_effort = effective_user_settings.ai.reasoning_effort
        except Exception:
            logger.warning(
                "Could not load effective user settings for session %s; "
                "user_chat_model left empty",
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
            config=workflow_config,
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
            initial_agents = get_agent_slugs(workflow_config, backlog_status)
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
        backlog_slugs = get_agent_slugs(workflow_config, backlog_status)
        if backlog_slugs:
            await self._ws.broadcast_to_project(
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

    # ── Internal helpers ─────────────────────────────────────────────

    @staticmethod
    def _trigger_signal_delivery(
        session: UserSession,
        message: ChatMessage,
        project_name: str | None = None,
    ) -> None:
        """Fire-and-forget Signal delivery for system messages."""
        if message.sender_type == SenderType.USER:
            return

        async def _deliver() -> None:
            try:
                from src.services.signal_delivery import deliver_chat_message_via_signal

                await deliver_chat_message_via_signal(
                    github_user_id=session.github_user_id,
                    message=message,
                    project_name=project_name,
                    project_id=session.selected_project_id,
                )
            except Exception as e:
                logger.debug("Signal delivery trigger failed (non-fatal): %s", e)

        try:
            from src.services.task_registry import task_registry

            task_registry.create_task(_deliver(), name="signal-delivery")
        except RuntimeError:
            pass  # No running event loop — skip silently
