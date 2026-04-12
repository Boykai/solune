from __future__ import annotations

from pathlib import Path

from tests.fleet_dispatch_harness import read_log, run_script


def _base_config() -> dict:
    return {
        'version': '1',
        'name': 'Test Fleet',
        'repository': {'owner': 'Boykai', 'name': 'solune'},
        'defaults': {
            'baseRef': 'main',
            'errorStrategy': 'continue',
            'pollIntervalSeconds': 5,
            'taskTimeoutSeconds': 10,
        },
        'groups': [
            {
                'id': 'serial',
                'name': 'Serial',
                'order': 1,
                'executionMode': 'serial',
                'agents': [
                    {
                        'slug': 'alpha',
                        'displayName': 'Alpha',
                        'customAgent': 'alpha',
                        'model': 'claude-opus-4.6',
                        'instructionTemplate': 'solune/scripts/pipelines/templates/generic.md',
                        'retryable': True,
                        'subIssue': {'title': '[Fleet] Alpha for #{{PARENT_ISSUE_NUMBER}}', 'labels': ['alpha']},
                    },
                    {
                        'slug': 'beta',
                        'displayName': 'Beta',
                        'customAgent': 'beta',
                        'model': 'claude-opus-4.6',
                        'instructionTemplate': 'solune/scripts/pipelines/templates/generic.md',
                        'retryable': True,
                        'subIssue': {'title': '[Fleet] Beta for #{{PARENT_ISSUE_NUMBER}}', 'labels': ['beta']},
                    },
                ],
            },
            {
                'id': 'parallel',
                'name': 'Parallel',
                'order': 2,
                'executionMode': 'parallel',
                'agents': [
                    {
                        'slug': 'gamma',
                        'displayName': 'Gamma',
                        'customAgent': 'gamma',
                        'model': 'claude-opus-4.6',
                        'instructionTemplate': 'solune/scripts/pipelines/templates/generic.md',
                        'retryable': True,
                        'subIssue': {'title': '[Fleet] Gamma for #{{PARENT_ISSUE_NUMBER}}', 'labels': ['gamma']},
                    },
                    {
                        'slug': 'delta',
                        'displayName': 'Delta',
                        'customAgent': 'delta',
                        'model': 'claude-opus-4.6',
                        'instructionTemplate': 'solune/scripts/pipelines/templates/generic.md',
                        'retryable': True,
                        'subIssue': {'title': '[Fleet] Delta for #{{PARENT_ISSUE_NUMBER}}', 'labels': ['delta']},
                    },
                ],
            },
        ],
    }


class TestFleetDispatchCli:
    def test_dispatch_orders_serial_then_parallel(self, tmp_path: Path) -> None:
        result = run_script(tmp_path, _base_config())
        log_lines = read_log(tmp_path)

        assert result.returncode == 0, result.stderr
        assert log_lines.index('dispatch:[Fleet] Alpha for #1555') < log_lines.index('task_view:task-1')
        assert log_lines.index('task_view:task-1') < log_lines.index('dispatch:[Fleet] Beta for #1555')
        assert log_lines.index('dispatch:[Fleet] Beta for #1555') < log_lines.index('task_view:task-2')
        gamma_dispatch = log_lines.index('dispatch:[Fleet] Gamma for #1555')
        delta_dispatch = log_lines.index('dispatch:[Fleet] Delta for #1555')
        parallel_task_views = [idx for idx, line in enumerate(log_lines) if line.startswith('task_view:')][2:]
        assert parallel_task_views, log_lines
        assert gamma_dispatch < parallel_task_views[0]
        assert delta_dispatch < parallel_task_views[0]

    def test_retry_unassigns_before_redispatch(self, tmp_path: Path) -> None:
        config = _base_config()
        config['groups'] = [
            {
                'id': 'retry',
                'name': 'Retry',
                'order': 1,
                'executionMode': 'serial',
                'agents': [config['groups'][0]['agents'][1]],
            }
        ]
        extra_issue = {
            'number': 200,
            'node_id': 'ISSUE_NODE_200',
            'html_url': 'https://github.com/Boykai/solune/issues/200',
            'title': 'Existing retry issue',
            'body': 'Retry body',
            'labels': ['fleet-dispatch', 'fleet-parent:1555', 'fleet-agent:beta', 'beta'],
        }
        result = run_script(
            tmp_path,
            config,
            extra_issues=[extra_issue],
            extra_args=['--retry', '--agent', 'beta', '--sub-issue', '200'],
        )
        log_lines = read_log(tmp_path)

        assert result.returncode == 0, result.stderr
        assert log_lines.index('issue_edit:200') < log_lines.index('dispatch:Existing retry issue')
