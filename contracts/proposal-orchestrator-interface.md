# Contract: `ProposalOrchestrator` Service Interface

**Feature**: Codebase Modularity Review | **Date**: 2026-04-11

> Defines the public interface of the `ProposalOrchestrator` service extracted from the `confirm_proposal()` god function.

## Class Definition

```python
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.models.recommendation import AITaskProposal, ProposalConfirmRequest
    from src.models.user import UserSession


class ProposalOrchestrator:
    """
    Orchestrates the proposal confirmation workflow.

    Extracted from the monolithic confirm_proposal() function in api/chat.py.
    Each step is an independently testable method.
    """

    def __init__(
        self,
        chat_state_manager: Any,
        chat_store_module: Any,
    ) -> None:
        """
        Args:
            chat_state_manager: In-memory state module (src.api.chat.state).
            chat_store_module: Persistent storage module (src.services.chat_store).
        """
        ...

    async def confirm(
        self,
        proposal_id: str,
        request: ProposalConfirmRequest | None,
        session: UserSession,
        github_service: Any,
        connection_manager: Any,
    ) -> AITaskProposal:
        """
        Full confirmation flow: validate → edit → create issue → add to project
        → persist → broadcast → setup workflow.

        Raises NotFoundError, ValidationError (same as the original endpoint).
        """
        ...
```

## Step Methods (Private)

Each step is a private method that can be tested independently by instantiating the class with mocked dependencies.

### `_validate_proposal`

```python
async def _validate_proposal(
    self,
    proposal_id: str,
    session: UserSession,
) -> AITaskProposal:
    """
    Retrieve proposal from cache/store and validate ownership + expiration + status.

    Returns the validated proposal.
    Raises NotFoundError or ValidationError.
    """
```

### `_apply_edits`

```python
def _apply_edits(
    self,
    proposal: AITaskProposal,
    request: ProposalConfirmRequest | None,
) -> None:
    """
    Apply user-provided title/description edits to the proposal.

    Mutates the proposal in place. No-op if request is None or has no edits.
    """
```

### `_build_body`

```python
def _build_body(self, proposal: AITaskProposal) -> str:
    """
    Build issue body with attachments and validate length.

    Raises ValidationError if body exceeds GitHub's character limit.
    """
```

### `_create_github_issue`

```python
async def _create_github_issue(
    self,
    proposal: AITaskProposal,
    session: UserSession,
    github_service: Any,
    owner: str,
    repo: str,
    body: str,
) -> tuple[str, int, str, int]:
    """
    Create a GitHub issue from the proposal.

    Returns (issue_url, issue_number, issue_node_id, issue_database_id).
    """
```

### `_add_to_project`

```python
async def _add_to_project(
    self,
    issue_node_id: str,
    issue_database_id: int,
    session: UserSession,
    github_service: Any,
    project_id: str,
) -> str:
    """
    Add the created issue to the user's GitHub project board.

    Returns the project item ID.
    """
```

### `_persist_status`

```python
async def _persist_status(
    self,
    proposal_id: str,
    proposal: AITaskProposal,
) -> None:
    """
    Update the proposal's status to CONFIRMED in SQLite via chat_store.

    Failure is logged but does not raise.
    """
```

### `_broadcast_update`

```python
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
    """
    Send the task_created WebSocket broadcast to connected clients.
    """
```

### `_setup_workflow`

```python
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
    """
    Set up workflow config, resolve pipeline, assign agent, start polling.

    Failures are logged but do not cause the endpoint to fail — the issue
    has already been created successfully at this point.
    """
```

### `_resolve_pipeline`

```python
async def _resolve_pipeline(
    self,
    proposal: AITaskProposal,
    proposal_id: str,
    project_id: str,
    github_user_id: str,
) -> Any:
    """
    Resolve pipeline mappings — selected pipeline or project/user/default fallback.
    """
```

## Error Handling Contract

| Error Type | HTTP Status | When |
|-----------|-------------|------|
| `NotFoundError` | 404 | Proposal ID doesn't exist or belongs to different session |
| `ValidationError` | 422 | Proposal has expired, already confirmed, or body exceeds limit |

## Testing Contract

```python
# Unit test example — test validation independently
orchestrator = ProposalOrchestrator(
    chat_state_manager=mock_state,
    chat_store_module=mock_store,
)
proposal = await orchestrator._validate_proposal("pid-123", mock_session)
assert proposal.status == ProposalStatus.PENDING

# Unit test example — test edits mutate in place
orchestrator._apply_edits(proposal, mock_request)
assert proposal.edited_title == mock_request.edited_title
```
