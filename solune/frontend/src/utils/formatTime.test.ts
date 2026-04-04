import { describe, it, expect } from 'vitest';
import { formatTimeAgo, formatTimeUntil } from './formatTime';

describe('formatTimeAgo', () => {
  it('returns "just now" for recent dates', () => {
    const now = new Date();
    expect(formatTimeAgo(now)).toBe('just now');
  });

  it('returns "just now" for dates less than 60 seconds ago', () => {
    const date = new Date(Date.now() - 30 * 1000);
    expect(formatTimeAgo(date)).toBe('just now');
  });

  it('returns minutes ago for dates less than an hour ago', () => {
    const date = new Date(Date.now() - 5 * 60 * 1000);
    expect(formatTimeAgo(date)).toBe('5m ago');
  });

  it('returns locale time string for dates more than an hour ago', () => {
    const date = new Date(Date.now() - 2 * 60 * 60 * 1000);
    const result = formatTimeAgo(date);
    // Should be a time string, not "just now" or "Xm ago"
    expect(result).not.toBe('just now');
    expect(result).not.toContain('m ago');
  });
});

describe('formatTimeUntil', () => {
  it('returns "now" for past dates', () => {
    const date = new Date(Date.now() - 1000);
    expect(formatTimeUntil(date)).toBe('now');
  });

  it('returns "in less than a minute" for dates less than 60 seconds away', () => {
    const date = new Date(Date.now() + 30 * 1000);
    expect(formatTimeUntil(date)).toBe('in less than a minute');
  });

  it('returns "in X minutes" for dates less than 60 minutes away', () => {
    const date = new Date(Date.now() + 5 * 60 * 1000);
    const result = formatTimeUntil(date);
    expect(result).toMatch(/^in \d+ minutes?$/);
  });

  it('returns "in 1 minute" singular', () => {
    const date = new Date(Date.now() + 60 * 1000);
    expect(formatTimeUntil(date)).toBe('in 1 minute');
  });

  it('returns locale time string for dates more than 60 minutes away', () => {
    const date = new Date(Date.now() + 2 * 60 * 60 * 1000);
    const result = formatTimeUntil(date);
    expect(result).toMatch(/^at /);
  });
});
