"""Lint canary tests — validate Ruff BLE001 rule behaviour.

Verifies that:
1. An untagged ``except Exception`` handler triggers a BLE001 violation.
2. A tagged handler with a BLE001 noqa directive suppresses the violation.
3. Narrowed exception types do not trigger BLE001.
4. BLE001 is not explicitly ignored in pyproject.toml.

These tests validate rule behaviour via ``--select BLE001`` and serve as
canary guards for the broad-except policy (specs/002-reduce-broad-except,
US1 Acceptance Scenarios 1-3).
"""

import shutil
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
PYPROJECT = BACKEND_ROOT / "pyproject.toml"

# Resolve the ruff binary from the same venv as the running interpreter.
_VENV_BIN = Path(sys.executable).parent
_RUFF = shutil.which("ruff", path=str(_VENV_BIN)) or shutil.which("ruff")


def _run_ruff_ble001(canary_path: str) -> subprocess.CompletedProcess[str]:
    """Run ruff check with BLE001 select on a canary file."""
    assert _RUFF is not None, "ruff not found in venv or PATH"
    return subprocess.run(
        [
            _RUFF,
            "check",
            canary_path,
            "--select",
            "BLE001",
            "--no-fix",
            "--output-format",
            "concise",
        ],
        capture_output=True,
        text=True,
        cwd=str(BACKEND_ROOT),
        timeout=30,
    )


class TestBLE001LintCanary:
    """Validate Ruff BLE001 lint rule behaviour via explicit --select BLE001."""

    def test_untagged_except_exception_triggers_ble001(self):
        """A file with untagged `except Exception` must produce BLE001 violation."""
        canary_code = textwrap.dedent("""\
            try:
                x = 1
            except Exception:
                pass
        """)
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False, dir="/tmp") as f:
            f.write(canary_code)
            f.flush()
            canary_path = f.name

        try:
            result = _run_ruff_ble001(canary_path)
            assert result.returncode != 0, (
                f"Expected non-zero exit for untagged except Exception.\n"
                f"stdout: {result.stdout}\nstderr: {result.stderr}"
            )
            assert "BLE001" in result.stdout, f"Expected BLE001 in output.\nstdout: {result.stdout}"
        finally:
            Path(canary_path).unlink(missing_ok=True)

    def test_tagged_except_exception_passes_ble001(self):
        """A file with a BLE001 noqa directive on the handler must pass cleanly."""
        canary_code = textwrap.dedent("""\
            try:
                x = 1
            except Exception:  # noqa: BLE001 — reason: test canary
                pass
        """)
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False, dir="/tmp") as f:
            f.write(canary_code)
            f.flush()
            canary_path = f.name

        try:
            result = _run_ruff_ble001(canary_path)
            assert result.returncode == 0, (
                f"Expected zero exit for tagged except Exception.\n"
                f"stdout: {result.stdout}\nstderr: {result.stderr}"
            )
        finally:
            Path(canary_path).unlink(missing_ok=True)

    def test_ble001_not_in_ignore_list(self):
        """BLE001 must NOT appear in the ignore or per-file-ignores lists."""
        import tomllib

        with PYPROJECT.open("rb") as f:
            config = tomllib.load(f)

        lint_config = config.get("tool", {}).get("ruff", {}).get("lint", {})
        ignore_list = lint_config.get("ignore", [])
        per_file_ignores = lint_config.get("per-file-ignores", {})

        assert "BLE001" not in ignore_list, "BLE001 should not be in [tool.ruff.lint] ignore list"
        for pattern, rules in per_file_ignores.items():
            assert "BLE001" not in rules, f"BLE001 should not be in per-file-ignores for {pattern}"

    @pytest.mark.parametrize(
        "exception_type",
        ["ValueError", "RuntimeError", "OSError", "KeyError"],
    )
    def test_specific_exception_does_not_trigger_ble001(self, exception_type: str):
        """Narrowed exception types should NOT trigger BLE001."""
        canary_code = textwrap.dedent(f"""\
            try:
                x = 1
            except {exception_type}:
                pass
        """)
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False, dir="/tmp") as f:
            f.write(canary_code)
            f.flush()
            canary_path = f.name

        try:
            result = _run_ruff_ble001(canary_path)
            assert result.returncode == 0, (
                f"except {exception_type} should not trigger BLE001.\n"
                f"stdout: {result.stdout}\nstderr: {result.stderr}"
            )
        finally:
            Path(canary_path).unlink(missing_ok=True)
