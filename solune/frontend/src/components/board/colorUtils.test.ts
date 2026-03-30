import { describe, it, expect } from 'vitest';
import { statusColorToCSS, statusColorToBg } from './colorUtils';
import type { StatusColor } from '@/types';

const VALID_COLORS: StatusColor[] = [
  'GRAY',
  'BLUE',
  'GREEN',
  'YELLOW',
  'ORANGE',
  'RED',
  'PINK',
  'PURPLE',
];

describe('statusColorToCSS', () => {
  it.each(VALID_COLORS)('returns a hex color for %s', (color) => {
    const result = statusColorToCSS(color);
    expect(result).toMatch(/^#[0-9a-fA-F]{6}$/);
  });

  it('returns gray as fallback for unknown colors', () => {
    const result = statusColorToCSS('UNKNOWN' as StatusColor);
    expect(result).toBe('#9b9389');
  });
});

describe('statusColorToBg', () => {
  it.each(VALID_COLORS)('returns an rgba background for %s', (color) => {
    const result = statusColorToBg(color);
    expect(result).toMatch(/^rgba\(/);
  });

  it('returns gray background as fallback for unknown colors', () => {
    const result = statusColorToBg('UNKNOWN' as StatusColor);
    expect(result).toBe('rgba(155, 147, 137, 0.18)');
  });
});
