"""Unit tests for ProposalOrchestrator — the extracted confirm_proposal workflow.

Tests each independently testable method of the orchestrator class,
verifying the contract behaviour documented in contracts/proposal-orchestrator-interface.md.
"""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.constants import GITHUB_ISSUE_BODY_MAX_LENGTH
from src.exceptions import NotFoundError, ValidationError
from src.models.recommendation import AITaskProposal, ProposalConfirmRequest, ProposalStatus
from src.models.user import UserSession
from src.services.proposal_orchestrator import ProposalOrchestrator
from src.utils import utcnow

# ── Helpers ─────────────────────────────────────────────────────────────────


def _make_session(**kw) -> UserSession:
    defaults = {
        "github_user_id": "12345",
        "github_username": "testuser",
        "access_token": "test-token",
        "selected_project_id": "PVT_1",
    }
    defaults.update(kw)
    return UserSession(**defaults)


def _make_proposal(session_id=None, **kw) -> AITaskProposal:
    defaults = {
        "session_id": session_id or uuid4(),
        "original_input": "fix login bug",
        "proposed_title": "Fix login bug",
        "proposed_description": "Fix the login flow",
    }
    defaults.update(kw)
    return AITaskProposal(**defaults)


def _make_orchestrator(chat_store=None) -> ProposalOrchestrator:
    store = chat_store or MagicMock()
    store.update_proposal_status = AsyncMock()
    return ProposalOrchestrator(chat_state_manager=None, chat_store_module=store)


# ── _validate_proposal ─────────────────────────────────────────────────────


class TestValidateProposal:
    """Tests for _validate_proposal — ownership, expiration, and status checks."""

    async def test_not_found_raises(self):
        orch = _make_orchestrator()
        session = _make_session()
        with (
            patch("src.services.proposal_orchestrator.get_db", return_value=MagicMock()),
            patch(
                "src.api.chat.helpers.get_proposal",
                new=AsyncMock(return_value=None),
            ),
            pytest.raises(NotFoundError, match="Proposal not found"),
        ):
            await orch._validate_proposal("nonexistent", session)

    async def test_wrong_session_raises(self):
        orch = _make_orchestrator()
        session = _make_session()
        other_session = uuid4()
        proposal = _make_proposal(session_id=other_session)

        with (
            patch("src.services.proposal_orchestrator.get_db", return_value=MagicMock()),
            patch(
                "src.api.chat.helpers.get_proposal",
                new=AsyncMock(return_value=proposal),
            ),
            pytest.raises(NotFoundError, match="Proposal not found"),
        ):
            await orch._validate_proposal(str(proposal.proposal_id), session)

    async def test_expired_proposal_cancels_and_raises(self):
        orch = _make_orchestrator()
        session = _make_session()
        proposal = _make_proposal(
            session_id=session.session_id,
            expires_at=utcnow() - timedelta(minutes=1),
        )

        with (
            patch("src.services.proposal_orchestrator.get_db", return_value=MagicMock()),
            patch(
                "src.api.chat.helpers.get_proposal",
                new=AsyncMock(return_value=proposal),
            ),
            pytest.raises(ValidationError, match="expired"),
        ):
            await orch._validate_proposal(str(proposal.proposal_id), session)

        assert proposal.status == ProposalStatus.CANCELLED

    async def test_expired_proposal_status_persist_failure_still_raises(self):
        """Even if SQLite update fails, the ValidationError is still raised."""
        store = MagicMock()
        store.update_proposal_status = AsyncMock(side_effect=RuntimeError("db down"))
        orch = ProposalOrchestrator(chat_state_manager=None, chat_store_module=store)
        session = _make_session()
        proposal = _make_proposal(
            session_id=session.session_id,
            expires_at=utcnow() - timedelta(minutes=1),
        )

        with (
            patch("src.services.proposal_orchestrator.get_db", return_value=MagicMock()),
            patch(
                "src.api.chat.helpers.get_proposal",
                new=AsyncMock(return_value=proposal),
            ),
            pytest.raises(ValidationError, match="expired"),
        ):
            await orch._validate_proposal(str(proposal.proposal_id), session)

    async def test_already_confirmed_raises(self):
        orch = _make_orchestrator()
        session = _make_session()
        proposal = _make_proposal(
            session_id=session.session_id,
            status=ProposalStatus.CONFIRMED,
        )

        with (
            patch("src.services.proposal_orchestrator.get_db", return_value=MagicMock()),
            patch(
                "src.api.chat.helpers.get_proposal",
                new=AsyncMock(return_value=proposal),
            ),
            pytest.raises(ValidationError, match="already confirmed"),
        ):
            await orch._validate_proposal(str(proposal.proposal_id), session)

    async def test_already_cancelled_raises(self):
        orch = _make_orchestrator()
        session = _make_session()
        proposal = _make_proposal(
            session_id=session.session_id,
            status=ProposalStatus.CANCELLED,
        )

        with (
            patch("src.services.proposal_orchestrator.get_db", return_value=MagicMock()),
            patch(
                "src.api.chat.helpers.get_proposal",
                new=AsyncMock(return_value=proposal),
            ),
            pytest.raises(ValidationError, match="already cancelled"),
        ):
            await orch._validate_proposal(str(proposal.proposal_id), session)

    async def test_valid_pending_proposal_returns(self):
        orch = _make_orchestrator()
        session = _make_session()
        proposal = _make_proposal(session_id=session.session_id)

        with (
            patch("src.services.proposal_orchestrator.get_db", return_value=MagicMock()),
            patch(
                "src.api.chat.helpers.get_proposal",
                new=AsyncMock(return_value=proposal),
            ),
        ):
            result = await orch._validate_proposal(str(proposal.proposal_id), session)

        assert result is proposal
        assert result.status == ProposalStatus.PENDING


