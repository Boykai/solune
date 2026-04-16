"""PipelineService — CRUD operations for Agent Pipeline configurations."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

import aiosqlite

from src.logging_utils import get_logger
from src.models.pipeline import (
    ExecutionGroup,
    PipelineConfig,
    PipelineConfigCreate,
    PipelineConfigListResponse,
    PipelineConfigSummary,
    PipelineConfigUpdate,
    PipelineStage,
    ProjectPipelineAssignment,
)

logger = get_logger(__name__)

_CANONICAL_PROJECT_SETTINGS_USER = "__workflow__"

# Column allowlist for dynamic SET clauses
_PIPELINE_COLUMNS = frozenset({"name", "description", "stages", "updated_at"})


# ---------------------------------------------------------------------------
# Helper to build a standard agent dict with model_id/model_name set to Auto
# ---------------------------------------------------------------------------
def _agent(aid: str, slug: str, display: str) -> dict:
    return {
        "id": aid,
        "agent_slug": slug,
        "agent_display_name": display,
        "model_id": "",
        "model_name": "",
        "tool_ids": [],
        "tool_count": 0,
        "config": {},
    }


def _group(gid: str, order: int, agents: list[dict], mode: str = "sequential") -> dict:
    """Build an execution group dict for preset definitions."""
    return {
        "id": gid,
        "order": order,
        "execution_mode": mode,
        "agents": agents,
    }


def _grouped_stage(
    sid: str,
    name: str,
    order: int,
    gid: str,
    agents: list[dict],
    mode: str = "sequential",
) -> dict:
    """Build a stage dict with a single execution group."""
    return {
        "id": sid,
        "name": name,
        "order": order,
        "groups": [_group(gid, 0, agents, mode)],
        # For backward compatibility, expose a flattened list of agents at the stage level.
        "agents": agents,
        "execution_mode": mode,
    }


# Preset pipeline definitions — matches frontend preset-pipelines.ts.
# Each preset uses a single "In progress" stage with one sequential Group 1.
_PRESET_DEFINITIONS = [
    # ── GitHub ────────────────────────────────────────────────────────
    {
        "preset_id": "github",
        "name": "GitHub",
        "description": "Single-agent pipeline powered by GitHub Copilot.",
        "stages": [
            _grouped_stage(
                "preset-gh-stage-1",
                "In progress",
                0,
                "preset-gh-group-1",
                [_agent("preset-gh-a1", "copilot", "GitHub Copilot")],
            ),
        ],
    },
    # ── Spec Kit ──────────────────────────────────────────────────────
    {
        "preset_id": "spec-kit",
        "name": "Spec Kit",
        "description": "Full specification workflow: specify → plan → tasks → analyze → implement.",
        "stages": [
            _grouped_stage(
                "preset-sk-stage-1",
                "In progress",
                0,
                "preset-sk-group-1",
                [
                    _agent("preset-sk-a1", "speckit.specify", "Spec Kit - Specify"),
                    _agent("preset-sk-a2", "speckit.plan", "Spec Kit - Plan"),
                    _agent("preset-sk-a3", "speckit.tasks", "Spec Kit - Tasks"),
                    _agent("preset-sk-a4", "speckit.analyze", "Spec Kit - Analyze"),
                    _agent("preset-sk-a5", "speckit.implement", "Spec Kit - Implement"),
                ],
            ),
        ],
    },
    # ── Default ───────────────────────────────────────────────────────
    {
        "preset_id": "default",
        "name": "Default",
        "description": "End-to-end workflow: specify, plan, tasks, analyze, implement, QA, test, lint, review, and judge.",
        "stages": [
            _grouped_stage(
                "preset-df-stage-1",
                "In progress",
                0,
                "preset-df-group-1",
                [
                    _agent("preset-df-a1", "speckit.specify", "Spec Kit - Specify"),
                    _agent("preset-df-a2", "speckit.plan", "Spec Kit - Plan"),
                    _agent("preset-df-a3", "speckit.tasks", "Spec Kit - Tasks"),
                    _agent("preset-df-a4", "speckit.analyze", "Spec Kit - Analyze"),
                    _agent("preset-df-a5", "speckit.implement", "Spec Kit - Implement"),
                    _agent("preset-df-a6", "quality-assurance", "Quality Assurance"),
                    _agent("preset-df-a7", "tester", "Tester"),
                    _agent("preset-df-a8", "linter", "Linter"),
                    _agent("preset-df-a9", "copilot-review", "Copilot Review"),
                    _agent("preset-df-a10", "judge", "Judge"),
                ],
            ),
        ],
    },
    # ── App Builder ───────────────────────────────────────────────────
    {
        "preset_id": "app-builder",
        "name": "App Builder",
        "description": "Full stack workflow with architecture, QA, testing, linting, review, and judging.",
        "stages": [
            _grouped_stage(
                "preset-ab-stage-1",
                "In progress",
                0,
                "preset-ab-group-1",
                [
                    _agent("preset-ab-a1", "speckit.specify", "Spec Kit - Specify"),
                    _agent("preset-ab-a2", "speckit.plan", "Spec Kit - Plan"),
                    _agent("preset-ab-a3", "speckit.tasks", "Spec Kit - Tasks"),
                    _agent("preset-ab-a4", "speckit.analyze", "Spec Kit - Analyze"),
                    _agent("preset-ab-a5", "speckit.implement", "Spec Kit - Implement"),
                    _agent("preset-ab-a6", "architect", "Architect"),
                    _agent("preset-ab-a7", "quality-assurance", "Quality Assurance"),
                    _agent("preset-ab-a8", "tester", "Tester"),
                    _agent("preset-ab-a9", "linter", "Linter"),
                    _agent("preset-ab-a10", "copilot-review", "Copilot Review"),
                    _agent("preset-ab-a11", "judge", "Judge"),
                ],
            ),
        ],
    },
]


class PipelineService:
    """Manages pipeline configuration records in the SQLite database."""

    def __init__(self, db: aiosqlite.Connection) -> None:
        self._db = db

    # ── Helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _normalize_tool_counts(stages: list[PipelineStage]) -> list[PipelineStage]:
        """Ensure tool_count matches len(tool_ids) for every agent node."""
        for stage in stages:
            for group in stage.groups:
                for agent in group.agents:
                    agent.tool_count = len(agent.tool_ids)
            # Also normalize legacy agents field for backward compat
            for agent in stage.agents:
                agent.tool_count = len(agent.tool_ids)
        return stages

    @staticmethod
    def _normalize_execution_modes(stages: list[PipelineStage]) -> list[PipelineStage]:
        """Ensure execution_mode is valid for every group.

        Per-group mode is preserved regardless of agent count (user intent).
        Invalid values are corrected to "sequential".
        """
        for stage in stages:
            for group in stage.groups:
                if group.execution_mode not in ("sequential", "parallel"):
                    group.execution_mode = "sequential"
            # Also normalize stage-level mode for backward compat
            if stage.execution_mode not in ("sequential", "parallel"):
                stage.execution_mode = "sequential"
        return stages

    @staticmethod
    def _normalize_groups(stages: list[PipelineStage]) -> list[PipelineStage]:
        """Ensure every stage has groups populated (migrate legacy format on write).

        If a stage has no groups but has agents, wrap agents in a single group.
        Also sync stage.agents as a flattened view of group agents for backward compat.
        """
        for stage in stages:
            if not stage.groups and stage.agents:
                logger.info(
                    "legacy_format_encountered: format_type=%s context=%s stage_id=%s",
                    "stage_without_groups",
                    "normalize_groups",
                    stage.id,
                )
                stage.groups = [
                    ExecutionGroup(
                        id=str(uuid.uuid4()),
                        order=0,
                        execution_mode=stage.execution_mode or "sequential",
                        agents=list(stage.agents),
                    )
                ]
            # Sync stage.agents from groups for backward-compat consumers
            if stage.groups:
                stage.agents = [a for g in stage.groups if g.agents for a in g.agents]
        return stages

    @staticmethod
    def _row_to_config(row_dict: dict) -> PipelineConfig:
        """Convert a database row dict to a PipelineConfig model."""
        stages_raw = json.loads(row_dict.get("stages", "[]"))
        stages = [PipelineStage(**s) for s in stages_raw]
        return PipelineConfig(
            id=row_dict["id"],
            project_id=row_dict["project_id"],
            name=row_dict["name"],
            description=row_dict.get("description", ""),
            stages=stages,
            is_preset=bool(row_dict.get("is_preset", 0)),
            preset_id=row_dict.get("preset_id", ""),
            created_at=row_dict["created_at"],
            updated_at=row_dict["updated_at"],
        )

    # ── List ──────────────────────────────────────────────────────────

    async def list_pipelines(
        self,
        project_id: str,
        sort: str = "updated_at",
        order: str = "desc",
        github_user_id: str = "",
    ) -> PipelineConfigListResponse:
        """List all pipeline configurations for a user with enriched summaries."""
        allowed_sort = {"updated_at", "name", "created_at"}
        allowed_order = {"asc", "desc"}
        sort_col = sort if sort in allowed_sort else "updated_at"
        sort_dir = order if order in allowed_order else "desc"

        if github_user_id:
            cursor = await self._db.execute(
                f"SELECT * FROM pipeline_configs WHERE (github_user_id = ? OR github_user_id = '') ORDER BY {sort_col} {sort_dir.upper()}",
                (github_user_id,),
            )
        else:
            cursor = await self._db.execute(
                f"SELECT * FROM pipeline_configs WHERE project_id = ? ORDER BY {sort_col} {sort_dir.upper()}",
                (project_id,),
            )
        rows = await cursor.fetchall()

        summaries: list[PipelineConfigSummary] = []
        for row in rows:
            row_dict = dict(row)
            stages = json.loads(row_dict.get("stages", "[]"))
            parsed_stages = [PipelineStage(**s) for s in stages]
            # Count agents from groups (preferred) or fallback to legacy agents field
            agent_count = sum(
                sum(len(g.agents) for g in s.groups) if s.groups else len(s.agents)
                for s in parsed_stages
            )
            total_tool_count = sum(
                a.tool_count for s in parsed_stages for g in (s.groups or []) for a in g.agents
            ) + sum(a.tool_count for s in parsed_stages if not s.groups for a in s.agents)
            summaries.append(
                PipelineConfigSummary(
                    id=row_dict["id"],
                    name=row_dict["name"],
                    description=row_dict.get("description", ""),
                    stage_count=len(parsed_stages),
                    agent_count=agent_count,
                    total_tool_count=total_tool_count,
                    is_preset=bool(row_dict.get("is_preset", 0)),
                    preset_id=row_dict.get("preset_id", ""),
                    stages=parsed_stages,
                    updated_at=row_dict["updated_at"],
                )
            )

        return PipelineConfigListResponse(pipelines=summaries, total=len(summaries))

    # ── Get ───────────────────────────────────────────────────────────

    async def get_pipeline(
        self,
        project_id: str,
        pipeline_id: str,
        github_user_id: str = "",
    ) -> PipelineConfig | None:
        """Get a single pipeline configuration by ID."""
        if github_user_id:
            cursor = await self._db.execute(
                "SELECT * FROM pipeline_configs WHERE id = ? AND (github_user_id = ? OR github_user_id = '')",
                (pipeline_id, github_user_id),
            )
        else:
            cursor = await self._db.execute(
                "SELECT * FROM pipeline_configs WHERE id = ? AND project_id = ?",
                (pipeline_id, project_id),
            )
        row = await cursor.fetchone()
        if row is None:
            return None
        return self._row_to_config(dict(row))

    # ── Create ────────────────────────────────────────────────────────

    async def create_pipeline(
        self,
        project_id: str,
        body: PipelineConfigCreate,
        github_user_id: str = "",
    ) -> PipelineConfig:
        """Create a new pipeline configuration.

        Raises:
            ValueError: If a pipeline with the same name already exists.
        """
        pipeline_id = str(uuid.uuid4())
        now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        normalized_stages = list(body.stages)
        self._normalize_groups(normalized_stages)
        self._normalize_tool_counts(normalized_stages)
        self._normalize_execution_modes(normalized_stages)
        stages_json = json.dumps([s.model_dump() for s in normalized_stages])

        try:
            await self._db.execute(
                """
                INSERT INTO pipeline_configs (id, project_id, name, description, stages, github_user_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    pipeline_id,
                    project_id,
                    body.name,
                    body.description,
                    stages_json,
                    github_user_id,
                    now,
                    now,
                ),
            )
            await self._db.commit()
        except aiosqlite.IntegrityError as exc:
            raise ValueError(f"A pipeline named '{body.name}' already exists.") from exc

        pipeline = await self.get_pipeline(project_id, pipeline_id, github_user_id=github_user_id)
        if pipeline is None:
            raise RuntimeError(f"Pipeline {pipeline_id} was not found after creation")
        return pipeline

    # ── Update ────────────────────────────────────────────────────────

    async def update_pipeline(
        self,
        project_id: str,
        pipeline_id: str,
        body: PipelineConfigUpdate,
        github_user_id: str = "",
    ) -> PipelineConfig | None:
        """Update an existing pipeline configuration.

        Returns None if the pipeline does not exist.
        Raises ValueError on duplicate name.
        Raises PermissionError if the pipeline is a preset.
        """
        existing = await self.get_pipeline(project_id, pipeline_id, github_user_id=github_user_id)
        if existing is None:
            return None

        if existing.is_preset:
            raise PermissionError(
                "Cannot modify preset pipelines. Use 'Save as Copy' to create an editable version."
            )

        updates = body.model_dump(exclude_unset=True)
        if not updates:
            return existing

        now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        updates["updated_at"] = now

        if "stages" in updates and updates["stages"] is not None:
            # Normalize tool counts before saving
            raw_stages = updates["stages"]
            parsed = [
                PipelineStage(**(s.model_dump() if hasattr(s, "model_dump") else s))
                for s in raw_stages
            ]
            self._normalize_groups(parsed)
            self._normalize_tool_counts(parsed)
            self._normalize_execution_modes(parsed)
            updates["stages"] = json.dumps([s.model_dump() for s in parsed])

        # Validate columns against allowlist
        safe_updates = {k: v for k, v in updates.items() if k in _PIPELINE_COLUMNS}
        if not safe_updates:
            return existing

        set_clause = ", ".join(f"{col} = ?" for col in safe_updates)
        if github_user_id:
            values = [*list(safe_updates.values()), pipeline_id, github_user_id]
            where = "WHERE id = ? AND (github_user_id = ? OR github_user_id = '')"
        else:
            values = [*list(safe_updates.values()), pipeline_id, project_id]
            where = "WHERE id = ? AND project_id = ?"

        try:
            await self._db.execute(
                f"UPDATE pipeline_configs SET {set_clause} {where}",
                values,
            )
            await self._db.commit()
        except aiosqlite.IntegrityError as exc:
            raise ValueError(
                f"A pipeline named '{updates.get('name', '')}' already exists."
            ) from exc

        return await self.get_pipeline(project_id, pipeline_id, github_user_id=github_user_id)

    # ── Delete ────────────────────────────────────────────────────────

    async def delete_pipeline(
        self,
        project_id: str,
        pipeline_id: str,
        github_user_id: str = "",
    ) -> bool:
        """Delete a pipeline configuration. Returns True if deleted."""
        if github_user_id:
            cursor = await self._db.execute(
                "DELETE FROM pipeline_configs WHERE id = ? AND (github_user_id = ? OR github_user_id = '')",
                (pipeline_id, github_user_id),
            )
        else:
            cursor = await self._db.execute(
                "DELETE FROM pipeline_configs WHERE id = ? AND project_id = ?",
                (pipeline_id, project_id),
            )
        await self._db.commit()
        return cursor.rowcount > 0

    # ── Presets ───────────────────────────────────────────────────────

    async def seed_presets(
        self,
        project_id: str,
        github_user_id: str = "",
    ) -> dict:
        """Idempotently seed preset pipeline configurations for a user."""
        seeded: list[str] = []
        skipped: list[str] = []
        did_update_existing = False
        did_delete_stale = False

        now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        valid_preset_ids = tuple(preset["preset_id"] for preset in _PRESET_DEFINITIONS)

        stale_placeholders = ", ".join("?" for _ in valid_preset_ids)
        stale_query = f"""
            DELETE FROM pipeline_configs
            WHERE project_id = ?
              AND is_preset = 1
              AND preset_id NOT IN ({stale_placeholders})
        """
        stale_params: list[str] = [project_id, *valid_preset_ids]
        if github_user_id:
            stale_query += " AND (github_user_id = ? OR github_user_id = '')"
            stale_params.append(github_user_id)

        stale_cursor = await self._db.execute(stale_query, stale_params)
        did_delete_stale = stale_cursor.rowcount > 0

        for preset in _PRESET_DEFINITIONS:
            preset_id = preset["preset_id"]
            stages_json = json.dumps(preset["stages"])
            # Check if already seeded for this user
            if github_user_id:
                cursor = await self._db.execute(
                    """
                    SELECT id, name, description, stages, is_preset
                    FROM pipeline_configs
                    WHERE preset_id = ? AND (github_user_id = ? OR github_user_id = '')
                    ORDER BY CASE WHEN project_id = ? THEN 0 ELSE 1 END,
                             CASE WHEN github_user_id = ? THEN 0 ELSE 1 END,
                             updated_at DESC
                    LIMIT 1
                    """,
                    (preset_id, github_user_id, project_id, github_user_id),
                )
            else:
                cursor = await self._db.execute(
                    """
                    SELECT id, name, description, stages, is_preset
                    FROM pipeline_configs
                    WHERE preset_id = ? AND project_id = ?
                    LIMIT 1
                    """,
                    (preset_id, project_id),
                )
            existing = await cursor.fetchone()
            if existing:
                existing_row = dict(existing)
                if (
                    existing_row.get("name") != preset["name"]
                    or (existing_row.get("description") or "") != preset["description"]
                    or (existing_row.get("stages") or "[]") != stages_json
                    or int(existing_row.get("is_preset") or 0) != 1
                ):
                    await self._db.execute(
                        """
                        UPDATE pipeline_configs
                        SET name = ?, description = ?, stages = ?, is_preset = 1, updated_at = ?
                        WHERE id = ?
                        """,
                        (
                            preset["name"],
                            preset["description"],
                            stages_json,
                            now,
                            existing_row["id"],
                        ),
                    )
                    did_update_existing = True
                skipped.append(preset_id)
                continue

            pipeline_id = str(uuid.uuid4())
            try:
                await self._db.execute(
                    """
                    INSERT INTO pipeline_configs
                        (id, project_id, name, description, stages, is_preset, preset_id, github_user_id, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
                    """,
                    (
                        pipeline_id,
                        project_id,
                        preset["name"],
                        preset["description"],
                        stages_json,
                        preset_id,
                        github_user_id,
                        now,
                        now,
                    ),
                )
                seeded.append(preset_id)
            except aiosqlite.IntegrityError:
                skipped.append(preset_id)

        if seeded or did_update_existing or did_delete_stale:
            await self._db.commit()

        return {"seeded": seeded, "skipped": skipped, "total": len(seeded) + len(skipped)}

    # ── Assignment ───────────────────────────────────────────────────

    async def get_assignment(
        self,
        project_id: str,
    ) -> ProjectPipelineAssignment:
        """Get the current pipeline assignment for a project."""
        cursor = await self._db.execute(
            """
            SELECT assigned_pipeline_id
            FROM project_settings
            WHERE github_user_id = ? AND project_id = ?
            LIMIT 1
            """,
            (_CANONICAL_PROJECT_SETTINGS_USER, project_id),
        )
        row = await cursor.fetchone()
        if row:
            row_dict = dict(row)
            pipeline_id = row_dict.get("assigned_pipeline_id", "") or ""
        else:
            pipeline_id = ""

        if pipeline_id:
            exists_cursor = await self._db.execute(
                "SELECT 1 FROM pipeline_configs WHERE id = ? LIMIT 1",
                (pipeline_id,),
            )
            exists = await exists_cursor.fetchone()

            if exists is None:
                logger.warning(
                    "Assigned pipeline %s not found for project %s; clearing stale assignment",
                    pipeline_id,
                    project_id,
                )
                await self._db.execute(
                    """
                    UPDATE project_settings
                    SET assigned_pipeline_id = '',
                        updated_at = ?
                    WHERE github_user_id = ? AND project_id = ?
                    """,
                    (
                        datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        _CANONICAL_PROJECT_SETTINGS_USER,
                        project_id,
                    ),
                )
                await self._db.commit()
                pipeline_id = ""

        return ProjectPipelineAssignment(
            project_id=project_id,
            pipeline_id=pipeline_id,
        )

    async def set_assignment(
        self,
        project_id: str,
        pipeline_id: str,
        github_user_id: str = "",
    ) -> ProjectPipelineAssignment:
        """Set the pipeline assignment for a project.

        Raises ValueError if pipeline_id is non-empty and doesn't exist.
        """
        if pipeline_id:
            existing = await self.get_pipeline(
                project_id,
                pipeline_id,
                github_user_id=github_user_id,
            )
            if existing is None:
                raise ValueError(f"Pipeline '{pipeline_id}' is no longer available.")

        now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        await self._db.execute(
            """
            INSERT INTO project_settings (github_user_id, project_id, updated_at, assigned_pipeline_id)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(github_user_id, project_id) DO UPDATE SET
                assigned_pipeline_id = excluded.assigned_pipeline_id,
                updated_at = excluded.updated_at
            """,
            (_CANONICAL_PROJECT_SETTINGS_USER, project_id, now, pipeline_id),
        )
        await self._db.commit()

        return await self.get_assignment(project_id)
