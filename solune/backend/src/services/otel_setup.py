"""OpenTelemetry setup — conditional initialisation gated by ``OTEL_ENABLED``.

This module is only imported when ``settings.otel_enabled`` is ``True``.
When OTel is disabled, the ``get_tracer()`` and ``get_meter()`` helpers
return no-op instances so instrumented code can call them unconditionally.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.logging_utils import get_logger

if TYPE_CHECKING:
    from opentelemetry.metrics import Meter
    from opentelemetry.sdk.trace import SpanProcessor
    from opentelemetry.trace import Tracer

logger = get_logger(__name__)

_tracer: Tracer | None = None
_meter: Meter | None = None


if TYPE_CHECKING:
    _SpanProcessorBase = SpanProcessor
    _TracerBase = Tracer
    _MeterBase = Meter
else:
    _SpanProcessorBase = object
    _TracerBase = object
    _MeterBase = object


class _RequestIDSpanProcessor(_SpanProcessorBase):
    """SpanProcessor that injects the current X-Request-ID into every span."""

    def on_start(self, span: Any, parent_context: Any = None) -> None:
        from src.middleware.request_id import request_id_var

        rid = request_id_var.get("")
        if rid:
            span.set_attribute("request.id", rid)

    def on_end(self, span: Any) -> None:
        pass

    def shutdown(self) -> None:
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True


def init_otel(service_name: str, endpoint: str) -> tuple[Tracer, Meter]:
    """Initialise OTel TracerProvider, MeterProvider, and auto-instrumentors.

    Returns the active ``(Tracer, Meter)`` tuple.
    """
    global _tracer, _meter

    from opentelemetry import metrics, trace
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.instrumentation.sqlite3 import SQLite3Instrumentor
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    try:
        resource = Resource.create({"service.name": service_name})

        # ── Tracing ──
        tracer_provider = TracerProvider(resource=resource)
        span_exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
        tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
        tracer_provider.add_span_processor(_RequestIDSpanProcessor())
        trace.set_tracer_provider(tracer_provider)

        # ── Metrics ──
        metric_exporter = OTLPMetricExporter(endpoint=endpoint, insecure=True)
        metric_reader = PeriodicExportingMetricReader(metric_exporter)
        meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
        metrics.set_meter_provider(meter_provider)

        # ── Auto-instrumentation ──
        FastAPIInstrumentor().instrument()
        HTTPXClientInstrumentor().instrument()
        SQLite3Instrumentor().instrument()

        _tracer = trace.get_tracer(service_name)
        _meter = metrics.get_meter(service_name)

        logger.info(
            "OpenTelemetry initialised: service=%s endpoint=%s",
            service_name,
            endpoint,
        )
        return _tracer, _meter  # noqa: TRY300 — reason: return in try block; acceptable for this pattern
    except Exception as exc:  # noqa: BLE001 — reason: 3rd-party callback; unbounded input
        _tracer = None
        _meter = None
        logger.warning(
            "OpenTelemetry initialisation failed; continuing without telemetry: %s",
            exc,
            exc_info=True,
        )
        return get_tracer(), get_meter()


class _NoOpSpan:
    """Minimal no-op span that satisfies the context-manager protocol."""

    def set_attribute(self, key: str, value: object) -> None:
        pass

    def __enter__(self) -> _NoOpSpan:
        return self

    def __exit__(self, *args: object) -> None:
        pass


class _NoOpTracer(_TracerBase):
    """Lightweight no-op tracer — avoids importing ``opentelemetry``."""

    def start_as_current_span(self, name: str, *args: Any, **kwargs: Any) -> Any:
        return _NoOpSpan()

    def start_span(self, name: str, *args: Any, **kwargs: Any) -> Any:
        return _NoOpSpan()


class _NoOpMeter(_MeterBase):
    """Lightweight no-op meter — avoids importing ``opentelemetry``."""

    def __init__(self) -> None:
        pass  # Skip Meter.__init__ which requires a name parameter

    class _NoOpInstrument:
        def set(self, value: object, attributes: object = None) -> None:
            pass

        def record(self, value: object, attributes: object = None) -> None:
            pass

        def add(self, amount: object, attributes: object = None) -> None:
            pass

    def create_gauge(self, name: str, *args: Any, **kwargs: Any) -> Any:
        return self._NoOpInstrument()

    def create_histogram(self, name: str, *args: Any, **kwargs: Any) -> Any:
        return self._NoOpInstrument()

    def create_counter(self, name: str, *args: Any, **kwargs: Any) -> Any:
        return self._NoOpInstrument()

    def create_up_down_counter(self, name: str, *args: Any, **kwargs: Any) -> Any:
        return self._NoOpInstrument()

    def create_observable_counter(self, name: str, *args: Any, **kwargs: Any) -> Any:
        return self._NoOpInstrument()

    def create_observable_gauge(self, name: str, *args: Any, **kwargs: Any) -> Any:
        return self._NoOpInstrument()

    def create_observable_up_down_counter(self, name: str, *args: Any, **kwargs: Any) -> Any:
        return self._NoOpInstrument()


def get_tracer() -> Tracer:
    """Return the active tracer, or a local no-op tracer (zero OTel imports)."""
    if _tracer is not None:
        return _tracer
    return _NoOpTracer()


def get_meter() -> Meter:
    """Return the active meter, or a local no-op meter (zero OTel imports)."""
    if _meter is not None:
        return _meter
    return _NoOpMeter()
