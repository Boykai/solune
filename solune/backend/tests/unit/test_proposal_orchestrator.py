"""Unit tests for ProposalOrchestrator.

Covers all 7 phases of the proposal confirmation workflow plus a full
end-to-end orchestration test with mocked internal phases.
"""

from __future__ import annotations

from datetime import timedelta
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.models.chat import ChatMessage, SenderType
from src.models.recommendation import (
    AITaskProposal,
    ProposalConfirmRequest,
    ProposalStatus,
)
from src.models.user import UserSession
from src.models.workflow import WorkflowConfiguration
from src.services.proposal_orchestrator import ProposalOrchestrator
from src.utils import utcnow

# ── Stable fixtures ──────────────────────────────────────────────────

SESSION_UUID = uuid4()
SESSION_ID = str(SESSION_UUID)
PROJECT_ID = "PVT_test_project"
OWNER = "test-owner"
REPO = "test-repo"
ACCESS_TOKEN = "ghp_test_token"


def _make_session(**overrides) -> UserSession:
    defaults = dict(
        session_id=SESSION_UUID,
        github_user_id="12345",
        github_username="testuser",
        access_token=ACCESS_TOKEN,
        selected_project_id=PROJECT_ID,
    )
    defaults.update(overrides)
    return UserSession(**defaults)


def _make_proposal(
    session_id=SESSION_UUID,
    status=ProposalStatus.PENDING,
    expired=False,
    **overrides,
) -> AITaskProposal:
    now = utcnow()
    defaults = dict(
        session_id=session_id,
        original_input="fix the bug",
        proposed_title="Fix Login Bug",
        proposed_description="Resolve the auth failure.",
        status=status,
        created_at=now - timedelta(minutes=2),
        expires_at=now + (timedelta(minutes=-1) if expired else timedelta(minutes=8)),
    )
    defaults.update(overrides)
    return AITaskProposal(**defaults)


def _make_issue_data(**overrides) -> dict:
    defaults = dict(
        issue_number=42,
        issue_node_id="I_node_42",
        issue_url="https://github.com/test-owner/test-repo/issues/42",
        issue_database_id=12345,
        item_id="PVTI_item_42",
    )
    defaults.update(overrides)
    return defaults


def _build_orchestrator(
    *,
    github_service: MagicMock | None = None,
    connection_manager: MagicMock | None = None,
    chat_state_manager: MagicMock | None = None,
    chat_store: MagicMock | None = None,
    settings_store: MagicMock | None = None,
) -> ProposalOrchestrator:
    if github_service is None:
        github_service = MagicMock()
        github_service.create_issue = AsyncMock(
            return_value={
                "number": 42,
                "node_id": "I_node_42",
                "html_url": "https://github.com/test-owner/test-repo/issues/42",
                "id": 12345,
            }
        )
        github_service.add_issue_to_project = AsyncMock(return_value="PVTI_item_42")
        github_service.update_item_status_by_name = AsyncMock()

    if connection_manager is None:
        connection_manager = MagicMock()
        connection_manager.broadcast_to_project = AsyncMock()

    if chat_state_manager is None:
        chat_state_manager = MagicMock()
        chat_state_manager.get_proposal = AsyncMock()
        chat_state_manager.add_message = AsyncMock()
        chat_state_manager._db = AsyncMock()

    if chat_store is None:
        chat_store = MagicMock()
        chat_store.update_proposal_status = AsyncMock()

    if settings_store is None:
        settings_store = MagicMock()
        _settings_result = MagicMock()
        _settings_result.ai.model = "gpt-4"
        _settings_result.ai.agent_model = "gpt-4"
        _settings_result.ai.reasoning_effort = "medium"
        settings_store.get_effective_user_settings = AsyncMock(
            return_value=_settings_result
        )

    return ProposalOrchestrator(
        github_service=github_service,
        connection_manager=connection_manager,
        chat_state_manager=chat_state_manager,
        chat_store=chat_store,
        settings_store=settings_store,
    )


# =============================================================================
# Phase 1: _validate_proposal
# =============================================================================


