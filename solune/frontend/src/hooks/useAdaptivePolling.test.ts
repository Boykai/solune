/**
 * Tests for useAdaptivePolling hook.
 *
 * Covers tier transitions, activity score computation, backoff / recovery,
 * visibility-triggered immediate polls, and TanStack Query integration.
 */

import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useAdaptivePolling } from './useAdaptivePolling';
import type { AdaptivePollingConfig } from './useAdaptivePolling';

// ── Helpers ────────────────────────────────────────────────────────────

/** Short config with a small window for deterministic transitions. */
const testConfig: AdaptivePollingConfig = {
  baseInterval: 10_000,
  minInterval: 3_000,
  maxInterval: 30_000,
  maxBackoffInterval: 60_000,
  windowSize: 5,
  highActivityThreshold: 0.6,
  mediumActivityThreshold: 0.2,
};

// ── Tests ──────────────────────────────────────────────────────────────

describe('useAdaptivePolling', () => {
  beforeEach(() => {
    vi.stubGlobal('document', {
      ...document,
      visibilityState: 'visible',
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // ── Initial state ──

  describe('initial state', () => {
    it('starts at medium tier with base interval', () => {
      const { result } = renderHook(() => useAdaptivePolling(testConfig));
      expect(result.current.state.tier).toBe('medium');
      expect(result.current.state.currentInterval).toBe(10_000);
      expect(result.current.state.activityScore).toBe(0);
      expect(result.current.state.isPaused).toBe(false);
    });

    it('uses defaults when no config is provided', () => {
      const { result } = renderHook(() => useAdaptivePolling());
      expect(result.current.state.currentInterval).toBe(10_000);
      expect(result.current.state.tier).toBe('medium');
    });
  });

  // ── Activity-based tier transitions ──

  describe('tier transitions', () => {
    it('transitions to high tier when >60% of polls detect changes', () => {
      const { result } = renderHook(() => useAdaptivePolling(testConfig));

      // Report 4 changes out of 5 polls → 80% activity → high tier
      act(() => {
        result.current.reportPollResult(true);
        result.current.reportPollResult(true);
        result.current.reportPollResult(true);
        result.current.reportPollResult(true);
        result.current.reportPollResult(false);
      });

      expect(result.current.state.tier).toBe('high');
      expect(result.current.state.currentInterval).toBe(3_000);
      expect(result.current.state.activityScore).toBe(0.8);
    });

    it('stays at medium tier when 20-60% of polls detect changes', () => {
      const { result } = renderHook(() => useAdaptivePolling(testConfig));

      // Report 2 changes out of 5 polls → 40% → medium tier
      act(() => {
        result.current.reportPollResult(true);
        result.current.reportPollResult(true);
        result.current.reportPollResult(false);
        result.current.reportPollResult(false);
        result.current.reportPollResult(false);
      });

      expect(result.current.state.tier).toBe('medium');
      expect(result.current.state.currentInterval).toBe(10_000);
      expect(result.current.state.activityScore).toBe(0.4);
    });

    it('transitions to low tier when <20% of polls detect changes', () => {
      const { result } = renderHook(() => useAdaptivePolling(testConfig));

      // Report 0 changes in 5 polls → 0% → low tier
      act(() => {
        result.current.reportPollResult(false);
        result.current.reportPollResult(false);
        result.current.reportPollResult(false);
        result.current.reportPollResult(false);
        result.current.reportPollResult(false);
      });

      expect(result.current.state.tier).toBe('low');
      expect(result.current.state.currentInterval).toBe(30_000);
      expect(result.current.state.activityScore).toBe(0);
    });

    it('sliding window evicts oldest entries beyond windowSize', () => {
      const { result } = renderHook(() => useAdaptivePolling(testConfig));

      // Fill window with changes → high tier
      act(() => {
        for (let i = 0; i < 5; i++) result.current.reportPollResult(true);
      });
      expect(result.current.state.tier).toBe('high');

      // Push 5 no-change entries to evict all changes
      act(() => {
        for (let i = 0; i < 5; i++) result.current.reportPollResult(false);
      });
      expect(result.current.state.tier).toBe('low');
      expect(result.current.state.activityScore).toBe(0);
    });
  });

  // ── Backoff ──

  describe('backoff', () => {
    it('enters backoff tier on first failure', () => {
      const { result } = renderHook(() => useAdaptivePolling(testConfig));

      act(() => {
        result.current.reportPollFailure();
      });

      expect(result.current.state.tier).toBe('backoff');
      // First failure: 2^1 * 10_000 = 20_000
      expect(result.current.state.currentInterval).toBe(20_000);
    });

    it('increases backoff exponentially on successive failures', () => {
      const { result } = renderHook(() => useAdaptivePolling(testConfig));

      act(() => result.current.reportPollFailure());
      expect(result.current.state.currentInterval).toBe(20_000); // 2^1 * 10k

      act(() => result.current.reportPollFailure());
      expect(result.current.state.currentInterval).toBe(40_000); // 2^2 * 10k

      act(() => result.current.reportPollFailure());
      expect(result.current.state.currentInterval).toBe(60_000); // capped at 60k
    });

    it('caps backoff at maxBackoffInterval', () => {
      const { result } = renderHook(() => useAdaptivePolling(testConfig));

      // 10 failures → 2^10 * 10k = huge, but capped at 60k
      act(() => {
        for (let i = 0; i < 10; i++) result.current.reportPollFailure();
      });

      expect(result.current.state.currentInterval).toBe(60_000);
    });
  });

  // ── Recovery from backoff ──

  describe('recovery from backoff', () => {
    it('resets to activity-based tier on success after failure', () => {
      const { result } = renderHook(() => useAdaptivePolling(testConfig));

      // Enter backoff
      act(() => result.current.reportPollFailure());
      expect(result.current.state.tier).toBe('backoff');

      // Recover
      act(() => result.current.reportPollSuccess());
      expect(result.current.state.tier).not.toBe('backoff');
    });

    it('does nothing when reportPollSuccess called without prior failure', () => {
      const { result } = renderHook(() => useAdaptivePolling(testConfig));

      const before = { ...result.current.state };
      act(() => result.current.reportPollSuccess());
      expect(result.current.state.tier).toBe(before.tier);
      expect(result.current.state.currentInterval).toBe(before.currentInterval);
    });

    it('failures during backoff override activity-based tier', () => {
      const { result } = renderHook(() => useAdaptivePolling(testConfig));

      // Build high activity
      act(() => {
        for (let i = 0; i < 5; i++) result.current.reportPollResult(true);
      });
      expect(result.current.state.tier).toBe('high');

      // Failure overrides to backoff
      act(() => result.current.reportPollFailure());
      expect(result.current.state.tier).toBe('backoff');
    });
  });

  // ── TanStack Query integration ──

  describe('getRefetchInterval', () => {
    it('returns current interval when tab is visible', () => {
      const { result } = renderHook(() => useAdaptivePolling(testConfig));
      expect(result.current.getRefetchInterval()).toBe(10_000);
    });

    it('returns false when tab is hidden (paused)', () => {
      const addListenerSpy = vi.fn();
      vi.stubGlobal('document', {
        ...document,
        visibilityState: 'hidden',
        addEventListener: addListenerSpy,
        removeEventListener: vi.fn(),
      });

      const { result } = renderHook(() => useAdaptivePolling(testConfig));

      // Simulate visibility change
      const handler = addListenerSpy.mock.calls.find(
        (c: unknown[]) => c[0] === 'visibilitychange',
      )?.[1] as (() => void) | undefined;
      if (handler) {
        act(() => handler());
      }

      expect(result.current.getRefetchInterval()).toBe(false);
    });
  });

  // ── Immediate poll ──

  describe('triggerImmediatePoll', () => {
    it('causes next getRefetchInterval to return 100ms', () => {
      const { result } = renderHook(() => useAdaptivePolling(testConfig));

      act(() => result.current.triggerImmediatePoll());

      const interval = result.current.getRefetchInterval();
      expect(interval).toBe(100);
    });

    it('resets to normal interval after the immediate poll is consumed', () => {
      const { result } = renderHook(() => useAdaptivePolling(testConfig));

      act(() => result.current.triggerImmediatePoll());

      // First call consumes the immediate flag
      result.current.getRefetchInterval();

      // Second call returns normal interval
      const interval = result.current.getRefetchInterval();
      expect(interval).not.toBe(100);
    });

    it('clears isPaused state', () => {
      const { result } = renderHook(() => useAdaptivePolling(testConfig));

      act(() => result.current.triggerImmediatePoll());
      expect(result.current.state.isPaused).toBe(false);
    });
  });

  // ── Activity score edge cases ──

  describe('activity score edge cases', () => {
    it('handles single poll result', () => {
      const { result } = renderHook(() => useAdaptivePolling(testConfig));

      act(() => result.current.reportPollResult(true));
      expect(result.current.state.activityScore).toBe(1.0);
    });

    it('score is exactly at high threshold boundary', () => {
      const { result } = renderHook(() =>
        useAdaptivePolling({ ...testConfig, windowSize: 5, highActivityThreshold: 0.6 }),
      );

      // 3 out of 5 = 0.6 exactly → medium (not strictly greater than 0.6)
      act(() => {
        result.current.reportPollResult(true);
        result.current.reportPollResult(true);
        result.current.reportPollResult(true);
        result.current.reportPollResult(false);
        result.current.reportPollResult(false);
      });

      expect(result.current.state.activityScore).toBe(0.6);
      expect(result.current.state.tier).toBe('medium');
    });

    it('score is exactly at medium threshold boundary', () => {
      const { result } = renderHook(() =>
        useAdaptivePolling({ ...testConfig, windowSize: 5, mediumActivityThreshold: 0.2 }),
      );

      // 1 out of 5 = 0.2 exactly → low (not strictly greater than 0.2)
      act(() => {
        result.current.reportPollResult(true);
        result.current.reportPollResult(false);
        result.current.reportPollResult(false);
        result.current.reportPollResult(false);
        result.current.reportPollResult(false);
      });

      expect(result.current.state.activityScore).toBe(0.2);
      expect(result.current.state.tier).toBe('low');
    });
  });
});
