"""Regression tests for generated Bug Basher spec artifacts."""

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
FEATURE_ROOT = REPO_ROOT / "specs" / "002-bug-basher"
FRONTEND_PACKAGE_JSON = REPO_ROOT / "solune" / "frontend" / "package.json"
TODO_MARKER = "TODO(bug-bash):"
TODO_FILE_GUIDANCE = "file's native comment syntax"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _referenced_npm_scripts(path: Path) -> set[str]:
    return set(re.findall(r"npm run ([a-zA-Z0-9:-]+)", _read_text(path)))


class TestFrontendValidationCommands:
    """The bug-bash docs should only reference real frontend scripts."""

    def test_spec_references_only_existing_frontend_scripts(self):
        frontend_scripts = set(
            json.loads(FRONTEND_PACKAGE_JSON.read_text(encoding="utf-8"))["scripts"]
        )

        referenced_scripts = _referenced_npm_scripts(
            FEATURE_ROOT / "plan.md"
        ) | _referenced_npm_scripts(FEATURE_ROOT / "quickstart.md")

        assert referenced_scripts <= frontend_scripts
        assert "type-check" in referenced_scripts


class TestTodoMarkerDocumentation:
    """TODO guidance should work across Python and TypeScript files."""

    def test_spec_and_supporting_docs_use_language_agnostic_todo_guidance(self):
        for path in (
            FEATURE_ROOT / "spec.md",
            FEATURE_ROOT / "plan.md",
            FEATURE_ROOT / "data-model.md",
            FEATURE_ROOT / "quickstart.md",
        ):
            content = _read_text(path)
            assert TODO_MARKER in content
            assert TODO_FILE_GUIDANCE in content

    def test_contract_still_accepts_python_and_typescript_todo_prefixes(self):
        contract = _read_text(FEATURE_ROOT / "contracts" / "review-process.yaml")

        assert 'pattern: "^(#|//) TODO\\\\(bug-bash\\\\):"' in contract
