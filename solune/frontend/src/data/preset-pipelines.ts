/**
 * Static preset pipeline definitions: GitHub, Spec Kit, Default, and App Builder.
 * These are seeded into the backend on first load and displayed as
 * read-only system presets in the Saved Workflows list.
 */

import type { PresetPipelineDefinition } from '@/types';

function makeAgent(id: string, slug: string, displayName: string) {
  return {
    id,
    agent_slug: slug,
    agent_display_name: displayName,
    model_id: '',
    model_name: '',
    tool_ids: [] as string[],
    tool_count: 0,
    config: {},
  };
}

export const PRESET_PIPELINES: PresetPipelineDefinition[] = [
  {
    presetId: 'github',
    name: 'GitHub',
    description: 'Single-stage pipeline powered by GitHub Copilot',
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
            agents: [makeAgent('preset-gh-agent-1', 'copilot', 'GitHub Copilot')],
          },
        ],
        agents: [],
        execution_mode: 'sequential',
      },
    ],
  },
  {
    presetId: 'spec-kit',
    name: 'Spec Kit',
    description: 'Full specification workflow: specify → plan → tasks → analyze → implement',
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
              makeAgent('preset-sk-agent-1', 'speckit.specify', 'speckit.specify'),
              makeAgent('preset-sk-agent-2', 'speckit.plan', 'speckit.plan'),
              makeAgent('preset-sk-agent-3', 'speckit.tasks', 'speckit.tasks'),
              makeAgent('preset-sk-agent-4', 'speckit.analyze', 'speckit.analyze'),
              makeAgent('preset-sk-agent-5', 'speckit.implement', 'speckit.implement'),
            ],
          },
        ],
        agents: [],
        execution_mode: 'sequential',
      },
    ],
  },
  {
    presetId: 'default',
    name: 'Default',
    description:
      'Spec Kit workflow plus quality assurance, testing, linting, and review agents',
    stages: [
      {
        id: 'preset-def-stage-1',
        name: 'In progress',
        order: 0,
        groups: [
          {
            id: 'preset-def-group-1',
            order: 0,
            execution_mode: 'sequential',
            agents: [
              makeAgent('preset-def-agent-1', 'speckit.specify', 'speckit.specify'),
              makeAgent('preset-def-agent-2', 'speckit.plan', 'speckit.plan'),
              makeAgent('preset-def-agent-3', 'speckit.tasks', 'speckit.tasks'),
              makeAgent('preset-def-agent-4', 'speckit.analyze', 'speckit.analyze'),
              makeAgent('preset-def-agent-5', 'speckit.implement', 'speckit.implement'),
              makeAgent('preset-def-agent-6', 'quality-assurance', 'Quality Assurance'),
              makeAgent('preset-def-agent-7', 'tester', 'Tester'),
              makeAgent('preset-def-agent-8', 'linter', 'Linter'),
              makeAgent('preset-def-agent-9', 'copilot-review', 'Copilot Review'),
              makeAgent('preset-def-agent-10', 'judge', 'Judge'),
            ],
          },
        ],
        agents: [],
        execution_mode: 'sequential',
      },
    ],
  },
  {
    presetId: 'app-builder',
    name: 'App Builder',
    description:
      'Full Spec Kit workflow with Architect agent plus quality, testing, and review',
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
              makeAgent('preset-ab-agent-1', 'speckit.specify', 'speckit.specify'),
              makeAgent('preset-ab-agent-2', 'speckit.plan', 'speckit.plan'),
              makeAgent('preset-ab-agent-3', 'speckit.tasks', 'speckit.tasks'),
              makeAgent('preset-ab-agent-4', 'speckit.analyze', 'speckit.analyze'),
              makeAgent('preset-ab-agent-5', 'speckit.implement', 'speckit.implement'),
              makeAgent('preset-ab-agent-6', 'architect', 'Architect'),
              makeAgent('preset-ab-agent-7', 'quality-assurance', 'Quality Assurance'),
              makeAgent('preset-ab-agent-8', 'tester', 'Tester'),
              makeAgent('preset-ab-agent-9', 'linter', 'Linter'),
              makeAgent('preset-ab-agent-10', 'copilot-review', 'Copilot Review'),
              makeAgent('preset-ab-agent-11', 'judge', 'Judge'),
            ],
          },
        ],
        agents: [],
        execution_mode: 'sequential',
      },
    ],
  },
];