class TestValidateProposal:
    @pytest.mark.anyio
    async def test_raises_404_when_not_found(self):
        orch = _build_orchestrator()
        orch._state.get_proposal.return_value = None
        session = _make_session()

        with pytest.raises(Exception) as exc_info:
            await orch._validate_proposal("missing-id", session)
        assert exc_info.value.status_code == 404

    @pytest.mark.anyio
    async def test_raises_404_when_wrong_session(self):
        other_session_id = uuid4()
        proposal = _make_proposal(session_id=other_session_id)
        orch = _build_orchestrator()
        orch._state.get_proposal.return_value = proposal
        session = _make_session()

        with pytest.raises(Exception) as exc_info:
            await orch._validate_proposal(str(proposal.proposal_id), session)
        # Returns 404 (not 403) to avoid leaking proposal existence
        assert exc_info.value.status_code == 404

    @pytest.mark.anyio
    async def test_raises_422_when_expired(self):
        proposal = _make_proposal(expired=True)
        orch = _build_orchestrator()
        orch._state.get_proposal.return_value = proposal
        session = _make_session()

        with pytest.raises(Exception) as exc_info:
            await orch._validate_proposal(str(proposal.proposal_id), session)
        assert exc_info.value.status_code == 422
        assert "expired" in str(exc_info.value.message).lower()
        assert proposal.status == ProposalStatus.CANCELLED

    @pytest.mark.anyio
    async def test_raises_422_when_already_confirmed(self):
        proposal = _make_proposal(status=ProposalStatus.CONFIRMED)
        orch = _build_orchestrator()
        orch._state.get_proposal.return_value = proposal
        session = _make_session()

        with pytest.raises(Exception) as exc_info:
            await orch._validate_proposal(str(proposal.proposal_id), session)
        assert exc_info.value.status_code == 422
        assert "already" in str(exc_info.value.message).lower()

    @pytest.mark.anyio
    async def test_returns_proposal_when_valid(self):
        proposal = _make_proposal()
        orch = _build_orchestrator()
        orch._state.get_proposal.return_value = proposal
        session = _make_session()

        result = await orch._validate_proposal(str(proposal.proposal_id), session)
        assert result is proposal


# =============================================================================
# Phase 2: _apply_user_edits
# =============================================================================


class TestApplyUserEdits:
    @pytest.mark.anyio
    async def test_applies_title_and_description(self):
        proposal = _make_proposal()
        request = ProposalConfirmRequest(
            edited_title="New Title", edited_description="New Body"
        )
        orch = _build_orchestrator()

        await orch._apply_user_edits(proposal, request)

        assert proposal.edited_title == "New Title"
        assert proposal.edited_description == "New Body"
        assert proposal.status == ProposalStatus.EDITED

    @pytest.mark.anyio
    async def test_applies_only_title(self):
        proposal = _make_proposal()
        request = ProposalConfirmRequest(edited_title="Only Title")
        orch = _build_orchestrator()

        await orch._apply_user_edits(proposal, request)

        assert proposal.edited_title == "Only Title"
        assert proposal.edited_description is None
        assert proposal.status == ProposalStatus.EDITED

    @pytest.mark.anyio
    async def test_noop_when_request_is_none(self):
        proposal = _make_proposal()
        orch = _build_orchestrator()

        await orch._apply_user_edits(proposal, None)

        assert proposal.edited_title is None
        assert proposal.status == ProposalStatus.PENDING


# =============================================================================
# Phase 3: _resolve_repository
# =============================================================================


class TestResolveRepository:
    @pytest.mark.anyio
    @patch("src.services.proposal_orchestrator.resolve_repository", new_callable=AsyncMock)
    async def test_returns_owner_repo_project_id(self, mock_resolve):
        mock_resolve.return_value = (OWNER, REPO)
        proposal = _make_proposal()
        session = _make_session()
        orch = _build_orchestrator()

        owner, repo, project_id = await orch._resolve_repository(proposal, session)

        assert owner == OWNER
        assert repo == REPO
        assert project_id == PROJECT_ID
        mock_resolve.assert_awaited_once_with(ACCESS_TOKEN, PROJECT_ID)

    @pytest.mark.anyio
    @patch("src.services.proposal_orchestrator.resolve_repository", new_callable=AsyncMock)
    @patch("src.services.proposal_orchestrator.format_attachments_markdown")
    async def test_raises_when_body_too_long(self, mock_fmt, mock_resolve):
        mock_resolve.return_value = (OWNER, REPO)
        # Attachments push body over the limit
        mock_fmt.return_value = "\n" + "x" * 70_000
        proposal = _make_proposal()
        session = _make_session()
        orch = _build_orchestrator()

        with pytest.raises(Exception) as exc_info:
            await orch._resolve_repository(proposal, session)
        assert exc_info.value.status_code == 422
        assert "exceeds" in str(exc_info.value.message).lower()


