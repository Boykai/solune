"""Webhooks API sub-package.

Splits the monolithic webhooks.py into event-type-specific modules:
- router.py: Main webhook dispatcher and deduplication
- utils.py: Signature verification and shared utilities
- pull_requests.py: Pull request event handlers
- check_runs.py: Check run and check suite handlers
"""
