import { describe, expect, it } from 'vitest';
import { act, renderHook } from '@testing-library/react';
import type { ReactNode } from 'react';
import { RateLimitProvider, useRateLimitStatus } from './RateLimitContext';
import type { RateLimitInfo } from '@/types';

function wrapper({ children }: { children: ReactNode }) {
  return <RateLimitProvider>{children}</RateLimitProvider>;
}

describe('RateLimitContext', () => {
  it('provides default state', () => {
    const { result } = renderHook(() => useRateLimitStatus(), { wrapper });
    expect(result.current.rateLimitState).toEqual({
      info: null,
      hasError: false,
    });
  });

  it('updates rate limit state', () => {
    const { result } = renderHook(() => useRateLimitStatus(), { wrapper });
    const info: RateLimitInfo = {
      limit: 5000,
      remaining: 4500,
      reset_at: Math.floor(Date.now() / 1000) + 3600,
      used: 500,
    };

    act(() => {
      result.current.updateRateLimit({ info, hasError: false });
    });

    expect(result.current.rateLimitState.info).toEqual(info);
    expect(result.current.rateLimitState.hasError).toBe(false);
  });

  it('updates error state', () => {
    const { result } = renderHook(() => useRateLimitStatus(), { wrapper });

    act(() => {
      result.current.updateRateLimit({ info: null, hasError: true });
    });

    expect(result.current.rateLimitState.hasError).toBe(true);
  });

  it('throws when used outside provider', () => {
    expect(() => {
      renderHook(() => useRateLimitStatus());
    }).toThrow('useRateLimitStatus must be used within a RateLimitProvider');
  });
});
