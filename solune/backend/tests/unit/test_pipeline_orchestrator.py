"""Unit tests for pipeline_orchestrator — stage sequencing, parallel groups, SSE events."""

import json

import pytest

from src.services.pipeline_orchestrator import (
    PIPELINE_STAGES,
    StageResult,
    run_pipeline,
    stage_completed_event,
    stage_failed_event,
    stage_started_event,
)


# =============================================================================
# SSE Event Helpers
# =============================================================================


class TestSSEEventHelpers:
    """Verify SSE event dict construction."""

    def test_stage_started_event(self):
        evt = stage_started_event("plan")
        assert evt["event"] == "stage_started"
        data = json.loads(evt["data"])
        assert data["stage"] == "plan"

    def test_stage_completed_event(self):
        evt = stage_completed_event("plan", "success")
        assert evt["event"] == "stage_completed"
        data = json.loads(evt["data"])
        assert data["stage"] == "plan"
        assert data["output"] == "success"

    def test_stage_failed_event(self):
        evt = stage_failed_event("plan", "timeout")
        assert evt["event"] == "stage_failed"
        data = json.loads(evt["data"])
        assert data["stage"] == "plan"
        assert data["error"] == "timeout"


# =============================================================================
# StageResult
# =============================================================================


class TestStageResult:
    """Verify StageResult serialization."""

    def test_to_dict_success(self):
        r = StageResult("plan", True, output="ok")
        d = r.to_dict()
        assert d["name"] == "plan"
        assert d["success"] is True
        assert d["output"] == "ok"
        assert d["error"] == ""

    def test_to_dict_failure(self):
        r = StageResult("plan", False, error="boom")
        d = r.to_dict()
        assert d["success"] is False
        assert d["error"] == "boom"


# =============================================================================
# Pipeline Execution
# =============================================================================


class TestRunPipeline:
    """Tests for run_pipeline with serial and parallel stages."""

    @pytest.mark.anyio
    async def test_serial_stages_run_in_order(self):
        """Serial stages in the same group run one at a time."""
        order = []

        async def handler_a(ctx):
            order.append("a")
            return "done_a"

        async def handler_b(ctx):
            order.append("b")
            return "done_b"

        stages = [
            {"name": "a", "agent": "x", "group": 1, "parallel": False},
            {"name": "b", "agent": "x", "group": 1, "parallel": False},
        ]
        context = {"stage_handlers": {"a": handler_a, "b": handler_b}}
        results = await run_pipeline(stages, context)

        assert len(results) == 2
        assert order == ["a", "b"]
        assert results[0].success is True
        assert results[1].success is True

    @pytest.mark.anyio
    async def test_parallel_stages_all_execute(self):
        """Parallel stages in the same group all execute."""
        stages = [
            {"name": "qa", "agent": "x", "group": 2, "parallel": True},
            {"name": "test", "agent": "x", "group": 2, "parallel": True},
        ]
        results = await run_pipeline(stages, {})

        assert len(results) == 2
        assert all(r.success for r in results)

    @pytest.mark.anyio
    async def test_serial_failure_halts_pipeline(self):
        """A failing serial stage stops further execution."""

        async def fail_handler(ctx):
            raise RuntimeError("Stage failed!")

        stages = [
            {"name": "a", "agent": "x", "group": 1, "parallel": False},
            {"name": "b", "agent": "x", "group": 1, "parallel": False},
        ]
        context = {"stage_handlers": {"a": fail_handler}}
        results = await run_pipeline(stages, context)

        assert len(results) == 1
        assert results[0].success is False
        assert "Stage failed" in results[0].error

    @pytest.mark.anyio
    async def test_event_callback_called(self):
        """Event callback receives started and completed events."""
        events = []

        async def callback(evt):
            events.append(evt)

        stages = [
            {"name": "a", "agent": "x", "group": 1, "parallel": False},
        ]
        results = await run_pipeline(stages, {}, event_callback=callback)

        assert len(events) == 2
        assert events[0]["event"] == "stage_started"
        assert events[1]["event"] == "stage_completed"

    @pytest.mark.anyio
    async def test_groups_run_in_order(self):
        """Different groups run in group number order."""
        order = []

        async def handler_g1(ctx):
            order.append("g1")

        async def handler_g2(ctx):
            order.append("g2")

        stages = [
            {"name": "g2_stage", "agent": "x", "group": 2, "parallel": False},
            {"name": "g1_stage", "agent": "x", "group": 1, "parallel": False},
        ]
        context = {"stage_handlers": {"g1_stage": handler_g1, "g2_stage": handler_g2}}
        await run_pipeline(stages, context)

        assert order == ["g1", "g2"]

    @pytest.mark.anyio
    async def test_empty_pipeline(self):
        results = await run_pipeline([], {})
        assert results == []

    @pytest.mark.anyio
    async def test_default_stages_defined(self):
        """PIPELINE_STAGES has expected structure."""
        assert len(PIPELINE_STAGES) > 0
        for stage in PIPELINE_STAGES:
            assert "name" in stage
            assert "agent" in stage
            assert "group" in stage
