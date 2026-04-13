from __future__ import annotations

import pytest

from src.services.fleet_dispatch import FleetDispatchService
from src.services.github_projects import GitHubProjectsService
from src.services.workflow_orchestrator.config import load_fleet_dispatch_config


def _fleet_eligible_agents() -> list[tuple[str, str]]:
    config = load_fleet_dispatch_config()
    service = FleetDispatchService()
    return [
        (agent.slug, agent.instruction_template)
        for group in config.groups
        for agent in group.agents
        if service.is_fleet_eligible(agent.slug)
    ]


@pytest.mark.parametrize(
    ("agent_slug", "instruction_template"),
    _fleet_eligible_agents(),
    ids=lambda value: value,
)
def test_fleet_prompt_preserves_core_issue_context(
    agent_slug: str,
    instruction_template: str,
) -> None:
    issue_data = {
        "title": "Add caching layer",
        "body": "We need Redis caching for expensive project lookups.",
        "comments": [
            {
                "author": "alice",
                "body": "Please handle cache invalidation carefully.",
                "created_at": "2026-04-12T10:00:00Z",
            }
        ],
    }
    github = GitHubProjectsService()
    fleet = FleetDispatchService()

    backend_prompt = github.format_issue_context_as_prompt(issue_data, agent_name=agent_slug)
    fleet_prompt = fleet.build_dispatch_payload(
        issue_data=issue_data,
        agent_slug=agent_slug,
        owner="Boykai",
        repo="solune",
        base_ref="copilot/test-branch",
        parent_issue_number=1555,
        parent_issue_url="https://github.com/Boykai/solune/issues/1555",
        assignment_config={
            "customAgent": agent_slug,
            "instructionTemplate": instruction_template,
        },
        existing_pr={"head_ref": "copilot/test-branch"},
        fallback_instructions=backend_prompt,
    ).custom_instructions

    for snippet in [
        "Add caching layer",
        "We need Redis caching for expensive project lookups.",
        "Please handle cache invalidation carefully.",
    ]:
        assert snippet in backend_prompt
        assert snippet in fleet_prompt
