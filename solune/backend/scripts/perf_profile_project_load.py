#!/usr/bin/env python3
"""
Performance profiling script for initial project load.

Measures wall-clock time for every function in the critical path when a user
selects a GitHub project for the first time (cold cache).

Usage (inside backend container or activated venv):
    python -m scripts.perf_profile_project_load <access_token> <username> [project_id]

If project_id is omitted, the first open project is used.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

# ── Timing infrastructure ──────────────────────────────────────────────


@dataclass
class TimingEntry:
    name: str
    start: float = 0.0
    end: float = 0.0
    duration_ms: float = 0.0
    children: list[TimingEntry] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class Profiler:
    """Hierarchical timer that tracks nested function calls."""

    def __init__(self):
        self.root_entries: list[TimingEntry] = []
        self._stack: list[TimingEntry] = []

    @asynccontextmanager
    async def measure(self, name: str, **meta):
        entry = TimingEntry(name=name, metadata=meta)
        if self._stack:
            self._stack[-1].children.append(entry)
        else:
            self.root_entries.append(entry)
        self._stack.append(entry)
        entry.start = time.perf_counter()
        try:
            yield entry
        finally:
            entry.end = time.perf_counter()
            entry.duration_ms = (entry.end - entry.start) * 1000
            self._stack.pop()

    def report(self) -> str:
        lines = []
        lines.append("")
        lines.append("=" * 80)
        lines.append("  SOLUNE PROJECT LOAD PERFORMANCE PROFILE")
        lines.append("=" * 80)

        total_ms = sum(e.duration_ms for e in self.root_entries)
        lines.append(f"\n  Total wall-clock time: {total_ms:.0f} ms\n")

        for entry in self.root_entries:
            self._format_entry(lines, entry, depth=0)

        lines.append("")
        lines.append("=" * 80)
        lines.append("  BOTTLENECK ANALYSIS")
        lines.append("=" * 80)

        # Flatten and sort by duration
        all_entries = []
        self._flatten(self.root_entries, all_entries)
        all_entries.sort(key=lambda e: e.duration_ms, reverse=True)

        lines.append(f"\n  {'Function':<55} {'Time (ms)':>10} {'% Total':>8}")
        lines.append(f"  {'-'*55} {'-'*10} {'-'*8}")
        for entry in all_entries[:20]:
            pct = (entry.duration_ms / total_ms * 100) if total_ms > 0 else 0
            lines.append(f"  {entry.name:<55} {entry.duration_ms:>10.0f} {pct:>7.1f}%")
            if entry.metadata:
                for k, v in entry.metadata.items():
                    lines.append(f"    └─ {k}: {v}")

        lines.append("")
        return "\n".join(lines)

    def _format_entry(self, lines: list[str], entry: TimingEntry, depth: int):
        indent = "  " + "│  " * depth
        bar_len = min(int(entry.duration_ms / 20), 50)
        bar = "█" * bar_len
        lines.append(f"{indent}├─ {entry.name}: {entry.duration_ms:.0f} ms  {bar}")
        if entry.metadata:
            for k, v in entry.metadata.items():
                lines.append(f"{indent}│  └─ {k}: {v}")
        for child in entry.children:
            self._format_entry(lines, child, depth + 1)

    def _flatten(self, entries: list[TimingEntry], out: list[TimingEntry]):
        for e in entries:
            out.append(e)
            self._flatten(e.children, out)


# ── Profiling functions ────────────────────────────────────────────────


async def profile_project_load(access_token: str, username: str, project_id: str | None = None):
    """Run the full project load profile with cold caches."""

    # Import backend services
    from src.services.cache import cache
    from src.services.github_projects import github_projects_service

    profiler = Profiler()

    # ── Phase 0: Clear all caches to simulate cold start ──
    cache.clear()  # Clear the in-memory cache
    print("✓ Cleared all caches (simulating cold start)")

    # ── Phase 1: List user projects (GET /projects equivalent) ──
    async with profiler.measure("1. list_user_projects (GET /projects)") as e1:
        projects = await github_projects_service.list_user_projects(access_token, username)
        e1.metadata["project_count"] = len(projects)

    if not projects:
        print("ERROR: No projects found for user", username)
        return

    # Select target project
    target = None
    if project_id:
        target = next((p for p in projects if p.project_id == project_id), None)
    if not target:
        target = projects[0]
        project_id = target.project_id

    print(f"✓ Profiling project: {target.name} ({project_id})")

    # Clear caches again before board data fetch
    cache.clear()

    # ── Phase 2: Select project (POST /projects/{id}/select equivalent) ──
    # This normally triggers: session update + copilot polling + agent prefetch
    # We profile resolve_repository separately as it's used by both polling and agents

    async with profiler.measure("2. resolve_repository") as e2:
        from src.utils import resolve_repository
        try:
            owner, repo = await resolve_repository(access_token, project_id)
            e2.metadata["result"] = f"{owner}/{repo}"
        except Exception as ex:
            e2.metadata["error"] = str(ex)
            owner, repo = None, None

    # Clear resolve cache to measure it fresh
    cache.clear()

    # ── Phase 3: List board projects (GET /board/projects equivalent) ──
    async with profiler.measure("3. list_board_projects (GET /board/projects)"):
        board_projects = await github_projects_service.list_user_projects(access_token, username)

    # ── Phase 4: Get board data (GET /board/projects/{id} — THE BIG ONE) ──
    cache.clear()

    async with profiler.measure("4. get_board_data (GET /board/projects/{id})") as e4:
        board_data = await _profile_board_data(profiler, access_token, project_id)
        if board_data:
            total_items = sum(len(col.items) for col in board_data.columns)
            e4.metadata["total_items"] = total_items
            e4.metadata["columns"] = len(board_data.columns)

    # ── Phase 5: Get project settings (GET /settings/project/{id}) ──
    cache.clear()
    async with profiler.measure("5. get_workflow_config (GET /settings/project/{id})") as e5:
        try:
            from src.services.workflow_orchestrator import get_workflow_config
            config = await get_workflow_config(project_id)
            e5.metadata["has_config"] = config is not None
        except Exception as ex:
            e5.metadata["error"] = str(ex)

    # ── Phase 6: List agents (GET /workflow/agents) ──
    cache.clear()
    async with profiler.measure("6. list_agents (GET /workflow/agents)") as e6:
        try:
            from src.services.agents.service import AgentsService
            from src.services.database import get_db
            svc = AgentsService(get_db())
            if owner and repo:
                agents = await svc.list_agents(access_token, owner, repo, project_id)
                e6.metadata["agent_count"] = len(agents)
            else:
                e6.metadata["skipped"] = "no repo resolved"
        except Exception as ex:
            e6.metadata["error"] = str(ex)

    # ── Phase 7: Simulate parallel load (as frontend does) ──
    cache.clear()

    from src.services.workflow_orchestrator import get_workflow_config as _get_wf_config

    async with profiler.measure("7. PARALLEL: board_projects + board_data + settings"):
        tasks = [
            _timed_call(profiler, "7a. list_user_projects (parallel)",
                        github_projects_service.list_user_projects, access_token, username),
            _timed_call(profiler, "7b. get_board_data (parallel)",
                        github_projects_service.get_board_data, access_token, project_id),
        ]
        if owner and repo:
            tasks.append(
                _timed_call(profiler, "7c. get_workflow_config (parallel)",
                            _get_wf_config, project_id)
            )
        await asyncio.gather(*tasks, return_exceptions=True)

    # ── Print report ──
    print(profiler.report())

    # ── Summarize critical path ──
    print("\n" + "=" * 80)
    print("  CRITICAL PATH ANALYSIS")
    print("=" * 80)
    print("""
  The critical path for initial project load (user selects project) is:

  1. POST /projects/{id}/select          (sequential — must complete first)
     ├─ Session update                   (fast, in-memory)
     ├─ resolve_repository()             (GraphQL call if uncached)
     └─ Fire-and-forget: polling + prefetch

  2. PARALLEL (triggered by selectedProjectId change on frontend):
     ├─ GET /board/projects              (list_user_projects GraphQL)
     ├─ GET /board/projects/{id}         (THE BOTTLENECK)
     │   ├─ Paginated GraphQL items fetch
     │   ├─ Sub-issue REST calls (N parallel, semaphore=20)
     │   └─ Reconciliation GraphQL per repo
     ├─ GET /settings/project/{id}       (fast, DB/memory)
     └─ GET /workflow/agents             (fast if cached)

  The user sees the board only after GET /board/projects/{id} completes.
  Everything else can load in parallel or after.
