# Contract: `ProposalOrchestrator` Service Interface

**Feature**: Codebase Modularity Review | **Date**: 2026-04-11

> Defines the public interface of the `ProposalOrchestrator` service extracted from the `confirm_proposal()` god function.

## Class Definition

```python
from src.models.chat import AITaskProposal, ProposalConfirmRequest
from src.models.auth import UserSession
from src.services.github_projects import GitHubProjectsService
from src.services.websocket import ConnectionManager


class ProposalOrchestrator:
    """
    Orchestrates the proposal confirmation workflow.

    Extracted from the monolithic confirm_proposal() function in api/chat.py.
    Each step is an independently testable method.
    """

    def __init__(
        self,
        chat_state: "ChatStateManager",
        chat_store: "ChatStore",
    ) -> None:
        """
        Args:
            chat_state: In-memory cache manager for proposals/messages.
            chat_store: Persistent storage (SQLite) for chat data.
        """
        ...

    async def confirm(
        self,
        proposal_id: str,
        request: ProposalConfirmRequest | None,
        session: UserSession,
        github_service: GitHubProjectsService,
        connection_manager: ConnectionManager,
    ) -> AITaskProposal:
        """
        Full confirmation flow: validate → edit → create issue → add to project → persist → broadcast.

        Raises:
            NotFoundError: Proposal not found or not owned by session.
            ExpiredError: Proposal has expired.
            GitHubApiError: GitHub issue creation or project assignment failed.
            PersistenceError: SQLite write failed after retries.
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
    Retrieve proposal from cache/store and validate ownership + expiration.

    Returns the validated proposal.
    Raises NotFoundError or ExpiredError.
    """
```

### `_apply_edits`

```python
def _apply_edits(
    self,
    proposal: AITaskProposal,
    request: ProposalConfirmRequest | None,
) -> AITaskProposal:
    """
    Apply user-provided title/description edits to the proposal.

    Pure function — no side effects.
    Returns a new proposal with edits applied (or the same proposal if no edits).
    """
```

### `_create_github_issue`

```python
async def _create_github_issue(
    self,
    proposal: AITaskProposal,
    session: UserSession,
    github_service: GitHubProjectsService,
) -> tuple[str, int]:
    """
    Create a GitHub issue from the proposal.

    Returns (issue_url, issue_number).
    Raises GitHubApiError on failure.
    """
```

### `_add_to_project`

```python
async def _add_to_project(
    self,
    issue_number: int,
    session: UserSession,
    github_service: GitHubProjectsService,
) -> None:
    """
    Add the created issue to the user's GitHub project board.

    No-op if the project is not configured.
    Raises GitHubApiError on failure.
    """
```

### `_persist_status`

```python
async def _persist_status(
    self,
    proposal: AITaskProposal,
) -> None:
    """
    Update the proposal's status in SQLite via chat_store.

    Uses retry logic for transient SQLite errors.
    Raises PersistenceError after max retries.
    """
```

### `_broadcast_update`

```python
async def _broadcast_update(
    self,
    proposal: AITaskProposal,
    session: UserSession,
    connection_manager: ConnectionManager,
) -> None:
    """
    Send the updated proposal to connected WebSocket clients.

    Failure is logged but does not raise — broadcast is best-effort.
    """
```

## Error Handling Contract

| Error Type | HTTP Status | When |
|-----------|-------------|------|
| `NotFoundError` | 404 | Proposal ID doesn't exist or belongs to different session |
| `ExpiredError` | 410 | Proposal has passed its expiration timestamp |
| `GitHubApiError` | 502 | GitHub API returned an error during issue creation or project assignment |
| `PersistenceError` | 500 | SQLite write failed after retry attempts |
| `ValueError` | 422 | Issue body exceeds GitHub's 64000 character limit |

## Testing Contract

```python
# Unit test example — test validation independently
orchestrator = ProposalOrchestrator(
    chat_state=mock_state,
    chat_store=mock_store,
)
proposal = await orchestrator._validate_proposal("pid-123", mock_session)
assert proposal.status == "pending"

# Unit test example — test GitHub creation independently
url, number = await orchestrator._create_github_issue(
    proposal=mock_proposal,
    session=mock_session,
    github_service=mock_github,  # Only mock needed
)
assert number == 42
```
