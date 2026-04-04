"""Tests for pure helpers in src.services.copilot_polling.agent_output."""

from __future__ import annotations

import pytest

from src.services.copilot_polling.agent_output import (
    _build_agent_output_summary,
    _format_changed_file_list,
)


class TestFormatChangedFileList:
    """Tests for the bounded file-list renderer."""

    def test_empty_list_returns_none(self):
        assert _format_changed_file_list([]) == "none"

    def test_single_file(self):
        result = _format_changed_file_list(["src/main.py"])
        assert result == "`src/main.py`"

    def test_multiple_within_limit(self):
        paths = ["a.py", "b.py", "c.py"]
        result = _format_changed_file_list(paths, limit=5)
        assert result == "`a.py`, `b.py`, `c.py`"

    def test_truncates_at_default_limit(self):
        paths = [f"file{i}.py" for i in range(8)]
        result = _format_changed_file_list(paths)
        assert "... and 3 more" in result
        # Should show first 5 files
        assert "`file0.py`" in result
        assert "`file4.py`" in result
        assert "`file5.py`" not in result

    def test_custom_limit(self):
        paths = ["a.py", "b.py", "c.py"]
        result = _format_changed_file_list(paths, limit=2)
        assert "`a.py`" in result
        assert "`b.py`" in result
        assert "... and 1 more" in result

    def test_exactly_at_limit(self):
        paths = ["a.py", "b.py", "c.py"]
        result = _format_changed_file_list(paths, limit=3)
        assert "more" not in result
        assert result == "`a.py`, `b.py`, `c.py`"


class TestBuildAgentOutputSummary:
    """Tests for the concise sub-issue summary builder."""

    def test_no_changed_files(self):
        result = _build_agent_output_summary("tester", 42, [])
        assert "`tester` completed PR #42." in result
        assert "Changed files: 0" in result
        assert "No changed files were reported" in result

    def test_with_markdown_files(self):
        pr_files = [
            {"filename": "README.md", "status": "modified"},
            {"filename": "docs/guide.md", "status": "added"},
        ]
        result = _build_agent_output_summary("archivist", 10, pr_files)
        assert "Markdown touched: 2" in result
        assert "`README.md`" in result

    def test_with_non_markdown_files(self):
        pr_files = [
            {"filename": "src/main.py", "status": "modified"},
            {"filename": "src/utils.py", "status": "added"},
        ]
        result = _build_agent_output_summary("coder", 5, pr_files)
        assert "Non-markdown touched: 2" in result
        assert "`src/main.py`" in result

    def test_mixed_files(self):
        pr_files = [
            {"filename": "README.md", "status": "modified"},
            {"filename": "src/app.py", "status": "added"},
        ]
        result = _build_agent_output_summary("dev", 99, pr_files)
        assert "Changed files: 2" in result
        assert "Markdown touched: 1" in result
        assert "Non-markdown touched: 1" in result

    def test_excludes_removed_files(self):
        pr_files = [
            {"filename": "keep.py", "status": "modified"},
            {"filename": "deleted.py", "status": "removed"},
        ]
        result = _build_agent_output_summary("agent", 1, pr_files)
        assert "Changed files: 1" in result
        assert "deleted.py" not in result

    def test_skips_files_without_filename(self):
        pr_files = [
            {"filename": "valid.py", "status": "modified"},
            {"status": "modified"},  # missing filename key
            {"filename": "", "status": "modified"},  # empty filename
        ]
        result = _build_agent_output_summary("agent", 1, pr_files)
        assert "Changed files: 1" in result

    def test_contains_full_file_note(self):
        result = _build_agent_output_summary("agent", 1, [])
        assert "Full file contents were intentionally not reposted" in result
