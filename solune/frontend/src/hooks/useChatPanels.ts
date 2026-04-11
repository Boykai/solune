/**
 * useChatPanels hook — manages open chat panel set with persistence.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { generateId } from '@/utils/generateId';

const STORAGE_KEY = 'solune:chat-panels';
const SCHEMA_VERSION = 1;
const MIN_WIDTH_PX = 320;

export interface PanelState {
  panelId: string;
  conversationId: string;
  widthPercent: number;
}

interface PanelLayout {
  version: number;
  panels: PanelState[];
}

function createDefaultPanel(conversationId: string): PanelState {
  return {
    panelId: generateId(),
    conversationId,
    widthPercent: 100,
  };
}

function redistributeWidths(panels: PanelState[]): PanelState[] {
  if (panels.length === 0) return panels;
  const w = 100 / panels.length;
  return panels.map((p) => ({ ...p, widthPercent: w }));
}

function loadLayout(): PanelLayout | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as PanelLayout;
    if (parsed.version !== SCHEMA_VERSION || !Array.isArray(parsed.panels) || parsed.panels.length === 0) {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

function saveLayout(panels: PanelState[]): void {
  try {
    const layout: PanelLayout = { version: SCHEMA_VERSION, panels };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(layout));
  } catch {
    // localStorage may be full or disabled — ignore
  }
}

export interface UseChatPanelsReturn {
  panels: PanelState[];
  addPanel: (conversationId: string) => void;
  removePanel: (panelId: string) => void;
  resizePanels: (leftPanelId: string, rightPanelId: string, leftPercent: number, rightPercent: number) => void;
  updatePanelConversation: (panelId: string, conversationId: string) => void;
  containerRef: React.RefObject<HTMLDivElement | null>;
  minWidthPx: number;
}

export function useChatPanels(initialConversationId?: string): UseChatPanelsReturn {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [panels, setPanels] = useState<PanelState[]>(() => {
    const saved = loadLayout();
    if (saved) return saved.panels;
    // Will be populated on mount when initialConversationId is available
    return [];
  });

  // Initialize with a default panel if nothing loaded from storage.
  // This is an initialization pattern — the effect only runs when
  // initialConversationId is first provided.
  useEffect(() => {
    if (panels.length === 0 && initialConversationId) {
      setPanels([createDefaultPanel(initialConversationId)]); // eslint-disable-line react-hooks/set-state-in-effect
    }
  }, [initialConversationId]); // eslint-disable-line react-hooks/exhaustive-deps

  // Debounced persist to localStorage
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  useEffect(() => {
    if (panels.length === 0) return;
    clearTimeout(saveTimerRef.current);
    saveTimerRef.current = setTimeout(() => saveLayout(panels), 300);
    return () => clearTimeout(saveTimerRef.current);
  }, [panels]);

  const addPanel = useCallback((conversationId: string) => {
    setPanels((prev) => {
      const newPanel: PanelState = {
        panelId: generateId(),
        conversationId,
        widthPercent: 0, // will be redistributed
      };
      return redistributeWidths([...prev, newPanel]);
    });
  }, []);

  const removePanel = useCallback((panelId: string) => {
    setPanels((prev) => {
      // Prevent removal of the last panel
      if (prev.length <= 1) return prev;
      const remaining = prev.filter((p) => p.panelId !== panelId);
      return redistributeWidths(remaining);
    });
  }, []);

  const resizePanels = useCallback(
    (leftPanelId: string, rightPanelId: string, leftPercent: number, rightPercent: number) => {
      setPanels((prev) =>
        prev.map((p) => {
          if (p.panelId === leftPanelId) return { ...p, widthPercent: leftPercent };
          if (p.panelId === rightPanelId) return { ...p, widthPercent: rightPercent };
          return p;
        }),
      );
    },
    [],
  );

  const updatePanelConversation = useCallback((panelId: string, conversationId: string) => {
    setPanels((prev) =>
      prev.map((p) => (p.panelId === panelId ? { ...p, conversationId } : p)),
    );
  }, []);

  return {
    panels,
    addPanel,
    removePanel,
    resizePanels,
    updatePanelConversation,
    containerRef,
    minWidthPx: MIN_WIDTH_PX,
  };
}
