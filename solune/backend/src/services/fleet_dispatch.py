from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from src.logging_utils import get_logger
from src.models.pipeline import FleetDispatchAgent

logger = get_logger(__name__)

_FLEET_EXCLUDED_AGENTS = frozenset({"copilot-review", "human"})


@dataclass(frozen=True)
class FleetDispatchPayload:
    """Resolved dispatch metadata for a fleet-backed agent assignment."""

    custom_agent: str
    custom_instructions: str
    template_path: Path


@lru_cache(maxsize=1)
def _load_canonical_agents() -> dict[str, FleetDispatchAgent]:
    """Return the canonical fleet agent definitions keyed by slug."""

    try:
        from src.services.workflow_orchestrator.config import load_fleet_dispatch_config

        config = load_fleet_dispatch_config()
    except Exception:
        logger.warning("Failed to load canonical fleet dispatch config", exc_info=True)
        return {}

    return {agent.slug: agent for group in config.groups for agent in group.agents}


class FleetDispatchService:
    """Resolve fleet-backed agent dispatch settings for orchestrator assignments."""

    def __init__(self, repo_root: Path | None = None):
        self._repo_root = (repo_root or Path(__file__).resolve().parents[3]).resolve()
        self._templates_dir = self._repo_root / "scripts" / "pipelines" / "templates"
        self._generic_template = self._templates_dir / "generic.md"

    @staticmethod
    def is_fleet_eligible(agent_slug: str) -> bool:
        """Return whether an agent should use fleet-backed dispatch by default."""

        return agent_slug not in _FLEET_EXCLUDED_AGENTS

    def build_dispatch_payload(
        self,
        *,
        issue_data: dict[str, Any],
        agent_slug: str,
        owner: str,
        repo: str,
        base_ref: str,
        parent_issue_number: int,
        assignment_config: dict[str, Any] | None = None,
        existing_pr: dict[str, Any] | None = None,
        parent_issue_url: str | None = None,
        fallback_instructions: str = "",
    ) -> FleetDispatchPayload:
        """Build the fleet dispatch payload for one agent assignment."""

        template_path = self.resolve_template_path(agent_slug, assignment_config)
        custom_agent = self.resolve_custom_agent(agent_slug, assignment_config)
        if parent_issue_url is None:
            parent_issue_url = f"https://github.com/{owner}/{repo}/issues/{parent_issue_number}"

        try:
            custom_instructions = self.render_template(
                template_path=template_path,
                issue_data=issue_data,
                base_ref=base_ref,
                parent_issue_number=parent_issue_number,
                parent_issue_url=parent_issue_url,
                existing_pr=existing_pr,
            )
        except Exception:
            logger.warning(
                "Failed to render fleet dispatch template for agent '%s' from %s",
                agent_slug,
                template_path,
                exc_info=True,
            )
            custom_instructions = fallback_instructions

        return FleetDispatchPayload(
            custom_agent=custom_agent,
            custom_instructions=custom_instructions,
            template_path=template_path,
        )

    @staticmethod
    def build_fleet_sub_issue_labels(parent_issue_number: int, agent_slug: str) -> list[str]:
        """Return the canonical resume labels for a fleet-managed sub-issue."""

        return [
            "fleet-dispatch",
            f"fleet-parent:{parent_issue_number}",
            f"fleet-agent:{agent_slug}",
        ]

    @staticmethod
    def normalize_task_state(state: str | None) -> str | None:
        """Normalize task states to the shared fleet status vocabulary."""

        if not state:
            return None
        normalized = state.lower().replace(" ", "_").replace("-", "_")
        if normalized in {"pending", "queued"}:
            return "queued"
        if normalized in {"in_progress", "running"}:
            return "in_progress"
        if normalized in {"completed", "success", "succeeded", "done"}:
            return "completed"
        if normalized in {"failed", "failure", "error", "cancelled", "canceled"}:
            return "failed"
        return normalized

    async def resolve_task_id(
        self,
        *,
        github_service: Any,
        access_token: str,
        owner: str,
        repo: str,
        agent_slug: str,
        issue_title: str,
    ) -> str | None:
        """Best-effort resolve the most recent coding-agent task for a dispatch."""

        list_tasks = getattr(github_service, "list_agent_tasks", None)
        if list_tasks is None:
            return None

        try:
            tasks = await list_tasks(
                access_token=access_token,
                owner=owner,
                repo=repo,
                limit=100,
            )
        except Exception:
            logger.warning(
                "Failed to list agent tasks for %s/%s while resolving '%s'",
                owner,
                repo,
                agent_slug,
                exc_info=True,
            )
            return None

        normalized_slug = agent_slug.lower()
        normalized_title = issue_title.lower().strip()
        matches = [
            task
            for task in tasks
            if self._task_matches(
                task, normalized_slug=normalized_slug, normalized_title=normalized_title
            )
        ]
        if not matches:
            return None

        matches.sort(key=lambda task: str(task.get("createdAt") or task.get("created_at") or ""))
        latest = matches[-1]
        task_id = latest.get("id") or latest.get("taskId") or latest.get("task_id")
        return str(task_id) if task_id else None

    async def get_task_status(
        self,
        *,
        github_service: Any,
        access_token: str,
        owner: str,
        repo: str,
        task_id: str,
    ) -> str | None:
        """Best-effort fetch and normalize the state for one coding-agent task."""

        get_task = getattr(github_service, "get_agent_task", None)
        if get_task is None:
            return None

        try:
            task = await get_task(
                access_token=access_token,
                owner=owner,
                repo=repo,
                task_id=task_id,
            )
        except Exception:
            logger.warning(
                "Failed to fetch agent task '%s' for %s/%s",
                task_id,
                owner,
                repo,
                exc_info=True,
            )
            return None

        if not task:
            return None
        return self.normalize_task_state(str(task.get("state") or ""))

    def resolve_custom_agent(
        self,
        agent_slug: str,
        assignment_config: dict[str, Any] | None = None,
    ) -> str:
        """Resolve the custom agent id for fleet-backed dispatch."""

        configured = self._first_config_value(assignment_config, "customAgent", "custom_agent")
        if configured:
            return configured

        canonical = _load_canonical_agents().get(agent_slug)
        if canonical and canonical.custom_agent:
            return canonical.custom_agent

        return agent_slug

    def resolve_template_path(
        self,
        agent_slug: str,
        assignment_config: dict[str, Any] | None = None,
    ) -> Path:
        """Resolve the instruction template path for an agent, with generic fallback."""

        configured = self._first_config_value(
            assignment_config,
            "instructionTemplate",
            "instruction_template",
        )
        if configured:
            return self._normalize_template_path(configured)

        canonical = _load_canonical_agents().get(agent_slug)
        if canonical and canonical.instruction_template:
            return self._normalize_template_path(canonical.instruction_template)

        return self._generic_template

    def render_template(
        self,
        *,
        template_path: Path,
        issue_data: dict[str, Any],
        base_ref: str,
        parent_issue_number: int,
        parent_issue_url: str,
        existing_pr: dict[str, Any] | None = None,
    ) -> str:
        """Render a fleet instruction template with the current issue context."""

        template = template_path.read_text(encoding="utf-8")
        replacements = {
            "{{ISSUE_TITLE}}": str(issue_data.get("title") or ""),
            "{{ISSUE_BODY}}": str(issue_data.get("body") or ""),
            "{{ISSUE_COMMENTS}}": self.render_comments_markdown(issue_data),
            "{{PARENT_ISSUE_NUMBER}}": str(parent_issue_number),
            "{{PARENT_ISSUE_URL}}": parent_issue_url,
            "{{BASE_REF}}": base_ref,
            "{{PR_BRANCH}}": str((existing_pr or {}).get("head_ref") or base_ref),
        }
        rendered = template
        for placeholder, value in replacements.items():
            rendered = rendered.replace(placeholder, value)
        return rendered

    @staticmethod
    def render_comments_markdown(issue_data: dict[str, Any]) -> str:
        """Render issue comments into the markdown block expected by fleet templates."""

        comments = issue_data.get("comments") or []
        if not comments:
            return ""

        sections: list[str] = ["## Comments and Discussion"]
        for idx, comment in enumerate(comments, start=1):
            user = comment.get("user") if isinstance(comment.get("user"), dict) else {}
            raw_author = comment.get("author")
            author_info = raw_author if isinstance(raw_author, dict) else {}
            author = (
                user.get("login")
                or author_info.get("login")
                or (raw_author if isinstance(raw_author, str) else "")
                or "unknown"
            )
            created_at = comment.get("created_at") or comment.get("createdAt") or ""
            body = comment.get("body") or ""
            sections.append(f"### Comment {idx} by @{author} ({created_at})\n{body}")
        return "\n\n".join(sections)

    def _normalize_template_path(self, configured_path: str) -> Path:
        path = Path(configured_path)
        if not path.is_absolute():
            path = self._repo_root / path
        if path.is_file():
            return path.resolve()
        return self._generic_template

    @staticmethod
    def _task_matches(
        task: dict[str, Any],
        *,
        normalized_slug: str,
        normalized_title: str,
    ) -> bool:
        name = str(task.get("name") or "").lower()
        if normalized_title and normalized_title in name:
            return True
        return normalized_slug in name

    @staticmethod
    def _first_config_value(
        assignment_config: dict[str, Any] | None,
        *keys: str,
    ) -> str:
        if not assignment_config:
            return ""
        for key in keys:
            value = assignment_config.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""
