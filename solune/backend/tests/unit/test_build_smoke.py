"""Build smoke tests — verify all source modules import without errors.

These tests catch import-time failures (missing dependencies, moved symbols,
broken circular imports) that would cause the application to fail on startup.
This prevents regressions like the Copilot SDK 0.1.0 import breakage where
PermissionHandler moved from copilot.session to copilot.types.
"""

import importlib
import pkgutil
from pathlib import Path

import pytest

SRC_ROOT = Path(__file__).resolve().parent.parent.parent / "src"


def _discover_modules() -> list[str]:
    """Walk src/ and return all importable module names."""
    modules: list[str] = []
    for _importer, modname, _ispkg in pkgutil.walk_packages([str(SRC_ROOT)], prefix="src."):
        modules.append(modname)
    return sorted(modules)


ALL_MODULES = _discover_modules()


class TestAllModulesImport:
    """Every src module must import without raising."""

    @pytest.mark.parametrize("module_name", ALL_MODULES)
    def test_module_imports(self, module_name: str) -> None:
        """Import a single module — catches broken dependencies and moved symbols."""
        importlib.import_module(module_name)


class TestCriticalImports:
    """Verify specific imports that have broken in CI before."""

    def test_fastapi_app_creates(self) -> None:
        """The FastAPI app object must be importable (catches config errors)."""
        from src.main import app

        assert app is not None

    def test_copilot_provider_imports(self) -> None:
        """CopilotClientPool must be importable (SDK import breakage)."""
        from src.services.agent_provider import CopilotClientPool

        assert CopilotClientPool is not None

    def test_config_loads(self) -> None:
        """Settings must instantiate without missing env var errors in test mode."""
        from src.config import get_settings

        settings = get_settings()
        assert settings is not None

    def test_database_module_imports(self) -> None:
        """Database service must import (catches aiosqlite/migration issues)."""
        from src.services.database import get_db

        assert get_db is not None

    def test_all_api_routers_import(self) -> None:
        """All API router modules must import without error."""
        api_dir = SRC_ROOT / "api"
        for py_file in sorted(api_dir.glob("*.py")):
            if py_file.name.startswith("_"):
                continue
            module_name = f"src.api.{py_file.stem}"
            try:
                importlib.import_module(module_name)
            except Exception as exc:  # noqa: BLE001 — reason: test assertion; catches all exceptions to produce test-specific error
                pytest.fail(f"Failed to import {module_name}: {exc}")

    def test_all_middleware_imports(self) -> None:
        """All middleware modules must import without error."""
        mw_dir = SRC_ROOT / "middleware"
        for py_file in sorted(mw_dir.glob("*.py")):
            if py_file.name.startswith("_"):
                continue
            module_name = f"src.middleware.{py_file.stem}"
            try:
                importlib.import_module(module_name)
            except Exception as exc:  # noqa: BLE001 — reason: test assertion; catches all exceptions to produce test-specific error
                pytest.fail(f"Failed to import {module_name}: {exc}")

    def test_all_model_imports(self) -> None:
        """All model modules must import without error."""
        models_dir = SRC_ROOT / "models"
        for py_file in sorted(models_dir.glob("*.py")):
            if py_file.name.startswith("_"):
                continue
            module_name = f"src.models.{py_file.stem}"
            try:
                importlib.import_module(module_name)
            except Exception as exc:  # noqa: BLE001 — reason: test assertion; catches all exceptions to produce test-specific error
                pytest.fail(f"Failed to import {module_name}: {exc}")
