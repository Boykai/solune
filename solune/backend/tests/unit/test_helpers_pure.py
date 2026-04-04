"""Tests for pure helper functions in src.services.copilot_polling.helpers."""

from __future__ import annotations

from datetime import UTC, datetime

from src.services.copilot_polling.helpers import (
    _build_copilot_review_done_marker,
    _build_copilot_review_request_metadata,
    _extract_copilot_review_requested_at,
    _format_github_timestamp,
    _parse_github_timestamp,
    _upsert_copilot_review_request_metadata,
)


class TestParseGitHubTimestamp:
    """Tests for ISO 8601 timestamp parsing with GitHub's Z form."""

    def test_parses_z_form(self):
        result = _parse_github_timestamp("2025-01-15T10:30:00Z")
        assert result is not None
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 10
        assert result.minute == 30

    def test_parses_offset_form(self):
        result = _parse_github_timestamp("2025-06-01T12:00:00+00:00")
        assert result is not None
        assert result.tzinfo is not None

    def test_none_input(self):
        assert _parse_github_timestamp(None) is None

    def test_empty_string(self):
        assert _parse_github_timestamp("") is None

    def test_invalid_format(self):
        assert _parse_github_timestamp("not-a-date") is None

    def test_partial_timestamp(self):
        result = _parse_github_timestamp("2025-01-15")
        # Should parse as date-only (Python accepts this in fromisoformat)
        assert result is not None
        assert result.year == 2025


class TestFormatGitHubTimestamp:
    """Tests for UTC datetime rendering in GitHub's Z form."""

    def test_utc_datetime(self):
        dt = datetime(2025, 3, 10, 14, 30, 0, tzinfo=UTC)
        result = _format_github_timestamp(dt)
        assert result.endswith("Z")
        assert "2025-03-10T14:30:00" in result
        assert "+00:00" not in result

    def test_roundtrip(self):
        original = datetime(2025, 6, 15, 8, 45, 30, tzinfo=UTC)
        formatted = _format_github_timestamp(original)
        parsed = _parse_github_timestamp(formatted)
        assert parsed == original


class TestExtractCopilotReviewRequestedAt:
    """Tests for extracting copilot-review metadata from text."""

    def test_extracts_from_request_marker(self):
        text = "Issue body\n<!-- solune:copilot-review-requested-at=2025-01-15T10:30:00Z -->"
        result = _extract_copilot_review_requested_at(text)
        assert result is not None
        assert result.year == 2025
        assert result.month == 1

    def test_extracts_from_done_marker(self):
        text = "<!-- solune:copilot-review-requested-at=2025-01-15T10:30:00Z detected-at=2025-01-15T11:00:00Z -->"
        result = _extract_copilot_review_requested_at(text)
        assert result is not None
        assert result.hour == 10

    def test_prefers_done_marker_over_request_marker(self):
        text = (
            "<!-- solune:copilot-review-requested-at=2025-01-15T09:00:00Z -->\n"
            "<!-- solune:copilot-review-requested-at=2025-01-15T10:30:00Z "
            "detected-at=2025-01-15T11:00:00Z -->"
        )
        result = _extract_copilot_review_requested_at(text)
        assert result is not None
        assert result.hour == 10  # From done marker

    def test_none_input(self):
        assert _extract_copilot_review_requested_at(None) is None

    def test_empty_string(self):
        assert _extract_copilot_review_requested_at("") is None

    def test_no_marker(self):
        assert _extract_copilot_review_requested_at("Just a regular body") is None


class TestBuildCopilotReviewRequestMetadata:
    """Tests for rendering the request marker."""

    def test_generates_html_comment(self):
        dt = datetime(2025, 3, 10, 14, 0, 0, tzinfo=UTC)
        result = _build_copilot_review_request_metadata(dt)
        assert result.startswith("<!-- solune:copilot-review-requested-at=")
        assert result.endswith("-->")
        assert "2025-03-10T14:00:00Z" in result

    def test_roundtrip_with_extraction(self):
        dt = datetime(2025, 6, 1, 12, 0, 0, tzinfo=UTC)
        marker = _build_copilot_review_request_metadata(dt)
        extracted = _extract_copilot_review_requested_at(marker)
        assert extracted == dt


class TestBuildCopilotReviewDoneMarker:
    """Tests for the Done marker with embedded metadata."""

    def test_includes_both_timestamps(self):
        requested = datetime(2025, 1, 10, 8, 0, 0, tzinfo=UTC)
        detected = datetime(2025, 1, 10, 9, 30, 0, tzinfo=UTC)
        result = _build_copilot_review_done_marker(requested, detected)
        assert "copilot-review: Done!" in result
        assert "2025-01-10T08:00:00Z" in result
        assert "2025-01-10T09:30:00Z" in result
        assert "detected-at=" in result

    def test_roundtrip_extraction(self):
        requested = datetime(2025, 3, 1, 12, 0, 0, tzinfo=UTC)
        detected = datetime(2025, 3, 1, 13, 0, 0, tzinfo=UTC)
        marker = _build_copilot_review_done_marker(requested, detected)
        extracted = _extract_copilot_review_requested_at(marker)
        assert extracted == requested


class TestUpsertCopilotReviewRequestMetadata:
    """Tests for upserting review request metadata in issue bodies."""

    def test_appends_to_empty_body(self):
        dt = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
        result = _upsert_copilot_review_request_metadata("", dt)
        assert "solune:copilot-review-requested-at=" in result

    def test_appends_to_existing_body(self):
        dt = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
        result = _upsert_copilot_review_request_metadata("Issue description here", dt)
        assert result.startswith("Issue description here")
        assert "solune:copilot-review-requested-at=" in result

    def test_replaces_existing_marker(self):
        dt_old = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
        dt_new = datetime(2025, 6, 1, 12, 0, 0, tzinfo=UTC)
        body_with_marker = _upsert_copilot_review_request_metadata("body text", dt_old)
        updated = _upsert_copilot_review_request_metadata(body_with_marker, dt_new)
        # Should only have one marker
        assert updated.count("solune:copilot-review-requested-at=") == 1
        assert "2025-06-01T12:00:00Z" in updated
        assert "2025-01-01T00:00:00Z" not in updated

    def test_preserves_body_content(self):
        dt = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
        original = "## Task\n\nDo something important\n\n### Notes\n\nExtra info"
        result = _upsert_copilot_review_request_metadata(original, dt)
        assert "## Task" in result
        assert "Do something important" in result
        assert "### Notes" in result

    def test_whitespace_only_body(self):
        dt = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
        result = _upsert_copilot_review_request_metadata("   \n  ", dt)
        assert "solune:copilot-review-requested-at=" in result