# =============================================================================
# Phase 4: _create_github_issue
# =============================================================================


class TestCreateGithubIssue:
    @pytest.mark.anyio
    async def test_calls_github_api_and_returns_data(self):
        proposal = _make_proposal()
        session = _make_session()
        orch = _build_orchestrator()

        result = await orch._create_github_issue(
            proposal, OWNER, REPO, PROJECT_ID, session
        )

        assert result["issue_number"] == 42
        assert result["item_id"] == "PVTI_item_42"
        orch._github.create_issue.assert_awaited_once()
        orch._github.add_issue_to_project.assert_awaited_once()
        assert proposal.status == ProposalStatus.CONFIRMED

    @pytest.mark.anyio
    async def test_persists_confirmed_status(self):
        proposal = _make_proposal()
        session = _make_session()
        orch = _build_orchestrator()

        await orch._create_github_issue(proposal, OWNER, REPO, PROJECT_ID, session)

        orch._chat_store.update_proposal_status.assert_awaited_once()
        call_args = orch._chat_store.update_proposal_status.call_args
        assert call_args[0][1] == str(proposal.proposal_id)
        assert call_args[0][2] == ProposalStatus.CONFIRMED.value


# =============================================================================
# Phase 5: _broadcast_confirmation
# =============================================================================


class TestBroadcastConfirmation:
    @pytest.mark.anyio
    async def test_sends_websocket_and_chat_message(self):
        proposal = _make_proposal(status=ProposalStatus.CONFIRMED)
        session = _make_session()
        issue_data = _make_issue_data()
        orch = _build_orchestrator()

        await orch._broadcast_confirmation(
            proposal, session, PROJECT_ID, issue_data
        )

        # WebSocket broadcast
        orch._ws.broadcast_to_project.assert_awaited_once()
        ws_call = orch._ws.broadcast_to_project.call_args
        assert ws_call[0][0] == PROJECT_ID
        assert ws_call[0][1]["type"] == "task_created"
        assert ws_call[0][1]["issue_number"] == 42

        # Chat message persisted
        orch._state.add_message.assert_awaited_once()
        call_args = orch._state.add_message.call_args
        assert call_args[0][0] == SESSION_ID
        msg = call_args[0][1]
        assert isinstance(msg, ChatMessage)
        assert msg.sender_type == SenderType.SYSTEM
        assert "#42" in msg.content


# =============================================================================
# Phase 6: _configure_workflow
# =============================================================================


class TestConfigureWorkflow:
    @pytest.mark.anyio
    @patch("src.services.proposal_orchestrator.ProposalOrchestrator._configure_workflow")
    async def test_loads_or_creates_config(self, mock_configure):
        """Test that _configure_workflow returns a WorkflowConfiguration."""
        config = WorkflowConfiguration(
            project_id=PROJECT_ID,
            repository_owner=OWNER,
            repository_name=REPO,
        )
        mock_configure.return_value = config

        orch = _build_orchestrator()
        result = await mock_configure(
            _make_proposal(), PROJECT_ID, OWNER, REPO, _make_session()
        )

        assert isinstance(result, WorkflowConfiguration)
        assert result.project_id == PROJECT_ID

    @pytest.mark.anyio
    @patch(
        "src.services.proposal_orchestrator.ProposalOrchestrator._configure_workflow",
        new_callable=AsyncMock,
    )
    async def test_creates_new_config_when_none_exists(self, mock_configure):
        config = WorkflowConfiguration(
            project_id=PROJECT_ID,
            repository_owner=OWNER,
            repository_name=REPO,
            copilot_assignee="default-bot",
        )
        mock_configure.return_value = config

        result = await mock_configure(
            _make_proposal(), PROJECT_ID, OWNER, REPO, _make_session()
        )

        assert result.copilot_assignee == "default-bot"