# ── _apply_edits ───────────────────────────────────────────────────────────


class TestApplyEdits:
    """Tests for _apply_edits — user-provided title/description edits."""

    def test_no_request_is_noop(self):
        orch = _make_orchestrator()
        proposal = _make_proposal()
        orch._apply_edits(proposal, None)
        assert proposal.edited_title is None
        assert proposal.edited_description is None
        assert proposal.status == ProposalStatus.PENDING

    def test_edited_title_sets_status_to_edited(self):
        orch = _make_orchestrator()
        proposal = _make_proposal()
        request = ProposalConfirmRequest(edited_title="New Title")
        orch._apply_edits(proposal, request)
        assert proposal.edited_title == "New Title"
        assert proposal.status == ProposalStatus.EDITED

    def test_edited_description_sets_status_to_edited(self):
        orch = _make_orchestrator()
        proposal = _make_proposal()
        request = ProposalConfirmRequest(edited_description="New description")
        orch._apply_edits(proposal, request)
        assert proposal.edited_description == "New description"
        assert proposal.status == ProposalStatus.EDITED

    def test_edited_both_title_and_description(self):
        orch = _make_orchestrator()
        proposal = _make_proposal()
        request = ProposalConfirmRequest(
            edited_title="New Title",
            edited_description="New description",
        )
        orch._apply_edits(proposal, request)
        assert proposal.edited_title == "New Title"
        assert proposal.edited_description == "New description"
        assert proposal.status == ProposalStatus.EDITED

    def test_empty_request_fields_are_noop(self):
        orch = _make_orchestrator()
        proposal = _make_proposal()
        request = ProposalConfirmRequest()
        orch._apply_edits(proposal, request)
        assert proposal.edited_title is None
        assert proposal.edited_description is None
        assert proposal.status == ProposalStatus.PENDING

    def test_final_title_reflects_edit(self):
        orch = _make_orchestrator()
        proposal = _make_proposal()
        request = ProposalConfirmRequest(edited_title="Edited Title")
        orch._apply_edits(proposal, request)
        assert proposal.final_title == "Edited Title"

    def test_final_description_reflects_edit(self):
        orch = _make_orchestrator()
        proposal = _make_proposal()
        request = ProposalConfirmRequest(edited_description="Edited Desc")
        orch._apply_edits(proposal, request)
        assert proposal.final_description == "Edited Desc"


# ── _build_body ────────────────────────────────────────────────────────────


