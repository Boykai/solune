"""Unit tests for import URL validation."""

from __future__ import annotations

import re

# The URL regex used in the apps API for import validation
_GITHUB_URL_RE = re.compile(
    r"^https://github\.com/(?P<owner>[a-zA-Z0-9_.-]+)/(?P<repo>[a-zA-Z0-9_.-]+)/?$"
)


class TestImportUrlValidation:
    def test_valid_url(self) -> None:
        m = _GITHUB_URL_RE.match("https://github.com/owner/repo")
        assert m is not None
        assert m.group("owner") == "owner"
        assert m.group("repo") == "repo"

    def test_valid_url_with_trailing_slash(self) -> None:
        m = _GITHUB_URL_RE.match("https://github.com/owner/repo/")
        assert m is not None

    def test_valid_url_with_dots_and_hyphens(self) -> None:
        m = _GITHUB_URL_RE.match("https://github.com/my-org/my.project")
        assert m is not None

    def test_malformed_url_rejected(self) -> None:
        assert _GITHUB_URL_RE.match("not-a-url") is None

    def test_non_github_url_rejected(self) -> None:
        assert _GITHUB_URL_RE.match("https://gitlab.com/owner/repo") is None

    def test_url_with_extra_path_segments(self) -> None:
        assert _GITHUB_URL_RE.match("https://github.com/owner/repo/tree/main") is None

    def test_http_url_rejected(self) -> None:
        assert _GITHUB_URL_RE.match("http://github.com/owner/repo") is None

    def test_url_with_subgroups(self) -> None:
        # GitHub doesn't use subgroups, but ensure the regex handles it
        assert _GITHUB_URL_RE.match("https://github.com/owner/sub/repo") is None

    def test_empty_owner(self) -> None:
        assert _GITHUB_URL_RE.match("https://github.com//repo") is None

    def test_empty_repo(self) -> None:
        assert _GITHUB_URL_RE.match("https://github.com/owner/") is None

    def test_url_with_query_params(self) -> None:
        assert _GITHUB_URL_RE.match("https://github.com/owner/repo?tab=code") is None

    def test_underscore_in_owner(self) -> None:
        m = _GITHUB_URL_RE.match("https://github.com/my_org/my_repo")
        assert m is not None
        assert m.group("owner") == "my_org"
