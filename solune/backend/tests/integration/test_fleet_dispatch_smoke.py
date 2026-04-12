from __future__ import annotations

from pathlib import Path

from tests.fleet_dispatch_harness import read_log, run_script


def _config(error_strategy: str = 'continue') -> dict:
    return {
        'version': '1',
        'name': 'Smoke Fleet',
        'repository': {'owner': 'Boykai', 'name': 'solune'},
        'defaults': {
            'baseRef': 'main',
            'errorStrategy': error_strategy,
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
                    {
                        'slug': 'gamma',
                        'displayName': 'Gamma',
                        'customAgent': 'gamma',
                        'model': 'claude-opus-4.6',
                        'instructionTemplate': 'solune/scripts/pipelines/templates/generic.md',
                        'retryable': True,
                        'subIssue': {'title': '[Fleet] Gamma for #{{PARENT_ISSUE_NUMBER}}', 'labels': ['gamma']},
                    },
                ],
            }
        ],
    }


def test_continue_strategy_keeps_dispatching_after_one_failure(tmp_path: Path) -> None:
    result = run_script(tmp_path, _config(), fail_agent='beta', extra_args=['--error-strategy', 'continue'])
    log_lines = read_log(tmp_path)

    assert result.returncode != 0
    assert 'dispatch:[Fleet] Alpha for #1555' in log_lines
    assert 'dispatch:[Fleet] Gamma for #1555' in log_lines


def test_parent_issue_lock_blocks_new_dispatch(tmp_path: Path) -> None:
    result = run_script(tmp_path, _config(), prelock=True)

    assert result.returncode != 0
    assert 'already locked' in result.stderr