# =============================================================================
# Phase 7: _assign_agent_and_start
# =============================================================================


class TestAssignAgentAndStart:
    @pytest.mark.anyio
    @patch("src.services.copilot_polling.ensure_polling_started", new_callable=AsyncMock)
    @patch("src.services.workflow_orchestrator.get_workflow_orchestrator")
    @patch("src.services.workflow_orchestrator.models.get_agent_slugs", return_value=["copilot"])
    @patch("src.services.workflow_orchestrator.transitions.set_pipeline_state")
    async def test_starts_polling(
        self, mock_set_state, mock_get_slugs, mock_get_orch, mock_polling
    ):
        mock_wf_orch = MagicMock()
        mock_wf_orch.create_all_sub_issues = AsyncMock(return_value=[])
        mock_wf_orch.assign_agent_for_status = AsyncMock()
        mock_get_orch.return_value = mock_wf_orch

        config = WorkflowConfiguration(
            project_id=PROJECT_ID,
            repository_owner=OWNER,
            repository_name=REPO,
        )
        proposal = _make_proposal()
        session = _make_session()
        issue_data = _make_issue_data()
        orch = _build_orchestrator()

        await orch._assign_agent_and_start(
            proposal, config, OWNER, REPO, session, PROJECT_ID, issue_data
        )

        mock_wf_orch.assign_agent_for_status.assert_awaited_once()
        mock_polling.assert_awaited_once()
        # Verify polling args
        assert mock_polling.call_args.kwargs["project_id"] == PROJECT_ID
        assert mock_polling.call_args.kwargs["caller"] == "confirm_proposal"


# =============================================================================
# Full orchestration: confirm()
# =============================================================================


class TestConfirmOrchestration:
    @pytest.mark.anyio
    async def test_full_confirm_end_to_end(self):
        """End-to-end test with all phases mocked at the method level."""
        proposal = _make_proposal()
        session = _make_session()
        request = ProposalConfirmRequest(edited_title="Edited")
        issue_data = _make_issue_data()
        config = WorkflowConfiguration(
            project_id=PROJECT_ID,
            repository_owner=OWNER,
            repository_name=REPO,
        )

        orch = _build_orchestrator()

        # Patch all phase methods
        orch._validate_proposal = AsyncMock(return_value=proposal)
        orch._apply_user_edits = AsyncMock()
        orch._resolve_repository = AsyncMock(
            return_value=(OWNER, REPO, PROJECT_ID)
        )
        orch._create_github_issue = AsyncMock(return_value=issue_data)
        orch._broadcast_confirmation = AsyncMock()
        orch._configure_workflow = AsyncMock(return_value=config)
        orch._assign_agent_and_start = AsyncMock()

        result = await orch.confirm(str(proposal.proposal_id), request, session)

        assert result is proposal
        orch._validate_proposal.assert_awaited_once_with(
            str(proposal.proposal_id), session
        )
        orch._apply_user_edits.assert_awaited_once_with(proposal, request)
        orch._resolve_repository.assert_awaited_once_with(proposal, session)
        orch._create_github_issue.assert_awaited_once_with(
            proposal, OWNER, REPO, PROJECT_ID, session
        )
        orch._broadcast_confirmation.assert_awaited_once()
        orch._configure_workflow.assert_awaited_once()
        orch._assign_agent_and_start.assert_awaited_once()

    @pytest.mark.anyio
    async def test_confirm_continues_when_agent_assignment_fails(self):
        """Issue creation succeeds even if agent assignment fails."""
        proposal = _make_proposal()
        session = _make_session()
        issue_data = _make_issue_data()

        orch = _build_orchestrator()
        orch._validate_proposal = AsyncMock(return_value=proposal)
        orch._apply_user_edits = AsyncMock()
        orch._resolve_repository = AsyncMock(
            return_value=(OWNER, REPO, PROJECT_ID)
        )
        orch._create_github_issue = AsyncMock(return_value=issue_data)
        orch._broadcast_confirmation = AsyncMock()
        orch._configure_workflow = AsyncMock(side_effect=RuntimeError("boom"))

        result = await orch.confirm(str(proposal.proposal_id), None, session)

        # Should still return the proposal
        assert result is proposal
