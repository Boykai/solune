/**
 * useSidebarState — manages sidebar collapse state with localStorage persistence.
 */

import { useState, useCallback } from 'react';

const STORAGE_KEY = 'sidebar-collapsed';
const MOBILE_QUERY = '(max-width: 767px)';

function isMobileViewport(): boolean {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
    return false;
  }

  try {
    return window.matchMedia(MOBILE_QUERY).matches;
  } catch {
    return false;
  }
}

function loadCollapsed(): boolean {
  if (isMobileViewport()) {
    return true;
  }

  try {
    return localStorage.getItem(STORAGE_KEY) === 'true';
  } catch {
    return false;
  }
}

export function useSidebarState() {
  const [isCollapsed, setIsCollapsed] = useState(loadCollapsed);

  const toggle = useCallback(() => {
    setIsCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem(STORAGE_KEY, String(next));
      } catch {
        /* ignore */
      }
      return next;
    });
  }, []);

  return { isCollapsed, toggle };
}