class TestBuildBody:
    """Tests for _build_body — issue body construction and length validation."""

    def test_short_body_passes(self):
        orch = _make_orchestrator()
        proposal = _make_proposal()

        with patch(
            "src.attachment_formatter.format_attachments_markdown", return_value=""
        ):
            body = orch._build_body(proposal)

        assert body == "Fix the login flow"

    def test_body_with_attachments(self):
        orch = _make_orchestrator()
        proposal = _make_proposal(file_urls=["/uploads/img.png"])

        with patch(
            "src.attachment_formatter.format_attachments_markdown",
            return_value="\n\n![img](/uploads/img.png)",
        ):
            body = orch._build_body(proposal)

        assert "img.png" in body
        assert body.startswith("Fix the login flow")

    def test_oversized_body_raises_validation_error(self):
        orch = _make_orchestrator()
        proposal = _make_proposal()

        # Create a body that exceeds the limit
        huge_attachment = "x" * (GITHUB_ISSUE_BODY_MAX_LENGTH + 1)
        with (
            patch(
                "src.attachment_formatter.format_attachments_markdown",
                return_value=huge_attachment,
            ),
            pytest.raises(ValidationError, match="exceeds"),
        ):
            orch._build_body(proposal)

    def test_body_at_exact_limit_passes(self):
        orch = _make_orchestrator()
        # Create a proposal whose final_description + attachments = exactly the limit
        desc_len = GITHUB_ISSUE_BODY_MAX_LENGTH - 10
        proposal = _make_proposal(proposed_description="x" * desc_len)

        with patch(
            "src.attachment_formatter.format_attachments_markdown",
            return_value="y" * 10,
        ):
            body = orch._build_body(proposal)

        assert len(body) == GITHUB_ISSUE_BODY_MAX_LENGTH

    def test_empty_description_uses_empty_string(self):
        orch = _make_orchestrator()
        proposal = _make_proposal(proposed_description="")
        proposal.edited_description = None

        with patch(
            "src.attachment_formatter.format_attachments_markdown", return_value=""
        ):
            body = orch._build_body(proposal)

        assert body == ""


# ── _create_github_issue ───────────────────────────────────────────────────


class TestCreateGitHubIssue:
    """Tests for _create_github_issue — delegates to github_service.create_issue."""

    async def test_creates_issue_and_returns_tuple(self):
        orch = _make_orchestrator()
        session = _make_session()
        proposal = _make_proposal(session_id=session.session_id)
        github_service = AsyncMock()
        github_service.create_issue.return_value = {
            "html_url": "https://github.com/owner/repo/issues/42",
            "number": 42,
            "node_id": "I_42",
            "id": 100042,
        }

        result = await orch._create_github_issue(
            proposal, session, github_service, "owner", "repo", "body text"
        )

        assert result == (
            "https://github.com/owner/repo/issues/42",
            42,
            "I_42",
            100042,
        )
        github_service.create_issue.assert_awaited_once_with(
            access_token=session.access_token,
            owner="owner",
            repo="repo",
            title=proposal.final_title,
            body="body text",
            labels=[],
        )

    async def test_uses_edited_title_when_present(self):
        orch = _make_orchestrator()
        session = _make_session()
        proposal = _make_proposal(session_id=session.session_id)
        proposal.edited_title = "Custom Title"
        github_service = AsyncMock()
        github_service.create_issue.return_value = {
            "html_url": "https://github.com/o/r/issues/1",
            "number": 1,
            "node_id": "I_1",
            "id": 1,
        }

        await orch._create_github_issue(
            proposal, session, github_service, "o", "r", "body"
        )

        call_kwargs = github_service.create_issue.call_args.kwargs
        assert call_kwargs["title"] == "Custom Title"


# ── _add_to_project ───────────────────────────────────────────────────────


class TestAddToProject:
    """Tests for _add_to_project — delegates to github_service.add_issue_to_project."""

    async def test_returns_project_item_id(self):
        orch = _make_orchestrator()
        session = _make_session()
        github_service = AsyncMock()
        github_service.add_issue_to_project.return_value = "PVTI_99"

        result = await orch._add_to_project(
            "I_42", 100042, session, github_service, "PVT_1"
        )

        assert result == "PVTI_99"
        github_service.add_issue_to_project.assert_awaited_once_with(
            access_token=session.access_token,
            project_id="PVT_1",
            issue_node_id="I_42",
            issue_database_id=100042,
        )


