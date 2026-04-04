/**
 * Tests for constants.ts — application-wide constant values.
 */
import { describe, it, expect } from 'vitest';
import {
  STALE_TIME_LONG,
  STALE_TIME_PROJECTS,
  STALE_TIME_MEDIUM,
  STALE_TIME_SHORT,
  BOARD_POLL_INTERVAL_MS,
  WS_FALLBACK_POLL_MS,
  WS_RECONNECT_DELAY_MS,
  WS_CONNECTION_TIMEOUT_MS,
  AUTO_REFRESH_INTERVAL_MS,
  RATE_LIMIT_LOW_THRESHOLD,
  PROPOSAL_EXPIRY_MS,
  TOAST_SUCCESS_MS,
  TOAST_ERROR_MS,
  HIGHLIGHT_DURATION_MS,
  NAV_ROUTES,
  PRIORITY_COLORS,
} from './constants';

describe('Cache/Stale Time Constants', () => {
  it('stale times are positive numbers in milliseconds', () => {
    expect(STALE_TIME_LONG).toBeGreaterThan(0);
    expect(STALE_TIME_PROJECTS).toBeGreaterThan(0);
    expect(STALE_TIME_MEDIUM).toBeGreaterThan(0);
    expect(STALE_TIME_SHORT).toBeGreaterThan(0);
  });

  it('long stale time is greater than medium', () => {
    expect(STALE_TIME_LONG).toBeGreaterThan(STALE_TIME_MEDIUM);
  });

  it('projects stale time is the longest', () => {
    expect(STALE_TIME_PROJECTS).toBeGreaterThanOrEqual(STALE_TIME_LONG);
  });
});

describe('Polling/WebSocket Constants', () => {
  it('board poll interval is at least 30 seconds', () => {
    expect(BOARD_POLL_INTERVAL_MS).toBeGreaterThanOrEqual(30_000);
  });

  it('WebSocket fallback interval is positive', () => {
    expect(WS_FALLBACK_POLL_MS).toBeGreaterThan(0);
  });

  it('WebSocket reconnect delay is positive', () => {
    expect(WS_RECONNECT_DELAY_MS).toBeGreaterThan(0);
  });

  it('WebSocket connection timeout is positive', () => {
    expect(WS_CONNECTION_TIMEOUT_MS).toBeGreaterThan(0);
  });
});

describe('UI Timing Constants', () => {
  it('auto refresh interval is at least 1 minute', () => {
    expect(AUTO_REFRESH_INTERVAL_MS).toBeGreaterThanOrEqual(60_000);
  });

  it('rate limit threshold is a positive number', () => {
    expect(RATE_LIMIT_LOW_THRESHOLD).toBeGreaterThan(0);
  });

  it('proposal expiry is at least 1 minute', () => {
    expect(PROPOSAL_EXPIRY_MS).toBeGreaterThanOrEqual(60_000);
  });

  it('toast durations are positive', () => {
    expect(TOAST_SUCCESS_MS).toBeGreaterThan(0);
    expect(TOAST_ERROR_MS).toBeGreaterThan(0);
  });

  it('error toast is at least as long as success toast', () => {
    expect(TOAST_ERROR_MS).toBeGreaterThanOrEqual(TOAST_SUCCESS_MS);
  });

  it('highlight duration is positive', () => {
    expect(HIGHLIGHT_DURATION_MS).toBeGreaterThan(0);
  });
});

describe('NAV_ROUTES', () => {
  it('has at least 5 routes', () => {
    expect(NAV_ROUTES.length).toBeGreaterThanOrEqual(5);
  });

  it('each route has path, label, and icon', () => {
    for (const route of NAV_ROUTES) {
      expect(route.path).toBeTruthy();
      expect(route.label).toBeTruthy();
      expect(route.icon).toBeDefined();
    }
  });

  it('first route is the app root', () => {
    expect(NAV_ROUTES[0].path).toBe('/');
  });

  it('all paths start with /', () => {
    for (const route of NAV_ROUTES) {
      expect(route.path.startsWith('/')).toBe(true);
    }
  });

  it('includes Settings route', () => {
    expect(NAV_ROUTES.some((r) => r.label === 'Settings')).toBe(true);
  });

  it('includes Projects route', () => {
    expect(NAV_ROUTES.some((r) => r.label === 'Projects')).toBe(true);
  });
});

describe('PRIORITY_COLORS', () => {
  it('has P0-P3 priority levels', () => {
    expect(PRIORITY_COLORS.P0).toBeDefined();
    expect(PRIORITY_COLORS.P1).toBeDefined();
    expect(PRIORITY_COLORS.P2).toBeDefined();
    expect(PRIORITY_COLORS.P3).toBeDefined();
  });

  it('each priority has bg, text, and label', () => {
    for (const [, colors] of Object.entries(PRIORITY_COLORS)) {
      expect(colors.bg).toBeTruthy();
      expect(colors.text).toBeTruthy();
      expect(colors.label).toBeTruthy();
    }
  });

  it('P0 is labeled Critical', () => {
    expect(PRIORITY_COLORS.P0.label).toBe('Critical');
  });

  it('P3 is labeled Low', () => {
    expect(PRIORITY_COLORS.P3.label).toBe('Low');
  });
});
