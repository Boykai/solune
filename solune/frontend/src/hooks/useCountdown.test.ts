import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';

import { formatCountdown, useCountdown } from './useCountdown';

describe('useCountdown', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-04-06T00:00:00Z'));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('decrements once per second until expiry', () => {
    const expiresAt = new Date(Date.now() + 65_000).toISOString();
    const { result } = renderHook(({ target }) => useCountdown(target), {
      initialProps: { target: expiresAt },
    });

    expect(result.current).toBe(65);

    act(() => {
      vi.advanceTimersByTime(1_000);
    });

    expect(result.current).toBe(64);
  });

  it('returns zero after expiration and resets when props change', () => {
    const firstTarget = new Date(Date.now() + 1_000).toISOString();
    const { result, rerender } = renderHook(({ target }) => useCountdown(target), {
      initialProps: { target: firstTarget },
    });

    act(() => {
      vi.advanceTimersByTime(2_000);
    });

    expect(result.current).toBe(0);

    const secondTarget = new Date(Date.now() + 10_000).toISOString();
    rerender({ target: secondTarget });

    expect(result.current).toBe(10);
  });

  it('cleans up its interval on unmount', () => {
    const clearIntervalSpy = vi.spyOn(globalThis, 'clearInterval');
    const expiresAt = new Date(Date.now() + 5_000).toISOString();
    const { unmount } = renderHook(() => useCountdown(expiresAt));

    unmount();

    expect(clearIntervalSpy).toHaveBeenCalled();
  });
});

describe('formatCountdown', () => {
  it('formats edge cases', () => {
    expect(formatCountdown(-1)).toBe('Expired');
    expect(formatCountdown(0)).toBe('Expired');
    expect(formatCountdown(59)).toBe('59s');
    expect(formatCountdown(61)).toBe('1m 1s');
  });
});