# ── _persist_status ───────────────────────────────────────────────────────


class TestPersistStatus:
    """Tests for _persist_status — updates proposal to CONFIRMED in SQLite."""

    async def test_sets_status_and_calls_store(self):
        store = MagicMock()
        store.update_proposal_status = AsyncMock()
        orch = ProposalOrchestrator(chat_state_manager=None, chat_store_module=store)
        proposal = _make_proposal()

        with patch("src.services.proposal_orchestrator.get_db", return_value=MagicMock()) as mock_db:
            await orch._persist_status("p-1", proposal)

        assert proposal.status == ProposalStatus.CONFIRMED
        store.update_proposal_status.assert_awaited_once_with(
            mock_db.return_value,
            "p-1",
            ProposalStatus.CONFIRMED.value,
            edited_title=proposal.edited_title,
            edited_description=proposal.edited_description,
        )

    async def test_store_failure_does_not_raise(self):
        """SQLite failure is logged but not propagated."""
        store = MagicMock()
        store.update_proposal_status = AsyncMock(side_effect=RuntimeError("db down"))
        orch = ProposalOrchestrator(chat_state_manager=None, chat_store_module=store)
        proposal = _make_proposal()

        with patch("src.services.proposal_orchestrator.get_db", return_value=MagicMock()):
            await orch._persist_status("p-1", proposal)

        # Status is still set even if persist fails
        assert proposal.status == ProposalStatus.CONFIRMED

    async def test_persists_edited_title_and_description(self):
        store = MagicMock()
        store.update_proposal_status = AsyncMock()
        orch = ProposalOrchestrator(chat_state_manager=None, chat_store_module=store)
        proposal = _make_proposal()
        proposal.edited_title = "Edited"
        proposal.edited_description = "Edited desc"

        with patch("src.services.proposal_orchestrator.get_db", return_value=MagicMock()):
            await orch._persist_status("p-1", proposal)

        call_kwargs = store.update_proposal_status.call_args.kwargs
        assert call_kwargs["edited_title"] == "Edited"
        assert call_kwargs["edited_description"] == "Edited desc"


# ── _broadcast_update ─────────────────────────────────────────────────────


class TestBroadcastUpdate:
    """Tests for _broadcast_update — WebSocket task_created broadcast."""

    async def test_broadcasts_correct_payload(self):
        orch = _make_orchestrator()
        session = _make_session()
        proposal = _make_proposal(session_id=session.session_id)
        connection_manager = AsyncMock()

        await orch._broadcast_update(
            proposal, session, connection_manager,
            project_id="PVT_1",
            item_id="PVTI_10",
            issue_number=42,
            issue_url="https://github.com/owner/repo/issues/42",
        )

        connection_manager.broadcast_to_project.assert_awaited_once_with(
            "PVT_1",
            {
                "type": "task_created",
                "task_id": "PVTI_10",
                "title": proposal.final_title,
                "issue_number": 42,
                "issue_url": "https://github.com/owner/repo/issues/42",
            },
        )


# ── _resolve_pipeline ─────────────────────────────────────────────────────


class TestResolvePipeline:
    """Tests for _resolve_pipeline — selected pipeline vs. fallback resolution."""

    async def test_no_selected_pipeline_uses_project_fallback(self):
        orch = _make_orchestrator()
        proposal = _make_proposal()
        assert proposal.selected_pipeline_id is None

        mock_result = MagicMock(agent_mappings={"Backlog": ["copilot"]}, source="default")
        with patch(
            "src.services.workflow_orchestrator.config.resolve_project_pipeline_mappings",
            new=AsyncMock(return_value=mock_result),
        ):
            result = await orch._resolve_pipeline(proposal, "p-1", "PVT_1", "12345")

        assert result is mock_result

    async def test_selected_pipeline_found(self):
        orch = _make_orchestrator()
        proposal = _make_proposal(selected_pipeline_id="pipe-abc")

        mappings = {"Backlog": ["copilot"]}
        with patch(
            "src.services.workflow_orchestrator.config.load_pipeline_as_agent_mappings",
            new=AsyncMock(return_value=(mappings, "My Pipeline", {}, {})),
        ):
            result = await orch._resolve_pipeline(proposal, "p-1", "PVT_1", "12345")

        assert result.source == "pipeline"
        assert result.pipeline_name == "My Pipeline"
        assert result.agent_mappings == mappings

    async def test_selected_pipeline_not_found_falls_back(self):
        orch = _make_orchestrator()
        proposal = _make_proposal(selected_pipeline_id="pipe-missing")

        mock_fallback = MagicMock(agent_mappings={"Backlog": ["copilot"]}, source="default")
        with (
            patch(
                "src.services.workflow_orchestrator.config.load_pipeline_as_agent_mappings",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "src.services.workflow_orchestrator.config.resolve_project_pipeline_mappings",
                new=AsyncMock(return_value=mock_fallback),
            ),
        ):
            result = await orch._resolve_pipeline(proposal, "p-1", "PVT_1", "12345")

        assert result is mock_fallback


