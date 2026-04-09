"""Tests for otel_setup service.

Covers:
- No-op fallback behaviour when OTel is disabled
- _RequestIDSpanProcessor behaviour
- _NoOpTracer and _NoOpMeter context-manager protocols
- get_tracer() / get_meter() factory functions
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.services.otel_setup import (
    _NoOpMeter,
    _NoOpSpan,
    _NoOpTracer,
    _RequestIDSpanProcessor,
    get_meter,
    get_tracer,
)


class TestNoOpSpan:
    """Verify _NoOpSpan satisfies the context-manager protocol."""

    def test_enter_returns_self(self):
        span = _NoOpSpan()
        assert span.__enter__() is span

    def test_exit_does_not_raise(self):
        span = _NoOpSpan()
        span.__exit__(None, None, None)

    def test_set_attribute_is_noop(self):
        span = _NoOpSpan()
        span.set_attribute("key", "value")  # Should not raise

    def test_context_manager_protocol(self):
        with _NoOpSpan() as span:
            span.set_attribute("test.key", 42)


class TestNoOpTracer:
    """Verify _NoOpTracer returns no-op spans."""

    def test_start_as_current_span_returns_noop(self):
        tracer = _NoOpTracer()
        result = tracer.start_as_current_span("test-span")
        assert isinstance(result, _NoOpSpan)

    def test_start_span_returns_noop(self):
        tracer = _NoOpTracer()
        result = tracer.start_span("test-span")
        assert isinstance(result, _NoOpSpan)

    def test_start_as_current_span_context_manager(self):
        tracer = _NoOpTracer()
        with tracer.start_as_current_span("op"):
            pass  # Should not raise


class TestNoOpMeter:
    """Verify _NoOpMeter creates no-op instruments."""

    def test_create_counter(self):
        meter = _NoOpMeter()
        counter = meter.create_counter("requests")
        counter.add(1)  # Should not raise

    def test_create_histogram(self):
        meter = _NoOpMeter()
        hist = meter.create_histogram("latency")
        hist.record(0.5)

    def test_create_gauge(self):
        meter = _NoOpMeter()
        gauge = meter.create_gauge("cpu_usage")
        gauge.set(42.0)

    def test_create_up_down_counter(self):
        meter = _NoOpMeter()
        udc = meter.create_up_down_counter("connections")
        udc.add(1)
        udc.add(-1)

    def test_create_observable_counter(self):
        meter = _NoOpMeter()
        meter.create_observable_counter("obs_requests")

    def test_create_observable_gauge(self):
        meter = _NoOpMeter()
        meter.create_observable_gauge("obs_cpu")

    def test_create_observable_up_down_counter(self):
        meter = _NoOpMeter()
        meter.create_observable_up_down_counter("obs_connections")


class TestGetTracerAndMeter:
    """Verify get_tracer() and get_meter() return correct instances."""

    def test_get_tracer_returns_noop_when_not_initialised(self):
        import src.services.otel_setup as otel_mod

        original = otel_mod._tracer
        try:
            otel_mod._tracer = None
            tracer = get_tracer()
            assert isinstance(tracer, _NoOpTracer)
        finally:
            otel_mod._tracer = original

    def test_get_meter_returns_noop_when_not_initialised(self):
        import src.services.otel_setup as otel_mod

        original = otel_mod._meter
        try:
            otel_mod._meter = None
            meter = get_meter()
            assert isinstance(meter, _NoOpMeter)
        finally:
            otel_mod._meter = original

    def test_get_tracer_returns_real_when_set(self):
        import src.services.otel_setup as otel_mod

        original = otel_mod._tracer
        try:
            mock_tracer = MagicMock()
            otel_mod._tracer = mock_tracer
            assert get_tracer() is mock_tracer
        finally:
            otel_mod._tracer = original

    def test_get_meter_returns_real_when_set(self):
        import src.services.otel_setup as otel_mod

        original = otel_mod._meter
        try:
            mock_meter = MagicMock()
            otel_mod._meter = mock_meter
            assert get_meter() is mock_meter
        finally:
            otel_mod._meter = original


class TestRequestIDSpanProcessor:
    """Verify _RequestIDSpanProcessor injects request IDs into spans."""

    def test_on_start_sets_request_id_attribute(self):
        processor = _RequestIDSpanProcessor()
        mock_span = MagicMock()
        with patch("src.middleware.request_id.request_id_var") as mock_var:
            mock_var.get.return_value = "req-123"
            processor.on_start(mock_span)
        mock_span.set_attribute.assert_called_once_with("request.id", "req-123")

    def test_on_start_skips_when_no_request_id(self):
        processor = _RequestIDSpanProcessor()
        mock_span = MagicMock()
        with patch("src.middleware.request_id.request_id_var") as mock_var:
            mock_var.get.return_value = ""
            processor.on_start(mock_span)
        mock_span.set_attribute.assert_not_called()

    def test_on_end_does_not_raise(self):
        processor = _RequestIDSpanProcessor()
        processor.on_end(MagicMock())

    def test_shutdown_does_not_raise(self):
        processor = _RequestIDSpanProcessor()
        processor.shutdown()

    def test_force_flush_returns_true(self):
        processor = _RequestIDSpanProcessor()
        assert processor.force_flush() is True
