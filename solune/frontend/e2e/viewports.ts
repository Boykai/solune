/**
 * Viewport preset constants for Playwright E2E tests.
 *
 * Defines standard breakpoints for responsive layout testing.
 */

export const VIEWPORTS = {
  mobile: { width: 375, height: 667 },
  'mobile-lg': { width: 414, height: 896 },
  tablet: { width: 768, height: 1024 },
  'tablet-lg': { width: 820, height: 1180 },
  desktop: { width: 1280, height: 800 },
} as const;

export type ViewportName = keyof typeof VIEWPORTS;
