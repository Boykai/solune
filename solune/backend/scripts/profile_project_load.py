#!/usr/bin/env python3
"""
Profile the full project import/load flow.

Measures the time for each API call that fires when a user selects a
GitHub project in the Solune UI.  Simulates the exact frontend sequence:

  Phase 1: POST /projects/{id}/select           (blocking)
  Phase 2: GET  /projects                        (parallel)
           GET  /projects/{id}/tasks              (parallel)
  Phase 3: GET  /board/projects                   (parallel)
           GET  /board/projects/{id}              (parallel — THE HEAVY CALL)
  Phase 4: WS   /projects/{id}/subscribe          (initial_data)

Usage:
    python scripts/profile_project_load.py [--project-id PVT_xxx] [--cold]

    --cold    Flush caches before profiling to simulate first-time load
"""

import argparse
import asyncio
import json
import sys
import time
from dataclasses import dataclass, field

import httpx
import websockets

BASE_URL = "http://localhost:8000/api/v1"
WS_URL = "ws://localhost:8000/api/v1/projects"
SESSION_COOKIE = "session_id=b10974d6-45d8-4cf7-a978-284fdf4e7f6c"
COOKIE_DICT = {"session_id": "b10974d6-45d8-4cf7-a978-284fdf4e7f6c"}


@dataclass
class TimingResult:
    name: str
    duration_ms: float
    status_code: int = 0
    response_size_kb: float = 0.0
    detail: str = ""
    sub_timings: list["TimingResult"] = field(default_factory=list)


async def timed_request(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    name: str,
    **kwargs,
) -> tuple[TimingResult, httpx.Response | None]:
    """Make an HTTP request and return timing + response."""
    start = time.perf_counter()
    try:
        resp = await client.request(method, url, **kwargs)
        elapsed = (time.perf_counter() - start) * 1000
        size_kb = len(resp.content) / 1024
        return TimingResult(
            name=name,
            duration_ms=round(elapsed, 1),
            status_code=resp.status_code,
            response_size_kb=round(size_kb, 1),
        ), resp
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000
        return TimingResult(
            name=name,
            duration_ms=round(elapsed, 1),
            status_code=0,
            detail=f"ERROR: {e}",
        ), None


async def timed_websocket(project_id: str, name: str) -> TimingResult:
    """Connect to WebSocket and measure time to receive initial_data."""
    start = time.perf_counter()
    try:
        uri = f"{WS_URL}/{project_id}/subscribe"
        extra_headers = {"Cookie": SESSION_COOKIE}
        async with websockets.connect(uri, additional_headers=extra_headers) as ws:
            # Wait for initial_data message
            msg_raw = await asyncio.wait_for(ws.recv(), timeout=120)
            elapsed = (time.perf_counter() - start) * 1000
            msg = json.loads(msg_raw)
            msg_type = msg.get("type", "unknown")
            task_count = len(msg.get("tasks", []))
            size_kb = len(str(msg_raw)) / 1024
            return TimingResult(
                name=name,
                duration_ms=round(elapsed, 1),
                response_size_kb=round(size_kb, 1),
                detail=f"type={msg_type}, tasks={task_count}",
            )
    except asyncio.TimeoutError:
        elapsed = (time.perf_counter() - start) * 1000
        return TimingResult(
            name=name,
            duration_ms=round(elapsed, 1),
            detail="TIMEOUT (120s)",
        )
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000
        return TimingResult(
            name=name,
            duration_ms=round(elapsed, 1),
            detail=f"ERROR: {e}",
        )


async def flush_caches(client: httpx.AsyncClient) -> None:
    """Flush backend caches by calling refresh endpoints."""
    print("  Flushing caches (cold-start simulation)...")
    # We don't have a direct cache-flush endpoint, but we can use refresh=true
    # on the next calls. For a true cold-start, we'd need to restart the backend.
    # Instead, we'll note that the first request with refresh=true bypasses cache.
    pass


