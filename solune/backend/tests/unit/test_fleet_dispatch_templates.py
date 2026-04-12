from __future__ import annotations

import os
import subprocess
from pathlib import Path

from src.services.github_projects import GitHubProjectsService

SCRIPTS_DIR = Path(__file__).resolve().parents[3] / 'scripts'
COMMON_SH = SCRIPTS_DIR / 'lib' / 'fleet_dispatch_common.sh'
TEMPLATES_DIR = SCRIPTS_DIR / 'pipelines' / 'templates'
REPO_ROOT = Path(__file__).resolve().parents[4]


def _run_shell(function_call: str, env: dict[str, str]) -> str:
    result = subprocess.run(
        ['bash', '-lc', f'source "{COMMON_SH}"; {function_call}'],
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, **env},
    )
    return result.stdout.strip()


class TestFleetDispatchTemplates:
    def test_rendered_template_contains_backend_prompt_sections(self) -> None:
        issue_data = {
            'title': 'Add caching layer',
            'body': 'We need Redis caching.',
            'comments': [
                {
                    'author': 'alice',
                    'body': 'Investigate cache invalidation.',
                    'created_at': '2026-04-12T10:00:00Z',
                }
            ],
        }
        service = GitHubProjectsService()
        backend_prompt = service.format_issue_context_as_prompt(issue_data, agent_name='speckit.implement')
        comments_markdown = '## Comments and Discussion\n\n### Comment 1 by @alice (2026-04-12T10:00:00Z)\nInvestigate cache invalidation.'

        rendered = _run_shell(
            'fd_render_template "$TEMPLATE_PATH" "$ISSUE_TITLE" "$ISSUE_BODY" "$ISSUE_COMMENTS" "$PARENT_ISSUE_NUMBER" "$PARENT_ISSUE_URL" "$BASE_REF" "$PR_BRANCH"',
            {
                'TEMPLATE_PATH': str(TEMPLATES_DIR / 'speckit.implement.md'),
                'ISSUE_TITLE': issue_data['title'],
                'ISSUE_BODY': issue_data['body'],
                'ISSUE_COMMENTS': comments_markdown,
                'PARENT_ISSUE_NUMBER': '1555',
                'PARENT_ISSUE_URL': 'https://github.com/Boykai/solune/issues/1555',
                'BASE_REF': 'copilot/test-branch',
                'PR_BRANCH': 'copilot/test-branch',
            },
        )

        for snippet in [
            '## Issue Title',
            'Add caching layer',
            '## Issue Description',
            'We need Redis caching.',
            '## Comments and Discussion',
            'Investigate cache invalidation.',
        ]:
            assert snippet in backend_prompt
            assert snippet in rendered
        assert 'commit all changes to the PR branch (`copilot/test-branch`)' in rendered

    def test_tailored_sub_issue_body_preserves_parent_link_and_agent_task(self) -> None:
        service = GitHubProjectsService()
        backend_body = service.tailor_body_for_agent(
            parent_body='Parent body text',
            agent_name='tester',
            parent_issue_number=1555,
            parent_title='Fleet Dispatch',
        )

        rendered = _run_shell(
            'fd_tailor_body_for_agent "$PARENT_BODY" "$AGENT_SLUG" "$PARENT_ISSUE_NUMBER" "$PARENT_TITLE"',
            {
                'PARENT_BODY': 'Parent body text',
                'AGENT_SLUG': 'tester',
                'PARENT_ISSUE_NUMBER': '1555',
                'PARENT_TITLE': 'Fleet Dispatch',
            },
        )

        for snippet in [
            '> **Parent Issue:** #1555 — Fleet Dispatch',
            '## 🤖 Agent Task: `tester`',
            'Parent body text',
            'Sub-issue created for agent `tester`',
        ]:
            assert snippet in backend_body
            assert snippet in rendered

    def test_missing_template_falls_back_to_generic_template(self) -> None:
        resolved = _run_shell(
            'fd_template_path "$REPO_ROOT" "$MISSING_TEMPLATE"',
            {
                'REPO_ROOT': str(REPO_ROOT),
                'MISSING_TEMPLATE': 'solune/scripts/pipelines/templates/not-there.md',
            },
        )

        assert resolved.endswith('solune/scripts/pipelines/templates/generic.md')
