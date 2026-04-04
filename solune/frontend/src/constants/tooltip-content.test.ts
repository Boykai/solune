/**
 * Tests for tooltip-content.ts — centralized tooltip content registry.
 */
import { describe, it, expect } from 'vitest';
import { tooltipContent } from './tooltip-content';

describe('tooltipContent', () => {
  it('has tooltip entries', () => {
    const keys = Object.keys(tooltipContent);
    expect(keys.length).toBeGreaterThan(0);
  });

  it('all entries have a non-empty summary', () => {
    for (const [key, entry] of Object.entries(tooltipContent)) {
      expect(entry.summary, `${key} should have a summary`).toBeTruthy();
      expect(entry.summary.length, `${key} summary should be non-empty`).toBeGreaterThan(0);
    }
  });

  it('keys follow dot-notation pattern', () => {
    for (const key of Object.keys(tooltipContent)) {
      expect(key).toMatch(/^[\w]+\.[\w]+/);
      expect(key.split('.').length).toBeGreaterThanOrEqual(2);
    }
  });

  it('has board tooltips', () => {
    const boardKeys = Object.keys(tooltipContent).filter((k) => k.startsWith('board.'));
    expect(boardKeys.length).toBeGreaterThan(0);
  });

  it('has chat tooltips', () => {
    const chatKeys = Object.keys(tooltipContent).filter((k) => k.startsWith('chat.'));
    expect(chatKeys.length).toBeGreaterThan(0);
  });

  it('has agents tooltips', () => {
    const agentKeys = Object.keys(tooltipContent).filter((k) => k.startsWith('agents.'));
    expect(agentKeys.length).toBeGreaterThan(0);
  });

  it('has pipeline tooltips', () => {
    const pipelineKeys = Object.keys(tooltipContent).filter((k) => k.startsWith('pipeline.'));
    expect(pipelineKeys.length).toBeGreaterThan(0);
  });

  it('has settings tooltips', () => {
    const settingsKeys = Object.keys(tooltipContent).filter((k) => k.startsWith('settings.'));
    expect(settingsKeys.length).toBeGreaterThan(0);
  });

  it('has navigation tooltips', () => {
    const navKeys = Object.keys(tooltipContent).filter((k) => k.startsWith('nav.'));
    expect(navKeys.length).toBeGreaterThan(0);
  });

  it('entries with title have non-empty title', () => {
    for (const [key, entry] of Object.entries(tooltipContent)) {
      if (entry.title !== undefined) {
        expect(entry.title.length, `${key} title should be non-empty`).toBeGreaterThan(0);
      }
    }
  });
});
