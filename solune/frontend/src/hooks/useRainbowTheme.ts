/**
 * Custom hook for managing the rainbow theme preference.
 *
 * The rainbow theme is orthogonal to dark/light mode. When enabled it adds
 * a `rainbow` class to <html>, which CSS uses to apply rainbow gradient
 * overlays to primary UI elements.
 *
 * When authenticated: syncs from user settings API on load, and persists
 * toggles back to API + localStorage. When unauthenticated: falls back to
 * localStorage only.
 */

import { useEffect, useCallback } from 'react';
import { useUserSettings } from '@/hooks/useSettings';

const STORAGE_KEY = 'solune-rainbow-theme';

/** Apply or remove the `rainbow` class on <html>. */
function applyRainbowClass(enabled: boolean): void {
  const root = window.document.documentElement;
  if (enabled) {
    root.classList.add('rainbow');
  } else {
    root.classList.remove('rainbow');
  }
}

export function useRainbowTheme() {
  const { settings, updateSettings } = useUserSettings();

  const isRainbow =
    settings?.display?.rainbow_theme ??
    localStorage.getItem(STORAGE_KEY) === 'true';

  // Keep <html> class in sync with effective setting.
  useEffect(() => {
    applyRainbowClass(isRainbow);
  }, [isRainbow]);

  // Sync from API settings when they load (takes precedence over localStorage).
  useEffect(() => {
    if (settings?.display?.rainbow_theme !== undefined) {
      applyRainbowClass(settings.display.rainbow_theme);
      localStorage.setItem(STORAGE_KEY, String(settings.display.rainbow_theme));
    }
  }, [settings?.display?.rainbow_theme]);

  const toggleRainbow = useCallback(() => {
    const next = !isRainbow;
    applyRainbowClass(next);
    localStorage.setItem(STORAGE_KEY, String(next));

    if (settings) {
      updateSettings({ display: { rainbow_theme: next } }).catch(() => {
        // Silently fail — localStorage is the fallback.
      });
    }
  }, [isRainbow, settings, updateSettings]);

  return {
    isRainbow,
    toggleRainbow,
  };
}
