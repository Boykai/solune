"""Tests for the _is_plaintext_token helper in src.services.encryption."""

from __future__ import annotations

import pytest

from src.services.encryption import _is_plaintext_token


class TestIsPlaintextToken:
    """Verify detection of raw GitHub token prefixes."""

    @pytest.mark.parametrize(
        "prefix",
        ["gho_", "ghp_", "ghr_", "ghu_", "ghs_", "github_pat_"],
    )
    def test_recognizes_all_github_prefixes(self, prefix):
        assert _is_plaintext_token(f"{prefix}abc123xyz") is True

    def test_rejects_encrypted_value(self):
        assert _is_plaintext_token("gAAAAA...encrypted_data") is False

    def test_rejects_empty_string(self):
        assert _is_plaintext_token("") is False

    def test_rejects_arbitrary_string(self):
        assert _is_plaintext_token("some_random_value") is False

    def test_case_sensitive(self):
        # GitHub token prefixes are lowercase
        assert _is_plaintext_token("GHO_abc123") is False
        assert _is_plaintext_token("GITHUB_PAT_abc123") is False

    def test_prefix_only(self):
        assert _is_plaintext_token("gho_") is True

    def test_full_realistic_token(self):
        # Realistic token format
        assert _is_plaintext_token("ghp_aBcDeFgHiJkLmNoPqRsTuVwXyZ123456") is True
        assert _is_plaintext_token("github_pat_11ABCDEF0_xYz123456789") is True
