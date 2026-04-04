/**
 * useCountdown — returns the remaining time in seconds until an ISO timestamp,
 * updating every second. Returns 0 once expired.
 */

import { useState, useEffect } from 'react';

function secondsUntil(isoTimestamp: string): number {
  return Math.max(0, Math.floor((new Date(isoTimestamp).getTime() - Date.now()) / 1000));
}

export function useCountdown(expiresAt: string): number {
  const [remaining, setRemaining] = useState(() => secondsUntil(expiresAt));

  useEffect(() => {
    const id = setInterval(() => {
      const next = secondsUntil(expiresAt);
      setRemaining(next);
      if (next <= 0) clearInterval(id);
    }, 1000);
    return () => clearInterval(id);
  }, [expiresAt]);

  return remaining;
}

/** Format seconds into "Xm Ys" or "Xs" */
export function formatCountdown(seconds: number): string {
  if (seconds <= 0) return 'Expired';
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}
