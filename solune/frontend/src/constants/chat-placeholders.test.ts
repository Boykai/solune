/**
 * Tests for chat-placeholders.ts — centralized chat placeholder registry.
 */
import { describe, it, expect } from 'vitest';
import { CHAT_PLACEHOLDERS, CYCLING_EXAMPLES } from './chat-placeholders';

describe('CHAT_PLACEHOLDERS', () => {
  it('has main placeholder config', () => {
    expect(CHAT_PLACEHOLDERS.main).toBeDefined();
    expect(CHAT_PLACEHOLDERS.main.desktop).toBeTruthy();
    expect(CHAT_PLACEHOLDERS.main.mobile).toBeTruthy();
    expect(CHAT_PLACEHOLDERS.main.ariaLabel).toBeTruthy();
  });

  it('has agentFlow placeholder config', () => {
    expect(CHAT_PLACEHOLDERS.agentFlow).toBeDefined();
    expect(CHAT_PLACEHOLDERS.agentFlow.desktop).toBeTruthy();
    expect(CHAT_PLACEHOLDERS.agentFlow.mobile).toBeTruthy();
    expect(CHAT_PLACEHOLDERS.agentFlow.ariaLabel).toBeTruthy();
  });

  it('has choreFlow placeholder config', () => {
    expect(CHAT_PLACEHOLDERS.choreFlow).toBeDefined();
    expect(CHAT_PLACEHOLDERS.choreFlow.desktop).toBeTruthy();
    expect(CHAT_PLACEHOLDERS.choreFlow.mobile).toBeTruthy();
    expect(CHAT_PLACEHOLDERS.choreFlow.ariaLabel).toBeTruthy();
  });

  it('mobile text is shorter than desktop text', () => {
    for (const [, config] of Object.entries(CHAT_PLACEHOLDERS)) {
      expect(config.mobile.length).toBeLessThan(config.desktop.length);
    }
  });

  it('all configs have non-empty ariaLabel', () => {
    for (const [, config] of Object.entries(CHAT_PLACEHOLDERS)) {
      expect(config.ariaLabel.length).toBeGreaterThan(0);
    }
  });
});

describe('CYCLING_EXAMPLES', () => {
  it('has at least 3 example prompts', () => {
    expect(CYCLING_EXAMPLES.length).toBeGreaterThanOrEqual(3);
  });

  it('all examples start with "Try:"', () => {
    for (const example of CYCLING_EXAMPLES) {
      expect(example).toMatch(/^Try:/);
    }
  });

  it('all examples are non-empty strings', () => {
    for (const example of CYCLING_EXAMPLES) {
      expect(typeof example).toBe('string');
      expect(example.length).toBeGreaterThan(0);
    }
  });
});