async def profile_flow(project_id: str, cold: bool) -> list[TimingResult]:
    """Run the full project selection flow with timing."""
    results: list[TimingResult] = []

    async with httpx.AsyncClient(
        cookies=COOKIE_DICT,
        timeout=httpx.Timeout(120.0),
    ) as client:
        refresh_param = "?refresh=true" if cold else ""

        # ── Phase 1: Project Selection (blocking) ──
        print("\n── Phase 1: POST /projects/{id}/select ──")
        t1, resp1 = await timed_request(
            client, "POST",
            f"{BASE_URL}/projects/{project_id}/select",
            "Phase 1: SELECT project",
        )
        results.append(t1)
        print(f"  {t1.duration_ms:>8.1f} ms | {t1.status_code} | {t1.response_size_kb} KB | {t1.name}")

        # ── Phase 2: Invalidation cascade (parallel) ──
        print("\n── Phase 2: Invalidation cascade (parallel) ──")
        phase2_start = time.perf_counter()
        t2a_task = timed_request(
            client, "GET",
            f"{BASE_URL}/projects{refresh_param}",
            "Phase 2a: GET /projects",
        )
        t2b_task = timed_request(
            client, "GET",
            f"{BASE_URL}/projects/{project_id}/tasks{refresh_param}",
            "Phase 2b: GET /projects/{id}/tasks",
        )
        (t2a, r2a), (t2b, r2b) = await asyncio.gather(t2a_task, t2b_task)
        phase2_wall = (time.perf_counter() - phase2_start) * 1000

        # Extract item counts
        if r2a and r2a.status_code == 200:
            data = r2a.json()
            t2a.detail = f"projects={len(data.get('projects', []))}"
        if r2b and r2b.status_code == 200:
            data = r2b.json()
            t2b.detail = f"tasks={len(data.get('tasks', []))}"

        results.extend([t2a, t2b])
        print(f"  {t2a.duration_ms:>8.1f} ms | {t2a.status_code} | {t2a.response_size_kb:>6.1f} KB | {t2a.name} ({t2a.detail})")
        print(f"  {t2b.duration_ms:>8.1f} ms | {t2b.status_code} | {t2b.response_size_kb:>6.1f} KB | {t2b.name} ({t2b.detail})")
        print(f"  {'':>8s}      Phase 2 wall time: {phase2_wall:.1f} ms")

        # ── Phase 3: Board data (parallel with Phase 2 in real UI) ──
        print("\n── Phase 3: Board data ──")
        phase3_start = time.perf_counter()
        t3a_task = timed_request(
            client, "GET",
            f"{BASE_URL}/board/projects{refresh_param}",
            "Phase 3a: GET /board/projects",
        )
        t3b_task = timed_request(
            client, "GET",
            f"{BASE_URL}/board/projects/{project_id}{refresh_param}",
            "Phase 3b: GET /board/projects/{id}",
        )
        (t3a, r3a), (t3b, r3b) = await asyncio.gather(t3a_task, t3b_task)
        phase3_wall = (time.perf_counter() - phase3_start) * 1000

        # Extract details
        if r3a and r3a.status_code == 200:
            data = r3a.json()
            t3a.detail = f"projects={len(data.get('projects', []))}"
        if r3b and r3b.status_code == 200:
            data = r3b.json()
            cols = data.get("columns", [])
            total_items = sum(len(c.get("items", [])) for c in cols)
            t3b.detail = f"columns={len(cols)}, items={total_items}"

        results.extend([t3a, t3b])
        print(f"  {t3a.duration_ms:>8.1f} ms | {t3a.status_code} | {t3a.response_size_kb:>6.1f} KB | {t3a.name} ({t3a.detail})")
        print(f"  {t3b.duration_ms:>8.1f} ms | {t3b.status_code} | {t3b.response_size_kb:>6.1f} KB | {t3b.name} ({t3b.detail})")
        print(f"  {'':>8s}      Phase 3 wall time: {phase3_wall:.1f} ms")

        # ── Phase 4: WebSocket initial_data ──
        print("\n── Phase 4: WebSocket initial_data ──")
        t4 = await timed_websocket(project_id, "Phase 4: WS initial_data")
        results.append(t4)
        print(f"  {t4.duration_ms:>8.1f} ms |     | {t4.response_size_kb:>6.1f} KB | {t4.name} ({t4.detail})")

    return results


