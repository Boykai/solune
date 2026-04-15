/**
 * Static preset pipeline definitions.
 * These are seeded into the backend on first load and displayed as
 * read-only system presets in the Saved Workflows list.
 *
 * Each preset uses a single "In progress" stage with one sequential
 * execution group containing all agents.
 */

import type { PresetPipelineDefinition } from '@/types';

/** Helper to build a PipelineAgentNode from a slug + display name. */
function agent(id: string, slug: string, displayName: string) {
  return {
    id,
    agent_slug: slug,
    agent_display_name: displayName,
    model_id: '',
    model_name: '',
    tool_ids: [] as string[],
    tool_count: 0,
    config: {} as Record<string, unknown>,
  };
}

export const PRESET_PIPELINES: PresetPipelineDefinition[] = [
  // ── GitHub ──────────────────────────────────────────────────────────
  {
    presetId: 'github',
    name: 'GitHub',
    description: 'Single-agent pipeline powered by GitHub Copilot.',
    stages: [
      {
        id: 'preset-gh-stage-1',
        name: 'In progress',
        order: 0,
        groups: [
          {
            id: 'preset-gh-group-1',
            order: 0,
            execution_mode: 'sequential',
            agents: [
              agent('preset-gh-a1', 'copilot', 'GitHub Copilot (Auto)'),
            ],
          },
        ],
        agents: [],
        execution_mode: 'sequential',
      },
    ],
  },

  // ── Spec Kit ────────────────────────────────────────────────────────
  {
    presetId: 'spec-kit',
    name: 'Spec Kit',
    description:
      'Full specification workflow: specify → plan → tasks → analyze → implement.',
    stages: [
      {
        id: 'preset-sk-stage-1',
        name: 'In progress',
        order: 0,
        groups: [
          {
            id: 'preset-sk-group-1',
            order: 0,
            execution_mode: 'sequential',
            agents: [
              agent('preset-sk-a1', 'speckit.specify', 'speckit.specify (Auto)'),
              agent('preset-sk-a2', 'speckit.plan', 'speckit.plan (Auto)'),
              agent('preset-sk-a3', 'speckit.tasks', 'speckit.tasks (Auto)'),
              agent('preset-sk-a4', 'speckit.analyze', 'speckit.analyze (Auto)'),
              agent('preset-sk-a5', 'speckit.implement', 'speckit.implement (Auto)'),
            ],
          },
        ],
        agents: [],
        execution_mode: 'sequential',
      },
    ],
  },

  // ── Default ─────────────────────────────────────────────────────────
  {
    presetId: 'default',
    name: 'Default',
    description:
      'End-to-end workflow: spec, plan, implement, QA, test, lint, review, and judge.',
    stages: [
      {
        id: 'preset-df-stage-1',
        name: 'In progress',
        order: 0,
        groups: [
          {
            id: 'preset-df-group-1',
            order: 0,
            execution_mode: 'sequential',
            agents: [
              agent('preset-df-a1', 'speckit.specify', 'speckit.specify (Auto)'),
              agent('preset-df-a2', 'speckit.plan', 'speckit.plan (Auto)'),
              agent('preset-df-a3', 'speckit.tasks', 'speckit.tasks (Auto)'),
              agent('preset-df-a4', 'speckit.analyze', 'speckit.analyze (Auto)'),
              agent('preset-df-a5', 'speckit.implement', 'speckit.implement (Auto)'),
              agent('preset-df-a6', 'quality-assurance', 'Quality Assurance (Auto)'),
              agent('preset-df-a7', 'tester', 'Tester (Auto)'),
              agent('preset-df-a8', 'linter', 'Linter (Auto)'),
              agent('preset-df-a9', 'copilot-review', 'Copilot Review (Auto)'),
              agent('preset-df-a10', 'judge', 'Judge (Auto)'),
            ],
          },
        ],
        agents: [],
        execution_mode: 'sequential',
      },
    ],
  },

  // ── App Builder ─────────────────────────────────────────────────────
  {
    presetId: 'app-builder',
    name: 'App Builder',
    description:
      'Full stack workflow with architecture, QA, testing, linting, review, and judging.',
    stages: [
      {
        id: 'preset-ab-stage-1',
        name: 'In progress',
        order: 0,
        groups: [
          {
            id: 'preset-ab-group-1',
            order: 0,
            execution_mode: 'sequential',
            agents: [
              agent('preset-ab-a1', 'speckit.specify', 'speckit.specify (Auto)'),
              agent('preset-ab-a2', 'speckit.plan', 'speckit.plan (Auto)'),
              agent('preset-ab-a3', 'speckit.tasks', 'speckit.tasks (Auto)'),
              agent('preset-ab-a4', 'speckit.analyze', 'speckit.analyze (Auto)'),
              agent('preset-ab-a5', 'speckit.implement', 'speckit.implement (Auto)'),
              agent('preset-ab-a6', 'architect', 'Architect (Auto)'),
              agent('preset-ab-a7', 'quality-assurance', 'Quality Assurance (Auto)'),
              agent('preset-ab-a8', 'tester', 'Tester (Auto)'),
              agent('preset-ab-a9', 'linter', 'Linter (Auto)'),
              agent('preset-ab-a10', 'copilot-review', 'Copilot Review (Auto)'),
              agent('preset-ab-a11', 'judge', 'Judge (Auto)'),
            ],
          },
        ],
        agents: [],
        execution_mode: 'sequential',
      },
    ],
  },
];