# ── _setup_workflow (integration-level) ────────────────────────────────────


class TestSetupWorkflow:
    """Tests for _setup_workflow — workflow config, pipeline, agent assignment.

    Failures in _setup_workflow are logged but do NOT prevent the endpoint
    from returning success (the issue has already been created).
    """

    async def test_setup_failure_does_not_raise(self):
        """_setup_workflow catches all exceptions."""
        orch = _make_orchestrator()
        session = _make_session()
        proposal = _make_proposal(session_id=session.session_id)

        with patch(
            "src.services.proposal_orchestrator.get_workflow_config",
            new=AsyncMock(side_effect=RuntimeError("boom")),
        ):
            # Should not raise
            await orch._setup_workflow(
                proposal, "p-1", session, AsyncMock(), AsyncMock(),
                "owner", "repo", "PVT_1", "PVTI_10", "I_42", 42,
            )

    async def test_creates_default_config_when_none_exists(self):
        orch = _make_orchestrator()
        session = _make_session()
        proposal = _make_proposal(session_id=session.session_id)
        github_service = AsyncMock()
        connection_manager = AsyncMock()

        mock_settings = MagicMock()
        mock_settings.default_assignee = "copilot-swe-agent"

        mock_orch = MagicMock()
        mock_orch.assign_agent_for_status = AsyncMock()
        mock_orch.create_all_sub_issues = AsyncMock(return_value=[])

        mock_pipeline_result = MagicMock(
            agent_mappings=None,
            source="default",
            pipeline_name=None,
        )

        with (
            patch(
                "src.services.proposal_orchestrator.get_workflow_config",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "src.services.proposal_orchestrator.set_workflow_config",
                new=AsyncMock(),
            ) as mock_set_config,
            patch(
                "src.services.proposal_orchestrator.get_workflow_orchestrator",
                return_value=mock_orch,
            ),
            patch(
                "src.services.proposal_orchestrator.get_agent_slugs",
                return_value=[],
            ),
            patch("src.config.get_settings", return_value=mock_settings),
            patch(
                "src.services.proposal_orchestrator.get_effective_user_settings",
                new=AsyncMock(side_effect=RuntimeError("no settings")),
            ),
            patch("src.services.proposal_orchestrator.get_db", return_value=MagicMock()),
            patch(
                "src.services.copilot_polling.ensure_polling_started",
                new=AsyncMock(),
            ) as mock_polling,
            patch.object(orch, "_resolve_pipeline", new=AsyncMock(return_value=mock_pipeline_result)),
        ):
            await orch._setup_workflow(
                proposal, "p-1", session, github_service, connection_manager,
                "owner", "repo", "PVT_1", "PVTI_10", "I_42", 42,
            )

        # set_workflow_config should have been called (to create default config)
        mock_set_config.assert_awaited()
        # Workflow continues despite settings retrieval failure
        mock_orch.assign_agent_for_status.assert_awaited_once()
        mock_polling.assert_awaited_once()


# ── Backward-compatible re-exports ─────────────────────────────────────────


