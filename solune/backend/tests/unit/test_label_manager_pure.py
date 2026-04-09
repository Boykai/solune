"""Unit tests for label_manager pure functions — build, parse, status color."""

from __future__ import annotations

import pytest

from src.services.copilot_polling.label_manager import (
    LABEL_PATTERN,
    LABEL_PREFIX,
    ParsedLabel,
    _status_color,
    build_label_name,
    parse_label,
)

# ── build_label_name ───────────────────────────────────────────────


class TestBuildLabelName:
    """Tests for build_label_name()."""

    def test_basic(self):
        assert build_label_name(1, "build", "running") == "solune:pipeline:1:stage:build:running"

    def test_large_run_id(self):
        result = build_label_name(999999, "deploy", "completed")
        assert result == "solune:pipeline:999999:stage:deploy:completed"

    def test_stage_with_hyphens(self):
        result = build_label_name(42, "pre-deploy", "pending")
        assert result == "solune:pipeline:42:stage:pre-deploy:pending"

    def test_roundtrip_with_parse(self):
        """build → parse should be lossless."""
        label = build_label_name(7, "test", "failed")
        parsed = parse_label(label)
        assert parsed is not None
        assert parsed.run_id == 7
        assert parsed.stage_id == "test"
        assert parsed.status == "failed"
        assert parsed.full_name == label


# ── parse_label ────────────────────────────────────────────────────


class TestParseLabel:
    """Tests for parse_label()."""

    def test_valid_label(self):
        parsed = parse_label("solune:pipeline:1:stage:build:running")
        assert parsed is not None
        assert parsed.run_id == 1
        assert parsed.stage_id == "build"
        assert parsed.status == "running"
        assert parsed.full_name == "solune:pipeline:1:stage:build:running"

    def test_returns_none_for_non_pipeline_label(self):
        assert parse_label("bug") is None
        assert parse_label("enhancement") is None
        assert parse_label("") is None

    def test_returns_none_for_malformed_pipeline_label(self):
        assert parse_label("solune:pipeline:notanumber:stage:build:running") is None
        assert parse_label("solune:pipeline:1:build:running") is None  # missing "stage:"

    def test_returns_none_for_partial_match(self):
        assert parse_label("solune:pipeline:1") is None
        assert parse_label("solune:pipeline:") is None

    def test_returns_none_for_status_with_uppercase(self):
        """Status must be lowercase per the regex."""
        assert parse_label("solune:pipeline:1:stage:build:RUNNING") is None

    @pytest.mark.parametrize(
        "status",
        ["pending", "running", "completed", "failed", "skipped", "cancelled"],
    )
    def test_all_known_statuses_parse(self, status: str):
        label = f"solune:pipeline:10:stage:deploy:{status}"
        parsed = parse_label(label)
        assert parsed is not None
        assert parsed.status == status

    def test_returns_parsed_label_type(self):
        parsed = parse_label("solune:pipeline:1:stage:build:running")
        assert isinstance(parsed, ParsedLabel)


# ── _status_color ──────────────────────────────────────────────────


class TestStatusColor:
    """Tests for _status_color()."""

    @pytest.mark.parametrize(
        "status,expected_color",
        [
            ("pending", "d4c5f9"),
            ("running", "0e8a16"),
            ("completed", "1d76db"),
            ("failed", "e11d48"),
            ("skipped", "6b7280"),
            ("cancelled", "fbbf24"),
        ],
    )
    def test_known_statuses(self, status: str, expected_color: str):
        assert _status_color(status) == expected_color

    def test_unknown_status_falls_back_to_default(self):
        assert _status_color("unknown") == "d4c5f9"
        assert _status_color("") == "d4c5f9"


# ── LABEL_PREFIX and LABEL_PATTERN constants ───────────────────────


class TestLabelConstants:
    """Verify module-level constants."""

    def test_label_prefix(self):
        assert LABEL_PREFIX == "solune:pipeline:"

    def test_label_pattern_matches_valid(self):
        assert LABEL_PATTERN.match("solune:pipeline:42:stage:build:running") is not None

    def test_label_pattern_rejects_invalid(self):
        assert LABEL_PATTERN.match("random:label") is None
