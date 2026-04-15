/**
 * Tests for preset-pipelines.ts — static preset pipeline definitions.
 */
import { describe, it, expect } from 'vitest';
import { PRESET_PIPELINES } from './preset-pipelines';

describe('PRESET_PIPELINES', () => {
  it('has at least 4 preset pipelines', () => {
    expect(PRESET_PIPELINES.length).toBeGreaterThanOrEqual(4);
  });

  it('each preset has required fields', () => {
    for (const preset of PRESET_PIPELINES) {
      expect(preset.presetId).toBeTruthy();
      expect(preset.name).toBeTruthy();
      expect(preset.description).toBeTruthy();
      expect(preset.stages.length).toBeGreaterThan(0);
    }
  });

  it('has spec-kit preset', () => {
    const specKit = PRESET_PIPELINES.find((p) => p.presetId === 'spec-kit');
    expect(specKit).toBeDefined();
    expect(specKit!.name).toBe('Spec Kit');
  });

  it('spec-kit has 1 stage with 5 agents', () => {
    const specKit = PRESET_PIPELINES.find((p) => p.presetId === 'spec-kit')!;
    expect(specKit.stages).toHaveLength(1);
    expect(specKit.stages[0].name).toBe('In progress');
    const agents = specKit.stages[0].groups![0].agents;
    expect(agents).toHaveLength(5);
  });

  it('has github preset', () => {
    const github = PRESET_PIPELINES.find((p) => p.presetId === 'github');
    expect(github).toBeDefined();
    expect(github!.name).toBe('GitHub');
  });

  it('github has single stage with 1 agent', () => {
    const github = PRESET_PIPELINES.find((p) => p.presetId === 'github')!;
    expect(github.stages).toHaveLength(1);
    expect(github.stages[0].name).toBe('In progress');
    expect(github.stages[0].groups![0].agents).toHaveLength(1);
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
});
