/**
 * Tests for preset-pipelines.ts — static preset pipeline definitions.
 */
import { describe, it, expect } from 'vitest';
import { PRESET_PIPELINES } from './preset-pipelines';

describe('PRESET_PIPELINES', () => {
  it('has at least 2 preset pipelines', () => {
    expect(PRESET_PIPELINES.length).toBeGreaterThanOrEqual(2);
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

  it('spec-kit has 5 stages in correct order', () => {
    const specKit = PRESET_PIPELINES.find((p) => p.presetId === 'spec-kit')!;
    expect(specKit.stages).toHaveLength(5);
    expect(specKit.stages[0].name).toBe('Specify');
    expect(specKit.stages[1].name).toBe('Plan');
    expect(specKit.stages[2].name).toBe('Tasks');
    expect(specKit.stages[3].name).toBe('Implement');
    expect(specKit.stages[4].name).toBe('Analyze');
  });

  it('has github-copilot preset', () => {
    const copilot = PRESET_PIPELINES.find((p) => p.presetId === 'github-copilot');
    expect(copilot).toBeDefined();
    expect(copilot!.name).toBe('GitHub Copilot');
  });

  it('github-copilot has single stage', () => {
    const copilot = PRESET_PIPELINES.find((p) => p.presetId === 'github-copilot')!;
    expect(copilot.stages).toHaveLength(1);
    expect(copilot.stages[0].name).toBe('Execute');
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
