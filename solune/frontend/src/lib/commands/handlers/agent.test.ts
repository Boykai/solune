import { describe, it, expect } from 'vitest';
import { agentHandler } from './agent';

describe('agentHandler', () => {
  it('returns success with passthrough', () => {
    const result = agentHandler();
    expect(result.success).toBe(true);
    expect(result.passthrough).toBe(true);
  });

  it('returns clearInput true', () => {
    const result = agentHandler();
    expect(result.clearInput).toBe(true);
  });

  it('returns empty message', () => {
    const result = agentHandler();
    expect(result.message).toBe('');
  });
});