def print_summary(results: list[TimingResult], cold: bool) -> None:
    """Print summary table."""
    total_sequential = sum(r.duration_ms for r in results)

    # In the real UI, phases 2+3 run in parallel after phase 1
    phase1 = results[0].duration_ms if results else 0
    phase2_max = max(results[1].duration_ms, results[2].duration_ms) if len(results) > 2 else 0
    phase3_max = max(results[3].duration_ms, results[4].duration_ms) if len(results) > 4 else 0
    phase4 = results[5].duration_ms if len(results) > 5 else 0

    # Phases 2, 3, 4 overlap with each other in the real UI
    estimated_wall = phase1 + max(phase2_max, phase3_max, phase4)

    total_payload = sum(r.response_size_kb for r in results)

    mode = "COLD START (caches flushed)" if cold else "WARM (caches populated)"
    print(f"\n{'='*72}")
    print(f"  PROFILING SUMMARY — {mode}")
    print(f"{'='*72}")
    print(f"")
    print(f"  {'Endpoint':<45} {'Time (ms)':>10} {'Size':>8}")
    print(f"  {'-'*45} {'-'*10} {'-'*8}")
    for r in results:
        status = f" [{r.status_code}]" if r.status_code else ""
        print(f"  {r.name:<45} {r.duration_ms:>10.1f} {r.response_size_kb:>7.1f}K")
    print(f"  {'-'*45} {'-'*10} {'-'*8}")
    print(f"  {'Sum of all requests':<45} {total_sequential:>10.1f} {total_payload:>7.1f}K")
    print(f"")
    print(f"  Estimated real-world wall time:")
    print(f"    Phase 1 (blocking select):   {phase1:>8.1f} ms")
    print(f"    Phase 2 (projects + tasks):  {phase2_max:>8.1f} ms")
    print(f"    Phase 3 (board data):        {phase3_max:>8.1f} ms")
    print(f"    Phase 4 (WS initial_data):   {phase4:>8.1f} ms")
    print(f"    ─────────────────────────────────────")
    print(f"    Phase 1 + max(P2,P3,P4):     {estimated_wall:>8.1f} ms")
    print(f"")

    # Identify top offenders
    sorted_results = sorted(results, key=lambda r: r.duration_ms, reverse=True)
    print(f"  TOP OFFENDERS (sorted by latency):")
    for i, r in enumerate(sorted_results[:5], 1):
        detail = f" — {r.detail}" if r.detail else ""
        print(f"    {i}. {r.name}: {r.duration_ms:.0f} ms ({r.response_size_kb:.0f} KB){detail}")

    print(f"{'='*72}\n")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Profile Solune project load flow")
    parser.add_argument(
        "--project-id",
        default="PVT_kwHOAIsXss4BTGUq",  # @Boykai's Solune (722 items)
        help="GitHub Project V2 node ID to profile",
    )
    parser.add_argument(
        "--cold",
        action="store_true",
        help="Simulate cold start (use refresh=true to bypass caches)",
    )
    args = parser.parse_args()

    print(f"Profiling project load for: {args.project_id}")
    print(f"Mode: {'COLD (refresh=true)' if args.cold else 'WARM (cache-allowed)'}")

    results = await profile_flow(args.project_id, args.cold)
    print_summary(results, args.cold)


if __name__ == "__main__":
    asyncio.run(main())
