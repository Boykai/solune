import { describe, it, expect, vi, afterEach } from 'vitest';
import {
  MS_PER_HOUR,
  MS_PER_DAY,
  daysToMs,
  formatMsRemaining,
  formatMsAgo,
  computeCountRemaining,
  computeTimeProgress,
  computeCountProgress,
} from './time-utils';

describe('MS_PER_HOUR', () => {
  it('equals 3 600 000', () => {
    expect(MS_PER_HOUR).toBe(3_600_000);
  });
});

describe('MS_PER_DAY', () => {
  it('equals 86 400 000', () => {
    expect(MS_PER_DAY).toBe(86_400_000);
  });
});

describe('daysToMs', () => {
  it('converts 1 day', () => {
    expect(daysToMs(1)).toBe(MS_PER_DAY);
  });

  it('converts 0 days', () => {
    expect(daysToMs(0)).toBe(0);
  });

  it('converts fractional days', () => {
    expect(daysToMs(0.5)).toBe(MS_PER_DAY / 2);
  });

  it('converts large values', () => {
    expect(daysToMs(365)).toBe(365 * MS_PER_DAY);
  });
});

describe('formatMsRemaining', () => {
  it('returns "Due now" for 0 ms', () => {
    expect(formatMsRemaining(0)).toBe('Due now');
  });

  it('returns "Due now" for negative values', () => {
    expect(formatMsRemaining(-1000)).toBe('Due now');
  });

  it('formats days and hours', () => {
    const ms = 2 * MS_PER_DAY + 5 * MS_PER_HOUR;
    expect(formatMsRemaining(ms)).toBe('2d 5h remaining');
  });

  it('formats hours only when less than a day', () => {
    expect(formatMsRemaining(3 * MS_PER_HOUR)).toBe('3h remaining');
  });

  it('shows 0h for sub-hour remainders', () => {
    expect(formatMsRemaining(30 * 60 * 1000)).toBe('0h remaining');
  });

  it('formats exactly one day as 1d 0h remaining', () => {
    expect(formatMsRemaining(MS_PER_DAY)).toBe('1d 0h remaining');
  });
});

describe('formatMsAgo', () => {
  it('returns "Run just now" for 0 ms', () => {
    expect(formatMsAgo(0)).toBe('Run just now');
  });

  it('returns "Run just now" for sub-hour elapsed', () => {
    expect(formatMsAgo(30 * 60 * 1000)).toBe('Run just now');
  });

  it('returns hours ago', () => {
    expect(formatMsAgo(5 * MS_PER_HOUR)).toBe('Run 5h ago');
  });

  it('returns days ago', () => {
    expect(formatMsAgo(3 * MS_PER_DAY)).toBe('Run 3d ago');
  });

  it('prefers days over hours when applicable', () => {
    const ms = 2 * MS_PER_DAY + 6 * MS_PER_HOUR;
    expect(formatMsAgo(ms)).toBe('Run 2d ago');
  });
});

describe('computeCountRemaining', () => {
  it('returns full schedule value when no issues since trigger', () => {
    expect(computeCountRemaining(10, 5, 5)).toBe(10);
  });

  it('returns 0 when schedule is exceeded', () => {
    expect(computeCountRemaining(5, 20, 10)).toBe(0);
  });

  it('returns correct remaining count', () => {
    expect(computeCountRemaining(10, 7, 3)).toBe(6);
  });

  it('never returns negative', () => {
    expect(computeCountRemaining(3, 100, 0)).toBe(0);
  });

  it('returns 0 when exactly at threshold', () => {
    expect(computeCountRemaining(5, 10, 5)).toBe(0);
  });
});

describe('computeTimeProgress', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('returns 0 progress at start', () => {
    const now = Date.now();
    vi.spyOn(Date, 'now').mockReturnValue(now);
    const baseDate = new Date(now).toISOString();
    const { remainingMs, progress } = computeTimeProgress(baseDate, 1);
    expect(progress).toBeCloseTo(0, 1);
    expect(remainingMs).toBeCloseTo(MS_PER_DAY, -3);
  });

  it('returns 1 progress when past threshold', () => {
    const now = Date.now();
    vi.spyOn(Date, 'now').mockReturnValue(now);
    const pastDate = new Date(now - 2 * MS_PER_DAY).toISOString();
    const { remainingMs, progress } = computeTimeProgress(pastDate, 1);
    expect(progress).toBe(1);
    expect(remainingMs).toBe(0);
  });

  it('returns 0.5 progress at midpoint', () => {
    const now = Date.now();
    vi.spyOn(Date, 'now').mockReturnValue(now);
    const halfwayDate = new Date(now - MS_PER_DAY).toISOString();
    const { remainingMs, progress } = computeTimeProgress(halfwayDate, 2);
    expect(progress).toBeCloseTo(0.5, 1);
    expect(remainingMs).toBeCloseTo(MS_PER_DAY, -3);
  });

  it('handles 0 threshold days', () => {
    const { progress } = computeTimeProgress(new Date().toISOString(), 0);
    expect(progress).toBe(0);
  });
});

describe('computeCountProgress', () => {
  it('returns 0 when nothing done', () => {
    expect(computeCountProgress(10, 10)).toBe(0);
  });

  it('returns 1 when all done', () => {
    expect(computeCountProgress(10, 0)).toBe(1);
  });

  it('returns 0.5 at midpoint', () => {
    expect(computeCountProgress(10, 5)).toBe(0.5);
  });

  it('returns 0 when schedule is 0', () => {
    expect(computeCountProgress(0, 0)).toBe(0);
  });
});
