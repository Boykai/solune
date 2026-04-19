"""Individual startup steps — one module per responsibility."""

from src.startup.steps.s01_logging import LoggingStep
from src.startup.steps.s02_asyncio_exception_handler import AsyncioExceptionHandlerStep
from src.startup.steps.s03_database import DatabaseStep
from src.startup.steps.s04_pipeline_state_cache import PipelineStateCacheStep
from src.startup.steps.s05_done_items_cache import DoneItemsCacheStep
from src.startup.steps.s06_singleton_services import SingletonServicesStep
from src.startup.steps.s07_alert_dispatcher import AlertDispatcherStep
from src.startup.steps.s08_otel import OtelStep
from src.startup.steps.s09_sentry import SentryStep
from src.startup.steps.s10_signal_ws_listener import SignalWsListenerStep
from src.startup.steps.s11_copilot_polling import CopilotPollingAutostartStep
from src.startup.steps.s12_multi_project_discovery import MultiProjectDiscoveryStep
from src.startup.steps.s13_app_pipeline_polling_restore import AppPipelinePollingRestoreStep
from src.startup.steps.s14_agent_mcp_sync import AgentMcpSyncStep
from src.startup.steps.s15_background_loops import BackgroundLoopsStep

STARTUP_STEPS = [
    LoggingStep(),
    AsyncioExceptionHandlerStep(),
    DatabaseStep(),
    PipelineStateCacheStep(),
    DoneItemsCacheStep(),
    SingletonServicesStep(),
    AlertDispatcherStep(),
    OtelStep(),
    SentryStep(),
    SignalWsListenerStep(),
    CopilotPollingAutostartStep(),
    MultiProjectDiscoveryStep(),
    AppPipelinePollingRestoreStep(),
    AgentMcpSyncStep(),
    BackgroundLoopsStep(),
]

__all__ = [
    "STARTUP_STEPS",
    "AgentMcpSyncStep",
    "AlertDispatcherStep",
    "AppPipelinePollingRestoreStep",
    "AsyncioExceptionHandlerStep",
    "BackgroundLoopsStep",
    "CopilotPollingAutostartStep",
    "DatabaseStep",
    "DoneItemsCacheStep",
    "LoggingStep",
    "MultiProjectDiscoveryStep",
    "OtelStep",
    "PipelineStateCacheStep",
    "SentryStep",
    "SignalWsListenerStep",
    "SingletonServicesStep",
]
