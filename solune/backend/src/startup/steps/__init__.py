"""Ordered list of all startup steps."""

from src.startup.protocol import Step
from src.startup.steps.s01_logging import LoggingStep
from src.startup.steps.s02_asyncio_exc import AsyncioExcHandlerStep
from src.startup.steps.s03_database import DatabaseStep
from src.startup.steps.s04_pipeline_cache import PipelineCacheStep
from src.startup.steps.s05_done_items_cache import DoneItemsCacheStep
from src.startup.steps.s06_singleton_svcs import SingletonServicesStep
from src.startup.steps.s07_alert_dispatcher import AlertDispatcherStep
from src.startup.steps.s08_otel import OtelStep
from src.startup.steps.s09_sentry import SentryStep
from src.startup.steps.s10_signal_ws import SignalWsStep
from src.startup.steps.s11_copilot_polling import CopilotPollingStep
from src.startup.steps.s12_multi_project import MultiProjectStep
from src.startup.steps.s13_pipeline_restore import PipelineRestoreStep
from src.startup.steps.s14_agent_mcp_sync import AgentMcpSyncStep
from src.startup.steps.s15_background_loops import BackgroundLoopsStep

STARTUP_STEPS: list[Step] = [
    LoggingStep(),
    AsyncioExcHandlerStep(),
    DatabaseStep(),
    PipelineCacheStep(),
    DoneItemsCacheStep(),
    SingletonServicesStep(),
    AlertDispatcherStep(),
    OtelStep(),
    SentryStep(),
    SignalWsStep(),
    CopilotPollingStep(),
    MultiProjectStep(),
    PipelineRestoreStep(),
    AgentMcpSyncStep(),
    BackgroundLoopsStep(),
]

__all__ = ["STARTUP_STEPS"]
