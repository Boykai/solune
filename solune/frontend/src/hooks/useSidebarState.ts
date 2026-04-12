/**
 * useSidebarState — manages sidebar collapse state with localStorage persistence.
 */

import { useState, useCallback } from 'react';

const STORAGE_KEY = 'sidebar-collapsed';

function loadCollapsed(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) === 'true';
  } catch {
    return false;
  }
}

export function useSidebarState() {
  const [isCollapsed, setIsCollapsed] = useState(loadCollapsed);

  const setCollapsed = useCallback((next: boolean) => {
    setIsCollapsed((prev) => {
      if (prev === next) {
        return prev;
      }

      try {
        localStorage.setItem(STORAGE_KEY, String(next));
      } catch {
        /* ignore */
      }

      return next;
    });
  }, []);

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

  return { isCollapsed, setCollapsed, toggle };
}
