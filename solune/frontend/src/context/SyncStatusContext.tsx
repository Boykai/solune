/**
 * SyncStatusContext — shares real-time sync state (connection status + last update timestamp)
 * so that the TopBar can render a connectivity indicator regardless of the active route.
 */

import { createContext, useCallback, useContext, useMemo, useRef, useState, type ReactNode } from 'react';

type SyncStatus = 'disconnected' | 'connecting' | 'connected' | 'polling';

interface SyncStatusState {
  status: SyncStatus;
  lastUpdate: Date | null;
}

interface SyncStatusContextValue extends SyncStatusState {
  /** Called by the page that owns useRealTimeSync to push updates into the global context. */
  updateSyncStatus: (status: SyncStatus, lastUpdate: Date | null) => void;
}

function isSameLastUpdate(a: Date | null, b: Date | null): boolean {
  if (a === b) return true;
  if (!a || !b) return false;
  return a.getTime() === b.getTime();
}

const SyncStatusContext = createContext<SyncStatusContextValue>({
  status: 'disconnected',
  lastUpdate: null,
  updateSyncStatus: () => {},
});

export function SyncStatusProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<SyncStatusState>({
    status: 'disconnected',
    lastUpdate: null,
  });
  const stateRef = useRef(state);

  const updateSyncStatus = useCallback((status: SyncStatus, lastUpdate: Date | null) => {
    const prev = stateRef.current;
    if (prev.status === status && isSameLastUpdate(prev.lastUpdate, lastUpdate)) return;
    const next = { status, lastUpdate };
    stateRef.current = next;
    setState(next);
  }, []);

  const value = useMemo(
    () => ({ ...state, updateSyncStatus }),
    [state, updateSyncStatus],
  );

  return <SyncStatusContext.Provider value={value}>{children}</SyncStatusContext.Provider>;
}

export function useSyncStatusContext() {
  return useContext(SyncStatusContext);
}
