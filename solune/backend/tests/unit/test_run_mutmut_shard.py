"""Unit tests for the mutmut shard runner (scripts/run_mutmut_shard.py).

Validates shard definitions, pyproject.toml path patching, and alignment
with the CI workflow so backend mutation shards don't silently drift.
"""

from __future__ import annotations

import importlib.util
import textwrap
from collections.abc import Callable
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "run_mutmut_shard.py"
_spec = importlib.util.spec_from_file_location("run_mutmut_shard", _SCRIPT)
assert _spec is not None and _spec.loader is not None
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

SHARDS: dict[str, list[str]] = getattr(_mod, "SHARDS")  # noqa: B009
_replace_paths_to_mutate: Callable[[str, list[str]], str] = getattr(_mod, "_replace_paths_to_mutate")  # noqa: B009
_build_paths_block: Callable[[list[str]], str] = getattr(_mod, "_build_paths_block")  # noqa: B009


# ── Shard definition tests ──────────────────────────────────────────────


class TestShardDefinitions:
    """Ensure the SHARDS dict is consistent and complete."""

    def test_all_expected_shards_exist(self) -> None:
        expected = {
            "auth-and-projects",
            "orchestration",
            "app-and-data",
            "agents-and-integrations",
            "api-and-middleware",
        }
        assert set(SHARDS.keys()) == expected

    def test_every_shard_has_at_least_one_path(self) -> None:
        for shard_name, paths in SHARDS.items():
            assert len(paths) > 0, f"Shard {shard_name!r} has no paths"

    def test_no_duplicate_paths_across_shards(self) -> None:
        """Each source path should belong to exactly one shard."""
        seen: dict[str, str] = {}
        for shard_name, paths in SHARDS.items():
            for path in paths:
                if path in seen:
                    pytest.fail(f"Path {path!r} appears in both {seen[path]!r} and {shard_name!r}")
                seen[path] = shard_name

    def test_shard_paths_are_relative(self) -> None:
        """All paths should be relative (no leading /)."""
        for shard_name, paths in SHARDS.items():
            for path in paths:
                assert not path.startswith("/"), (
                    f"Path {path!r} in shard {shard_name!r} is absolute"
                )

    def test_api_and_middleware_shard_covers_expected_paths(self) -> None:
        """The api-and-middleware shard should include api/, middleware/, and utils.py."""
        paths = SHARDS["api-and-middleware"]
        assert "src/api/" in paths
        assert "src/middleware/" in paths
        assert "src/utils.py" in paths


# ── Path block builder tests ────────────────────────────────────────────


class TestBuildPathsBlock:
    def test_single_path_inline(self) -> None:
        result = _build_paths_block(["src/services/cache.py"])
        assert result == 'paths_to_mutate = ["src/services/cache.py"]'

    def test_multiple_paths_multiline(self) -> None:
        result = _build_paths_block(["src/api/", "src/middleware/"])
        assert "paths_to_mutate = [\n" in result
        assert '    "src/api/",' in result
        assert '    "src/middleware/",' in result


# ── Replacement tests ───────────────────────────────────────────────────


class TestReplacePathsToMutate:
    _SAMPLE_TOML = textwrap.dedent("""\
        [tool.mutmut]
        paths_to_mutate = ["src/services/"]
        tests_dir = ["tests/"]
        debug = true
    """)

    def test_replaces_single_line_block(self) -> None:
        result = _replace_paths_to_mutate(self._SAMPLE_TOML, ["src/api/"])
        assert 'paths_to_mutate = ["src/api/"]' in result
        assert 'tests_dir = ["tests/"]' in result  # Untouched

    def test_replaces_with_multiline_block(self) -> None:
        result = _replace_paths_to_mutate(self._SAMPLE_TOML, ["src/api/", "src/middleware/"])
        assert "src/api/" in result
        assert "src/middleware/" in result
        # Original single-line should be gone
        assert 'paths_to_mutate = ["src/services/"]' not in result

    def test_raises_when_no_match(self) -> None:
        with pytest.raises(RuntimeError, match="Could not find"):
            _replace_paths_to_mutate("no mutmut section here", ["src/api/"])

    def test_replaces_multiline_original(self) -> None:
        multiline_toml = textwrap.dedent("""\
            [tool.mutmut]
            paths_to_mutate = [
                "src/services/",
                "src/api/",
            ]
            tests_dir = ["tests/"]
        """)
        result = _replace_paths_to_mutate(multiline_toml, ["src/middleware/"])
        assert 'paths_to_mutate = ["src/middleware/"]' in result
        assert 'tests_dir = ["tests/"]' in result


# ── CI alignment tests ──────────────────────────────────────────────────


class TestCIAlignment:
    """Verify that the workflow matrix matches the SHARDS dict."""

    _WORKFLOW = (
        Path(__file__).resolve().parents[4] / ".github" / "workflows" / "mutation-testing.yml"
    )

    @pytest.mark.skipif(
        not (
            Path(__file__).resolve().parents[4] / ".github" / "workflows" / "mutation-testing.yml"
        ).exists(),
        reason="CI workflow not found (shallow clone or missing file)",
    )
    def test_workflow_matrix_matches_shards(self) -> None:
        """mutation-testing.yml backend matrix should list all shard names."""
        content = self._WORKFLOW.read_text()
        for shard_name in SHARDS:
            assert shard_name in content, (
                f"Shard {shard_name!r} is defined in run_mutmut_shard.py "
                f"but missing from mutation-testing.yml"
            )
