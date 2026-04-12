"""FastAPI application entry point."""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.config import get_settings, setup_logging
from src.exceptions import AppException, RateLimitError
from src.logging_utils import get_logger
from src.services.bootstrap import (
    auto_start_copilot_polling,
    discover_and_register_active_projects,
    polling_watchdog_loop,
    restore_app_pipeline_polling,
    session_cleanup_loop,
    startup_agent_mcp_sync,
)

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    """Application lifespan handler.

    Uses :class:`asyncio.TaskGroup` for background tasks so they are
    automatically cancelled and awaited on shutdown.  Fire-and-forget
    tasks go through :data:`task_registry` and are drained before the
    database is closed.
    """
    settings = get_settings()
    setup_logging(settings.debug, structured=not settings.debug)
    logger.info("Starting Solune API")

    from src.services.database import close_database, init_database, seed_global_settings
    from src.services.signal_bridge import start_signal_ws_listener, stop_signal_ws_listener
    from src.services.task_registry import task_registry

    db = None
    signal_started = False

    try:
        # Install a global asyncio exception handler so unhandled async
        # errors are logged with context instead of silently swallowed.
        loop = asyncio.get_running_loop()

        def _asyncio_exception_handler(_loop: asyncio.AbstractEventLoop, context: dict) -> None:
            exc = context.get("exception")
            msg = context.get("message", "Unhandled async exception")
            logger.error(
                "Async exception: %s — %s",
                msg,
                exc,
                exc_info=(
                    (type(exc), exc, getattr(exc, "__traceback__", None))
                    if exc is not None
                    else None
                ),
            )

        loop.set_exception_handler(_asyncio_exception_handler)

        # Initialize SQLite database, run migrations, seed global settings
        db = await init_database()
        await seed_global_settings(db)
        _app.state.db = db

        # Load persisted pipeline state from SQLite into L1 caches
        from src.services.pipeline_state_store import init_pipeline_state_store

        await init_pipeline_state_store(db)

        # Initialise Done-items DB cache for cold-start optimisation
        from src.services.done_items_store import init_done_items_store

        await init_done_items_store(db)

        # Register singleton services on app.state for DI (see dependencies.py)
        from src.services.github_projects import github_projects_service
        from src.services.websocket import connection_manager

        _app.state.github_service = github_projects_service
        _app.state.connection_manager = connection_manager

        # ── Observability: Alert dispatcher (Phase 5) ──
        from src.services.alert_dispatcher import AlertDispatcher, set_dispatcher

        _alert_dispatcher = AlertDispatcher(
            webhook_url=settings.alert_webhook_url,
            cooldown_minutes=settings.alert_cooldown_minutes,
        )
        _app.state.alert_dispatcher = _alert_dispatcher
        set_dispatcher(_alert_dispatcher)

        # ── Observability: OpenTelemetry (Phase 5) ──
        if settings.otel_enabled:
            from src.services.otel_setup import init_otel

            tracer, meter = init_otel(settings.otel_service_name, settings.otel_endpoint)
            _app.state.otel_tracer = tracer
            _app.state.otel_meter = meter
        else:
            _app.state.otel_tracer = None
            _app.state.otel_meter = None

        # ── Observability: Sentry (Phase 5) ──
        if settings.sentry_dsn:
            import sentry_sdk
            from sentry_sdk.integrations.fastapi import FastApiIntegration

            sentry_sdk.init(
                dsn=settings.sentry_dsn,
                traces_sample_rate=0,  # avoid double-tracing when OTel is also active
                integrations=[FastApiIntegration()],
            )
            logger.info("Sentry SDK initialised")

        # Start Signal WebSocket listener for inbound messages
        await start_signal_ws_listener()
        signal_started = True

        # Auto-resume Copilot polling so agent pipelines survive restarts
        try:
            await auto_start_copilot_polling()
        except Exception as e:
            logger.exception("Failed to auto-start Copilot polling (non-fatal): %s", e)

        # Discover all projects with active pipelines and register them
        # for multi-project monitoring (survives container restarts).
        try:
            await discover_and_register_active_projects()
        except Exception as e:
            logger.warning("Multi-project discovery failed (non-fatal): %s", e)

        # Restore scoped app-pipeline polling for new-repo / external-repo
        # apps whose polling tasks were lost during the restart.
        try:
            await restore_app_pipeline_polling()
        except Exception as e:
            logger.warning("App-pipeline polling restore failed (non-fatal): %s", e)

        # Agent MCP sync — fire-and-forget via TaskRegistry
        async def _run_startup_agent_mcp_sync_background() -> None:
            try:
                await startup_agent_mcp_sync(db)
            except Exception as e:
                logger.warning("Startup agent MCP sync failed (non-fatal): %s", e)

        task_registry.create_task(_run_startup_agent_mcp_sync_background(), name="startup-mcp-sync")

        # Use TaskGroup for long-running background loops — automatic
        # cancellation and awaiting on exit.
        try:
            async with asyncio.TaskGroup() as tg:
                tg.create_task(session_cleanup_loop())
                tg.create_task(polling_watchdog_loop())
                yield
        except* Exception as eg:
            for exc in eg.exceptions:
                logger.error("Background task failed during lifespan: %s", exc, exc_info=exc)
    finally:
        # Stop known long-lived tasks first so they don't block the drain.
        if signal_started:
            await stop_signal_ws_listener()

        # Drain remaining fire-and-forget tasks tracked by the registry
        # before tearing down the database connection.
        await task_registry.drain(drain_timeout=30.0)

        # Stop Copilot polling if it was auto-started or started via the UI
        try:
            from src.services.copilot_polling import get_polling_status, stop_polling

            if get_polling_status()["is_running"]:
                await stop_polling()
        except Exception as e:
            logger.warning("Error stopping Copilot polling during shutdown: %s", e, exc_info=True)

        if db is not None:
            await close_database()
        logger.info("Shutting down Solune API")


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