class TestChatPackageReExports:
    """Verify that all symbols previously importable from src.api.chat still work."""

    def test_state_dicts_importable(self):
        from src.api.chat import _locks, _messages, _proposals, _recommendations

        assert isinstance(_messages, dict)
        assert isinstance(_proposals, dict)
        assert isinstance(_recommendations, dict)
        assert isinstance(_locks, dict)

    def test_helper_functions_importable(self):
        from src.api.chat import (
            _resolve_repository,
            _retry_persist,
            _safe_validation_detail,
            _trigger_signal_delivery,
            add_message,
            get_proposal,
            get_recommendation,
            get_session_messages,
            store_proposal,
            store_recommendation,
        )

        # All should be callable
        assert callable(_resolve_repository)
        assert callable(add_message)
        assert callable(get_proposal)
        assert callable(get_recommendation)
        assert callable(get_session_messages)
        assert callable(store_proposal)
        assert callable(store_recommendation)
        assert callable(_trigger_signal_delivery)
        assert callable(_retry_persist)
        assert callable(_safe_validation_detail)

    def test_constants_importable(self):
        from src.api.chat import _PERSIST_BASE_DELAY, _PERSIST_MAX_RETRIES

        assert _PERSIST_MAX_RETRIES == 3
        assert _PERSIST_BASE_DELAY == 0.1

    def test_router_importable(self):
        from src.api.chat import router

        assert router is not None

    def test_dispatch_functions_importable(self):
        from src.api.chat import (
            _extract_transcript_content,
            _handle_transcript_upload,
            _post_process_agent_response,
        )

        assert callable(_extract_transcript_content)
        assert callable(_handle_transcript_upload)
        assert callable(_post_process_agent_response)

    def test_model_importable(self):
        from src.api.chat import FileUploadResponse

        assert FileUploadResponse is not None

    def test_upload_file_importable(self):
        from src.api.chat import upload_file

        assert callable(upload_file)


class TestWebhooksPackageReExports:
    """Verify that all symbols previously importable from src.api.webhooks still work."""

    def test_router_importable(self):
        from src.api.webhooks import router

        assert router is not None

    def test_handler_importable(self):
        from src.api.webhooks import github_webhook

        assert callable(github_webhook)

    def test_common_functions_importable(self):
        from src.api.webhooks import (
            _processed_delivery_ids,
            classify_pull_request_activity,
            extract_issue_number_from_pr,
            verify_webhook_signature,
        )

        assert callable(classify_pull_request_activity)
        assert callable(extract_issue_number_from_pr)
        assert callable(verify_webhook_signature)
        # BoundedSet — not a plain set, but should support `in` / `add` operations
        assert hasattr(_processed_delivery_ids, "add")

    def test_pull_request_handlers_importable(self):
        from src.api.webhooks import (
            handle_copilot_pr_ready,
            handle_pull_request_event,
            update_issue_status_for_copilot_pr,
        )

        assert callable(handle_copilot_pr_ready)
        assert callable(handle_pull_request_event)
        assert callable(update_issue_status_for_copilot_pr)

    def test_check_run_handlers_importable(self):
        from src.api.webhooks import handle_check_run_event, handle_check_suite_event

        assert callable(handle_check_run_event)
        assert callable(handle_check_suite_event)

    def test_service_references_importable(self):
        from src.api.webhooks import get_db, get_settings, log_event

        assert callable(get_db)
        assert callable(get_settings)
        assert callable(log_event)


# ── Chat state module ──────────────────────────────────────────────────────


class TestChatState:
    """Tests for chat state module — verifies the extracted state dicts behave correctly."""

    def test_state_dicts_are_mutable(self):
        from src.api.chat.state import _locks, _messages, _proposals, _recommendations

        # Verify they can be used as expected
        _messages["test-key"] = []
        assert _messages["test-key"] == []
        del _messages["test-key"]

    def test_constants_have_expected_values(self):
        from src.api.chat.state import _PERSIST_BASE_DELAY, _PERSIST_MAX_RETRIES

        assert _PERSIST_MAX_RETRIES == 3
        assert _PERSIST_BASE_DELAY == 0.1

    def test_state_shared_between_imports(self):
        """State dicts should be the same objects when imported from different paths."""
        from src.api.chat import _messages as chat_messages
        from src.api.chat.state import _messages as state_messages

        assert chat_messages is state_messages