""")


async def _profile_board_data(profiler: Profiler, access_token: str, project_id: str):
    """Profile get_board_data with sub-step instrumentation."""
    from src.models.board import (
        Assignee, BoardColumn, BoardDataResponse, BoardItem, BoardProject,
        ContentType, CustomFieldValue, Label, LinkedPR, PRState, Repository,
        StatusColor, StatusField, StatusOption, SubIssue,
    )
    from src.services.github_projects import github_projects_service as svc
    from src.services.github_projects.graphql import (
        BOARD_GET_PROJECT_ITEMS_QUERY, BOARD_RECONCILE_ITEMS_QUERY,
    )

    board_models = {
        "Assignee": Assignee, "BoardColumn": BoardColumn, "BoardItem": BoardItem,
        "ContentType": ContentType, "CustomFieldValue": CustomFieldValue,
        "Label": Label, "LinkedPR": LinkedPR, "PRState": PRState,
        "Repository": Repository, "StatusColor": StatusColor, "StatusOption": StatusOption,
    }

    all_items = []
    project_meta = None
    page_count = 0

    # Step 4a: Paginated GraphQL fetch
    async with profiler.measure("4a. GraphQL: paginated project items") as e4a:
        has_next_page = True
        after = None
        while has_next_page:
            page_count += 1
            async with profiler.measure(f"4a.{page_count}. GraphQL page {page_count}") as ep:
                data = await svc._graphql(
                    access_token,
                    BOARD_GET_PROJECT_ITEMS_QUERY,
                    {"projectId": project_id, "first": 100, "after": after},
                )
                node = data.get("node")
                if not node:
                    break

                if project_meta is None:
                    status_field_data = node.get("field")
                    if not status_field_data:
                        raise ValueError(f"Project {project_id} has no Status field")
                    status_options = [
                        StatusOption(
                            option_id=opt["id"], name=opt["name"],
                            color=opt.get("color", "GRAY"),
                        )
                        for opt in status_field_data.get("options", [])
                    ]
                    owner_data = node.get("owner", {})
                    project_meta = BoardProject(
                        project_id=project_id,
                        name=node.get("title", ""),
                        description=node.get("shortDescription"),
                        url=node.get("url", ""),
                        owner_login=owner_data.get("login", ""),
                        status_field=StatusField(
                            field_id=status_field_data["id"],
                            options=status_options,
                        ),
                    )

                items_data = node.get("items", {})
                page_info = items_data.get("pageInfo", {})
                page_items = 0
                for item in items_data.get("nodes", []):
                    parsed = svc._parse_board_item(item, board_models)
                    if parsed:
                        all_items.append(parsed)
                        page_items += 1

                ep.metadata["items_parsed"] = page_items
                has_next_page = page_info.get("hasNextPage", False)
                after = page_info.get("endCursor")
                if not after:
                    break

        e4a.metadata["total_pages"] = page_count
        e4a.metadata["total_items"] = len(all_items)

    if project_meta is None:
        print("ERROR: Project metadata not found")
        return None

    # Step 4b: Sub-issue fetching
    from src.constants import SUB_ISSUE_LABEL, StatusNames
    parent_items = [
        item for item in all_items
        if item.content_type == ContentType.ISSUE
        and item.number is not None
        and item.repository
        and not any(lb.name == SUB_ISSUE_LABEL for lb in item.labels)
        and item.status != StatusNames.DONE
    ]

    async with profiler.measure("4b. REST: sub-issue fetching") as e4b:
        e4b.metadata["parent_issues_to_fetch"] = len(parent_items)
        sem = asyncio.Semaphore(20)
        sub_issue_timings = []

        async def fetch_one(board_item):
            t0 = time.perf_counter()
            async with sem:
                try:
                    raw = await svc.get_sub_issues(
                        access_token=access_token,
                        owner=board_item.repository.owner,
                        repo=board_item.repository.name,
                        issue_number=board_item.number,
                    )
                    elapsed = (time.perf_counter() - t0) * 1000
                    sub_issue_timings.append((board_item.number, elapsed, len(raw)))
                    for si in raw:
                        si_assignees = [
                            Assignee(login=a.get("login", ""), avatar_url=a.get("avatar_url", ""))
                            for a in si.get("assignees", []) if isinstance(a, dict)
                        ]
                        si_title = si.get("title", "")
                        si_agent = None
                        if si_title.startswith("[") and "]" in si_title:
                            si_agent = si_title[1:si_title.index("]")]
                        board_item.sub_issues.append(
                            SubIssue(
                                id=si.get("node_id", ""),
                                number=si.get("number", 0),
                                title=si_title,
                                url=si.get("html_url", ""),
                                state=si.get("state", "open"),
                                assigned_agent=si_agent,
                                assignees=si_assignees,
                            )
                        )
                except Exception:
                    elapsed = (time.perf_counter() - t0) * 1000
                    sub_issue_timings.append((board_item.number, elapsed, -1))

        await asyncio.gather(*[fetch_one(item) for item in parent_items])

        total_sub = sum(1 for _, _, c in sub_issue_timings if c > 0)
        e4b.metadata["total_sub_issues_found"] = total_sub
        if sub_issue_timings:
            times = [t for _, t, _ in sub_issue_timings]
            e4b.metadata["avg_per_call_ms"] = f"{sum(times)/len(times):.0f}"
            e4b.metadata["max_per_call_ms"] = f"{max(times):.0f}"
            e4b.metadata["min_per_call_ms"] = f"{min(times):.0f}"
            e4b.metadata["p95_per_call_ms"] = f"{sorted(times)[int(len(times)*0.95)]:.0f}"

    # Step 4c: Reconciliation
    existing_ids = {item.content_id for item in all_items if item.content_id}
    repos_seen = set()
    for item in all_items:
        if item.repository:
            repos_seen.add((item.repository.owner, item.repository.name))

    try:
        from src.services.workflow_orchestrator import get_workflow_config
        config = await get_workflow_config(project_id)
        if config and config.repository_owner and config.repository_name:
            repos_seen.add((config.repository_owner, config.repository_name))
    except Exception:
        pass

    async with profiler.measure("4c. GraphQL: reconciliation") as e4c:
        e4c.metadata["repos_to_reconcile"] = len(repos_seen)
        reconciled_total = 0
        for owner, repo_name in repos_seen:
            async with profiler.measure(f"4c. reconcile {owner}/{repo_name}") as er:
                try:
                    reconciled = await svc._reconcile_board_items(
                        access_token=access_token,
                        owner=owner,
                        repo=repo_name,
                        project_id=project_id,
                        existing_content_ids=existing_ids,
                        limit=100,
                    )
                    count = len(reconciled) if reconciled else 0
                    er.metadata["items_found"] = count
                    reconciled_total += count
                    if reconciled:
                        all_items.extend(reconciled)
                except Exception as ex:
                    er.metadata["error"] = str(ex)

        e4c.metadata["total_reconciled"] = reconciled_total

    # Build columns
    columns = svc._build_board_columns(
        all_items, project_meta.status_field.options, board_models
    )

    return BoardDataResponse(project=project_meta, columns=columns)


async def _timed_call(profiler: Profiler, name: str, func, *args, **kwargs):
    async with profiler.measure(name):
        return await func(*args, **kwargs)


# ── Entry point ────────────────────────────────────────────────────────

async def main():
    access_token = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("GITHUB_TOKEN", "")
    username = sys.argv[2] if len(sys.argv) > 2 else ""
    project_id = sys.argv[3] if len(sys.argv) > 3 else None

    if not access_token or not username:
        print("Usage: python -m scripts.perf_profile_project_load <token> <username> [project_id]")
        sys.exit(1)

    # Initialize the database (required by some services)
    from src.services.database import init_database
    await init_database()

    await profile_project_load(access_token, username, project_id)


if __name__ == "__main__":
    asyncio.run(main())
