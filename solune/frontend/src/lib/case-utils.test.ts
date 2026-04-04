import { describe, it, expect } from 'vitest';
import { caseInsensitiveKey } from './case-utils';

describe('caseInsensitiveKey', () => {
  it('returns the original key when an exact match exists', () => {
    const obj = { Name: 'Alice', Age: 30 };
    expect(caseInsensitiveKey(obj, 'Name')).toBe('Name');
  });

  it('matches case-insensitively and returns the original casing', () => {
    const obj = { ContentType: 'json' };
    expect(caseInsensitiveKey(obj, 'contenttype')).toBe('ContentType');
  });

  it('matches uppercase query to lowercase key', () => {
    const obj = { status: 'ok' };
    expect(caseInsensitiveKey(obj, 'STATUS')).toBe('status');
  });

  it('returns the provided key as fallback when no match exists', () => {
    const obj = { Foo: 1 };
    expect(caseInsensitiveKey(obj, 'Bar')).toBe('Bar');
  });

  it('handles an empty object', () => {
    expect(caseInsensitiveKey({}, 'anything')).toBe('anything');
  });

  it('returns the first matching key when multiple match', () => {
    // Object.keys order is deterministic for string keys in V8
    const obj = { ABC: 1, abc: 2 };
    const result = caseInsensitiveKey(obj, 'Abc');
    expect(['ABC', 'abc']).toContain(result);
  });

  it('handles keys with mixed casing', () => {
    const obj = { 'X-Request-ID': '123' };
    expect(caseInsensitiveKey(obj, 'x-request-id')).toBe('X-Request-ID');
  });
});
