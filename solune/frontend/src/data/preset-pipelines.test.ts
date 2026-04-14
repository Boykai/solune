/**
 * Tests for preset-pipelines.ts — static preset pipeline definitions.
 */
import { describe, it, expect } from 'vitest';
import { PRESET_PIPELINES } from './preset-pipelines';

describe('PRESET_PIPELINES', () => {
  it('has exactly 4 preset pipelines', () => {
    expect(PRESET_PIPELINES).toHaveLength(4);
  });

  it('each preset has required fields', () => {
    for (const preset of PRESET_PIPELINES) {
      expect(preset.presetId).toBeTruthy();
      expect(preset.name).toBeTruthy();
      expect(preset.description).toBeTruthy();
      expect(preset.stages.length).toBeGreaterThan(0);
    }
  });

  it('has github preset', () => {
    const github = PRESET_PIPELINES.find((p) => p.presetId === 'github');
    expect(github).toBeDefined();
    expect(github!.name).toBe('GitHub');
  });

  it('github preset has single "In progress" stage with GitHub Copilot', () => {
    const github = PRESET_PIPELINES.find((p) => p.presetId === 'github')!;
    expect(github.stages).toHaveLength(1);
    expect(github.stages[0].name).toBe('In progress');
    const agents = github.stages[0].groups![0].agents;
    expect(agents).toHaveLength(1);
    expect(agents[0].agent_slug).toBe('copilot');
  });

  it('has spec-kit preset', () => {
    const specKit = PRESET_PIPELINES.find((p) => p.presetId === 'spec-kit');
    expect(specKit).toBeDefined();
    expect(specKit!.name).toBe('Spec Kit');
  });

  it('spec-kit has single "In progress" stage with 5 speckit agents', () => {
    const specKit = PRESET_PIPELINES.find((p) => p.presetId === 'spec-kit')!;
    expect(specKit.stages).toHaveLength(1);
    expect(specKit.stages[0].name).toBe('In progress');
    const agents = specKit.stages[0].groups![0].agents;
    expect(agents).toHaveLength(5);
    expect(agents.map((a) => a.agent_slug)).toEqual([
      'speckit.specify',
      'speckit.plan',
      'speckit.tasks',
      'speckit.analyze',
      'speckit.implement',
    ]);
  });

  it('has default preset with 10 agents in correct order', () => {
    const defaultPreset = PRESET_PIPELINES.find((p) => p.presetId === 'default')!;
    expect(defaultPreset).toBeDefined();
    expect(defaultPreset.name).toBe('Default');
    expect(defaultPreset.stages).toHaveLength(1);
    expect(defaultPreset.stages[0].name).toBe('In progress');
    const agents = defaultPreset.stages[0].groups![0].agents;
    expect(agents).toHaveLength(10);
    expect(agents.map((a) => a.agent_slug)).toEqual([
      'speckit.specify',
      'speckit.plan',
      'speckit.tasks',
      'speckit.analyze',
      'speckit.implement',
      'quality-assurance',
      'tester',
      'linter',
      'copilot-review',
      'judge',
    ]);
  });

  it('has app-builder preset with 11 agents including architect in correct order', () => {
    const appBuilder = PRESET_PIPELINES.find((p) => p.presetId === 'app-builder')!;
    expect(appBuilder).toBeDefined();
    expect(appBuilder.name).toBe('App Builder');
    expect(appBuilder.stages).toHaveLength(1);
    expect(appBuilder.stages[0].name).toBe('In progress');
    const agents = appBuilder.stages[0].groups![0].agents;
    expect(agents).toHaveLength(11);
    expect(agents.map((a) => a.agent_slug)).toEqual([
      'speckit.specify',
      'speckit.plan',
      'speckit.tasks',
      'speckit.analyze',
      'speckit.implement',
      'architect',
      'quality-assurance',
      'tester',
      'linter',
      'copilot-review',
      'judge',
    ]);
  });

  it('all stages have valid order', () => {
    for (const preset of PRESET_PIPELINES) {
      for (let i = 0; i < preset.stages.length; i++) {
        expect(preset.stages[i].order).toBe(i);
      }
    }
  });

  it('all stages have at least one execution group', () => {
    for (const preset of PRESET_PIPELINES) {
      for (const stage of preset.stages) {
        expect(stage.groups?.length).toBeGreaterThan(0);
      }
    }
  });

  it('all execution groups have at least one agent', () => {
    for (const preset of PRESET_PIPELINES) {
      for (const stage of preset.stages) {
        for (const group of stage.groups ?? []) {
          expect(group.agents.length).toBeGreaterThan(0);
        }
      }
    }
  });

  it('all agents have required fields', () => {
    for (const preset of PRESET_PIPELINES) {
      for (const stage of preset.stages) {
        for (const group of stage.groups ?? []) {
          for (const agent of group.agents) {
            expect(agent.id).toBeTruthy();
            expect(agent.agent_slug).toBeTruthy();
            expect(agent.agent_display_name).toBeTruthy();
          }
        }
      }
    }
  });

  it('preset IDs are unique', () => {
    const ids = PRESET_PIPELINES.map((p) => p.presetId);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it('all agents use Auto mode (empty model_id)', () => {
    for (const preset of PRESET_PIPELINES) {
      for (const stage of preset.stages) {
        for (const group of stage.groups ?? []) {
          for (const agent of group.agents) {
            expect(agent.model_id).toBe('');
          }
        }
      }
    }
  });

  it('all agent IDs are globally unique across all presets', () => {
    const allIds: string[] = [];
    for (const preset of PRESET_PIPELINES) {
      for (const stage of preset.stages) {
        for (const group of stage.groups ?? []) {
          for (const agent of group.agents) {
            allIds.push(agent.id);
          }
        }
      }
    }
    expect(new Set(allIds).size).toBe(allIds.length);
  });

  it('does not contain retired preset IDs', () => {
    const retiredIds = ['easy', 'medium', 'hard', 'expert', 'github-copilot'];
    const currentIds = PRESET_PIPELINES.map((p) => p.presetId);
    for (const retired of retiredIds) {
      expect(currentIds).not.toContain(retired);
    }
  });

  it('does not contain retired preset names', () => {
    const retiredNames = ['Easy', 'Medium', 'Hard', 'Expert', 'GitHub Copilot'];
    const currentNames = PRESET_PIPELINES.map((p) => p.name);
    for (const retired of retiredNames) {
      expect(currentNames).not.toContain(retired);
    }
  });
});
