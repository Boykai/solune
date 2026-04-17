"""Tests for admin guard middleware path enforcement."""

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from src.models.guard import GuardResult


async def _ok(_request):
    return JSONResponse({"ok": True})


def _make_client() -> TestClient:
    from src.middleware.admin_guard import AdminGuardMiddleware

    app = Starlette(routes=[Route("/test", _ok)])
    app.add_middleware(AdminGuardMiddleware)
    return TestClient(app)


class TestAdminGuardMiddleware:
    def test_requests_without_target_paths_pass_through(self):
        client = _make_client()

        response = client.get("/test")

        assert response.status_code == 200
        assert response.json() == {"ok": True}

    def test_locked_paths_return_403(self, monkeypatch):
        monkeypatch.setattr(
            "src.middleware.admin_guard.check_guard",
            lambda _paths, elevated=False: GuardResult(locked=[".github/workflows/ci.yml"]),
        )
        client = _make_client()

        response = client.get("/test", headers={"X-Target-Paths": ".github/workflows/ci.yml"})

        assert response.status_code == 403
        assert "@adminlock" in response.text
        # Error message must NOT reveal the exact protected paths (info-disclosure fix)
        assert ".github/workflows/ci.yml" not in response.text

    def test_admin_paths_require_elevation(self, monkeypatch):
        monkeypatch.setattr(
            "src.middleware.admin_guard.check_guard",
            lambda _paths, elevated=False: GuardResult(
                admin_blocked=["solune/backend/src/main.py"]
            ),
        )
        client = _make_client()

        response = client.get("/test", headers={"X-Target-Paths": "solune/backend/src/main.py"})

        assert response.status_code == 403
        assert "@admin" in response.text
        # Error message must NOT reveal bypass instructions or protected paths
        assert "X-Guard-Elevated: true" not in response.text
        assert "solune/backend/src/main.py" not in response.text

    def test_trims_target_paths_and_passes_elevation_to_guard(self, monkeypatch):
        captured: dict[str, object] = {}

        def fake_check_guard(paths, elevated=False):
            captured["paths"] = paths
            captured["elevated"] = elevated
            return GuardResult(allowed=paths)

        monkeypatch.setattr("src.middleware.admin_guard.check_guard", fake_check_guard)
        client = _make_client()

        response = client.get(
            "/test",
            headers={
                "X-Target-Paths": " solune/backend/src/main.py , apps/test-app/README.md ",
                "X-Guard-Elevated": "true",
            },
        )

        assert response.status_code == 200
        assert captured == {
            "paths": ["solune/backend/src/main.py", "apps/test-app/README.md"],
            "elevated": True,
        }

    def test_empty_target_paths_after_trimming_pass_through(self):
        client = _make_client()

        response = client.get("/test", headers={"X-Target-Paths": " ,  , "})

        assert response.status_code == 200
        assert response.json() == {"ok": True}

    def test_error_responses_do_not_leak_protected_paths(self, monkeypatch):
        """Regression: 403 responses must not reveal the exact file paths that are
        protected.  Leaking the paths aids an attacker in mapping the guard config."""
        secret_path = "infra/secrets/production.env"
        monkeypatch.setattr(
            "src.middleware.admin_guard.check_guard",
            lambda _paths, elevated=False: GuardResult(locked=[secret_path]),
        )
        client = _make_client()

        response = client.get("/test", headers={"X-Target-Paths": secret_path})

        assert response.status_code == 403
        assert secret_path not in response.text

    def test_error_responses_do_not_leak_bypass_instructions(self, monkeypatch):
        """Regression: 403 responses must not instruct the caller on how to
        bypass the guard (e.g. 'Set X-Guard-Elevated: true to override')."""
        monkeypatch.setattr(
            "src.middleware.admin_guard.check_guard",
            lambda _paths, elevated=False: GuardResult(admin_blocked=["src/main.py"]),
        )
        client = _make_client()

        response = client.get("/test", headers={"X-Target-Paths": "src/main.py"})

        assert response.status_code == 403
        # Must not contain bypass instructions
        assert "X-Guard-Elevated" not in response.text
        assert "override" not in response.text.lower()
        # Must not reveal the protected path
        assert "src/main.py" not in response.text

    def test_locked_multiple_paths_count_in_message(self, monkeypatch):
        """When multiple paths are locked, the error message should report
        the correct count without revealing individual paths."""
        locked_paths = [".github/workflows/ci.yml", "infra/secrets/prod.env", ".env"]
        monkeypatch.setattr(
            "src.middleware.admin_guard.check_guard",
            lambda _paths, elevated=False: GuardResult(locked=locked_paths),
        )
        client = _make_client()

        response = client.get(
            "/test",
            headers={"X-Target-Paths": ",".join(locked_paths)},
        )

        assert response.status_code == 403
        assert "3 path(s)" in response.text
        # None of the actual paths should appear in the response body
        for p in locked_paths:
            assert p not in response.text

    def test_admin_blocked_multiple_paths_count_in_message(self, monkeypatch):
        """When multiple paths require elevation, the error message should
        report the correct count without revealing individual paths."""
        blocked_paths = ["src/main.py", "src/config.py"]
        monkeypatch.setattr(
            "src.middleware.admin_guard.check_guard",
            lambda _paths, elevated=False: GuardResult(admin_blocked=blocked_paths),
        )
        client = _make_client()

        response = client.get(
            "/test",
            headers={"X-Target-Paths": ",".join(blocked_paths)},
        )

        assert response.status_code == 403
        assert "2 path(s)" in response.text
        for p in blocked_paths:
            assert p not in response.text
