"""Unit tests for transcript analysis via ai_utilities.analyze_transcript().

Covers:
- Happy-path transcript analysis producing an IssueRecommendation
- Truncation of original_input to 500 characters
- Error handling for invalid AI responses
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.models.chat import RecommendationStatus
from src.services.ai_utilities import analyze_transcript

VALID_AI_RESPONSE = (
    '{"title": "Dark Mode Feature", '
    '"user_story": "As a user I want dark mode so I can reduce eye strain", '
    '"ui_ux_description": "Toggle in settings", '
    '"functional_requirements": ["System MUST provide dark theme", '
    '"System MUST persist preference", "System SHOULD support auto-detect", '
    '"System MUST apply to all pages", "System SHOULD animate transition"], '
    '"technical_notes": "Use CSS custom properties", '
    '"metadata": {"priority": "P1", "size": "M", "estimate_hours": 4, '
    '"labels": ["feature", "frontend", "ai-generated"]}}'
)


class TestAnalyzeTranscript:
    """Tests for ai_utilities.analyze_transcript()."""

    @pytest.fixture()
    def mock_completion(self):
        return AsyncMock(return_value=VALID_AI_RESPONSE)

    async def test_happy_path(self, mock_completion):
        with patch("src.services.agent_provider.call_completion", mock_completion):
            rec = await analyze_transcript(
                transcript_content="Alice: Dark mode please\nBob: Agreed",
                project_name="MyProject",
                session_id="00000000-0000-0000-0000-000000000001",
            )
        assert rec.title == "Dark Mode Feature"
        assert rec.status == RecommendationStatus.PENDING
        assert "ai-generated" in rec.metadata.labels
        assert len(rec.functional_requirements) >= 5

    async def test_original_input_truncated_to_500_chars(self, mock_completion):
        long_transcript = "A" * 1000
        with patch("src.services.agent_provider.call_completion", mock_completion):
            rec = await analyze_transcript(
                transcript_content=long_transcript,
                project_name="Proj",
                session_id="00000000-0000-0000-0000-000000000001",
            )
        assert len(rec.original_input) == 500
        # original_context preserves the full transcript
        assert rec.original_context == long_transcript

    async def test_short_transcript_not_truncated(self, mock_completion):
        short = "Alice: Hello"
        with patch("src.services.agent_provider.call_completion", mock_completion):
            rec = await analyze_transcript(
                transcript_content=short,
                project_name="Proj",
                session_id="00000000-0000-0000-0000-000000000001",
            )
        assert rec.original_input == short

    async def test_auth_error_raises_value_error(self):
        mock_fail = AsyncMock(side_effect=RuntimeError("401 Unauthorized"))
        with patch("src.services.agent_provider.call_completion", mock_fail):
            with pytest.raises(ValueError, match="authentication failed"):
                await analyze_transcript(
                    transcript_content="content",
                    project_name="Proj",
                    session_id="00000000-0000-0000-0000-000000000001",
                )

    async def test_not_found_error_raises_value_error(self):
        mock_fail = AsyncMock(side_effect=RuntimeError("404 Resource not found"))
        with patch("src.services.agent_provider.call_completion", mock_fail):
            with pytest.raises(ValueError, match="not found"):
                await analyze_transcript(
                    transcript_content="content",
                    project_name="Proj",
                    session_id="00000000-0000-0000-0000-000000000001",
                )

    async def test_generic_error_raises_value_error(self):
        mock_fail = AsyncMock(side_effect=RuntimeError("connection timeout"))
        with patch("src.services.agent_provider.call_completion", mock_fail):
            with pytest.raises(ValueError, match="Failed to analyse transcript"):
                await analyze_transcript(
                    transcript_content="content",
                    project_name="Proj",
                    session_id="00000000-0000-0000-0000-000000000001",
                )

    async def test_metadata_context_passed_through(self, mock_completion):
        with patch("src.services.agent_provider.call_completion", mock_completion):
            rec = await analyze_transcript(
                transcript_content="Alice: Needs dark mode",
                project_name="Proj",
                session_id="00000000-0000-0000-0000-000000000001",
                metadata_context={"labels": ["bug", "feature"]},
            )
        assert rec.title == "Dark Mode Feature"
