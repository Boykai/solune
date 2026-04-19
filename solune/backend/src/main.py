"""FastAPI application entry point."""
# pyright: basic
# reason: Legacy top-level module; pending follow-up typing pass.

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.config import get_settings
from src.exceptions import AppException, RateLimitError
from src.logging_utils import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    """Application lifespan handler — delegates to the startup step runner."""
    from src.services.task_registry import task_registry
    from src.startup import run_shutdown, run_startup
    from src.startup.protocol import StartupContext
    from src.startup.steps import STARTUP_STEPS

    ctx = StartupContext(
        app=_app,
        settings=get_settings(),
        task_registry=task_registry,
    )

    logger.info("Starting Solune API")
    try:
        await run_startup(STARTUP_STEPS, ctx)
        try:
            async with asyncio.TaskGroup() as tg:
                for coro in ctx.background:
                    tg.create_task(coro)
                yield
        except* Exception as eg:
            for exc in eg.exceptions:
                logger.error("Background task failed during lifespan: %s", exc, exc_info=exc)
    finally:
        await run_shutdown(ctx)
        logger.info("Shutting down Solune API")


# ── Backward-compat re-exports for existing tests ──────────────────────────
# These helpers were extracted to src/startup/steps/ as part of the lifespan
# refactor. Re-exporting them here preserves test imports without changes.


async def _auto_start_copilot_polling() -> bool:
    """Backward-compat wrapper: delegates to CopilotPollingStep."""
    from src.startup.steps.s11_copilot_polling import _auto_start_copilot_polling as _impl

    await _impl(get_settings())
    return True


async def _discover_and_register_active_projects() -> int:
    """Backward-compat wrapper: delegates to MultiProjectStep logic."""
    from src.config import get_settings as _get_settings
    from src.startup.steps.s12_multi_project import _discover_and_register_active_projects as _impl

    return await _impl(_get_settings())


async def _restore_app_pipeline_polling() -> int:
    """Backward-compat wrapper: delegates to PipelineRestoreStep logic."""
    from src.startup.steps.s13_pipeline_restore import _restore_app_pipeline_polling as _impl

    return await _impl(get_settings())


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Solune API",
        description="REST API for Solune",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/api/docs" if settings.enable_docs else None,
        redoc_url="/api/redoc" if settings.enable_docs else None,
    )

    # CORS middleware — explicit methods and headers reduce attack surface.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "Accept",
            "X-Request-ID",
            "X-Requested-With",
            "X-CSRF-Token",
        ],
    )

    # Request-ID middleware (must be added after CORS — Starlette LIFO order)
    from src.middleware.request_id import RequestIDMiddleware

    app.add_middleware(RequestIDMiddleware)

    # Content Security Policy middleware
    from src.middleware.csp import CSPMiddleware

    app.add_middleware(CSPMiddleware)

    # CSRF protection — double-submit cookie for state-changing requests
    from src.middleware.csrf import CSRFMiddleware

    app.add_middleware(CSRFMiddleware)

    # Rate limiting — slowapi state + exception handler
    from typing import cast

    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from starlette.types import ExceptionHandler

    from src.middleware.rate_limit import RateLimitKeyMiddleware, limiter

    app.state.limiter = limiter
    app.add_exception_handler(
        RateLimitExceeded,
        cast(ExceptionHandler, _rate_limit_exceeded_handler),
    )
    app.add_middleware(RateLimitKeyMiddleware)

    # Exception handlers
    @app.exception_handler(AppException)
    async def app_exception_handler(_request: Request, exc: AppException) -> JSONResponse:
        headers: dict[str, str] = {}
        if isinstance(exc, RateLimitError):
            headers["Retry-After"] = str(exc.retry_after)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.message,
                "details": exc.details,
            },
            headers=headers or None,
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
        from src.middleware.request_id import request_id_var

        rid = request_id_var.get("")
        logger.exception(
            "Unhandled exception: %s | request_id=%s method=%s path=%s",
            type(exc).__name__,
            rid,
            _request.method,
            _request.url.path,
        )

        # ── Sentry capture (Phase 5) ──
        try:
            import sentry_sdk

            if sentry_sdk.is_initialized():
                with sentry_sdk.new_scope() as scope:
                    scope.set_tag("request_id", rid)
                    scope.set_context(
                        "request",
                        {"path": _request.url.path, "method": _request.method},
                    )
                    sentry_sdk.capture_exception(exc)
        except Exception:
            pass  # Sentry capture is best-effort

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Internal server error"},
        )

    # Include API routes (imported here to avoid circular import)
    from src.api import router as api_router

    app.include_router(api_router, prefix="/api/v1")

    # MCP server configuration discovery endpoint (FR-037)
    # Registered BEFORE the MCP mount so Starlette's router matches
    # the explicit route before the catch-all mount prefix.
    # Available regardless of mcp_server_enabled so clients can check.
    @app.get("/api/v1/mcp/config")
    async def mcp_server_config() -> dict:
        """Return MCP server connection details for external agents."""
        return {
            "server_name": settings.mcp_server_name,
            "enabled": settings.mcp_server_enabled,
            "url": "/api/v1/mcp",
            "transport": "streamable-http",
            "auth": {
                "type": "bearer",
                "description": "Provide a GitHub Personal Access Token (PAT) as a Bearer token.",
            },
        }

    # ── MCP Server (v0.4.0) — mount when enabled ──
    if settings.mcp_server_enabled:
        from src.services.mcp_server import create_mcp_server, get_mcp_app
        from src.services.mcp_server.middleware import McpAuthMiddleware
        from src.services.mcp_server.server import get_token_verifier

        create_mcp_server()
        mcp_app = get_mcp_app()
        verifier = get_token_verifier()
        if verifier is not None:
            mcp_app = McpAuthMiddleware(mcp_app, verifier)
        app.mount("/api/v1/mcp", mcp_app)
        logger.info("MCP server mounted at /api/v1/mcp")

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
