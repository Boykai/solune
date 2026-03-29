import { describe, it, expect } from 'vitest';
import { generateId } from './generateId';

describe('generateId', () => {
  it('returns a non-empty string', () => {
    const id = generateId();
    expect(typeof id).toBe('string');
    expect(id.length).toBeGreaterThan(0);
  });

  it('returns unique IDs', () => {
    const ids = new Set(Array.from({ length: 100 }, () => generateId()));
    expect(ids.size).toBe(100);
  });

  it('returns UUID-like format when crypto.randomUUID is available', () => {
    const id = generateId();
    // The test setup stubs crypto.randomUUID to return deterministic UUIDs
    expect(id).toMatch(/^[0-9a-f-]+$/i);
  });
});
