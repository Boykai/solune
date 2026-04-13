import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useChatPanels, type PanelState } from '@/hooks/useChatPanels';

const STORAGE_KEY = 'solune:chat-panels';

// Mock generateId to produce deterministic IDs
let idCounter = 0;
vi.mock('@/utils/generateId', () => ({
  generateId: () => `panel-${++idCounter}`,
}));

beforeEach(() => {
  idCounter = 0;
  localStorage.clear();
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
  vi.clearAllTimers();
});

describe('useChatPanels', () => {
  describe('initialization', () => {
    it('starts with empty panels when no localStorage and no initialConversationId', () => {
      const { result } = renderHook(() => useChatPanels());
      expect(result.current.panels).toEqual([]);
    });

    it('creates a default panel when initialConversationId is provided', () => {
      const { result } = renderHook(() => useChatPanels('conv-1'));
      expect(result.current.panels).toHaveLength(1);
      expect(result.current.panels[0].conversationId).toBe('conv-1');
      expect(result.current.panels[0].widthPercent).toBe(100);
    });

    it('restores panels from localStorage', () => {
      const saved: PanelState[] = [
        { panelId: 'saved-1', conversationId: 'conv-a', widthPercent: 50 },
        { panelId: 'saved-2', conversationId: 'conv-b', widthPercent: 50 },
      ];
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ version: 1, panels: saved }));

      const { result } = renderHook(() => useChatPanels());
      expect(result.current.panels).toHaveLength(2);
      expect(result.current.panels[0].panelId).toBe('saved-1');
      expect(result.current.panels[1].panelId).toBe('saved-2');
    });

    it('ignores corrupted localStorage data', () => {
      localStorage.setItem(STORAGE_KEY, 'not-valid-json');
      const { result } = renderHook(() => useChatPanels());
      expect(result.current.panels).toEqual([]);
    });

    it('ignores localStorage with wrong schema version', () => {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ version: 999, panels: [{ panelId: 'x', conversationId: 'y', widthPercent: 100 }] }));
      const { result } = renderHook(() => useChatPanels());
      expect(result.current.panels).toEqual([]);
    });

    it('ignores localStorage with empty panels array', () => {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ version: 1, panels: [] }));
      const { result } = renderHook(() => useChatPanels());
      expect(result.current.panels).toEqual([]);
    });

    it('does not duplicate panels when initialConversationId is provided and panels already exist from localStorage', () => {
      const saved: PanelState[] = [
        { panelId: 'existing', conversationId: 'conv-old', widthPercent: 100 },
      ];
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ version: 1, panels: saved }));

      const { result } = renderHook(() => useChatPanels('conv-new'));
      // Should not add another panel since panels already exist
      expect(result.current.panels).toHaveLength(1);
      expect(result.current.panels[0].panelId).toBe('existing');
    });

    it('recreates a default panel when stale persisted panels are removed after bootstrap', () => {
      const saved: PanelState[] = [
        { panelId: 'stale-1', conversationId: 'conv-stale', widthPercent: 100 },
      ];
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ version: 1, panels: saved }));

      const { result } = renderHook(() => useChatPanels('conv-current'));

      expect(result.current.panels).toHaveLength(1);
      expect(result.current.panels[0].conversationId).toBe('conv-stale');

      act(() => {
        result.current.removeStalePanels(new Set(['conv-current']));
      });

      expect(result.current.panels).toHaveLength(1);
      expect(result.current.panels[0].conversationId).toBe('conv-current');
    });
  });

  describe('addPanel', () => {
    it('adds a panel and redistributes widths equally', () => {
      const { result } = renderHook(() => useChatPanels('conv-1'));
      expect(result.current.panels).toHaveLength(1);

      act(() => result.current.addPanel('conv-2'));

      expect(result.current.panels).toHaveLength(2);
      expect(result.current.panels[0].widthPercent).toBe(50);
      expect(result.current.panels[1].widthPercent).toBe(50);
      expect(result.current.panels[1].conversationId).toBe('conv-2');
    });

    it('redistributes to thirds when adding a third panel', () => {
      const { result } = renderHook(() => useChatPanels('conv-1'));

      act(() => result.current.addPanel('conv-2'));
      act(() => result.current.addPanel('conv-3'));

      expect(result.current.panels).toHaveLength(3);
      for (const panel of result.current.panels) {
        expect(panel.widthPercent).toBeCloseTo(100 / 3, 5);
      }
    });
  });

  describe('removePanel', () => {
    it('removes a panel and redistributes remaining widths', () => {
      const { result } = renderHook(() => useChatPanels('conv-1'));
      act(() => result.current.addPanel('conv-2'));

      const panelToRemove = result.current.panels[1].panelId;
      act(() => result.current.removePanel(panelToRemove));

      expect(result.current.panels).toHaveLength(1);
      expect(result.current.panels[0].widthPercent).toBe(100);
      expect(result.current.panels[0].conversationId).toBe('conv-1');
    });

    it('prevents removal of the last panel', () => {
      const { result } = renderHook(() => useChatPanels('conv-1'));
      expect(result.current.panels).toHaveLength(1);

      const panelId = result.current.panels[0].panelId;
      act(() => result.current.removePanel(panelId));

      // Panel should still be there
      expect(result.current.panels).toHaveLength(1);
    });
  });

  describe('resizePanels', () => {
    it('updates widths of two specified panels', () => {
      const { result } = renderHook(() => useChatPanels('conv-1'));
      act(() => result.current.addPanel('conv-2'));

      const leftId = result.current.panels[0].panelId;
      const rightId = result.current.panels[1].panelId;

      act(() => result.current.resizePanels(leftId, rightId, 30, 70));

      expect(result.current.panels[0].widthPercent).toBe(30);
      expect(result.current.panels[1].widthPercent).toBe(70);
    });
  });

  describe('updatePanelConversation', () => {
    it('switches a panel to a different conversation', () => {
      const { result } = renderHook(() => useChatPanels('conv-1'));

      const panelId = result.current.panels[0].panelId;
      act(() => result.current.updatePanelConversation(panelId, 'conv-new'));

      expect(result.current.panels[0].conversationId).toBe('conv-new');
    });
  });

  describe('persistence', () => {
    it('saves panel layout to localStorage after debounce', () => {
      const { result } = renderHook(() => useChatPanels('conv-1'));
      expect(result.current.panels).toHaveLength(1);

      // Fast-forward debounce timer
      act(() => vi.advanceTimersByTime(400));

      const stored = localStorage.getItem(STORAGE_KEY);
      expect(stored).not.toBeNull();
      const parsed = JSON.parse(stored!);
      expect(parsed.version).toBe(1);
      expect(parsed.panels).toHaveLength(1);
      expect(parsed.panels[0].conversationId).toBe('conv-1');
    });

    it('does not persist empty panels', () => {
      renderHook(() => useChatPanels());
      act(() => vi.advanceTimersByTime(400));

      expect(localStorage.getItem(STORAGE_KEY)).toBeNull();
    });

    it('clears a previously saved layout when panels become empty', () => {
      const saved: PanelState[] = [
        { panelId: 'stale-1', conversationId: 'conv-stale', widthPercent: 100 },
      ];
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ version: 1, panels: saved }));

      const { result } = renderHook(() => useChatPanels());

      act(() => {
        result.current.removeStalePanels(new Set());
      });

      act(() => vi.advanceTimersByTime(400));

      expect(localStorage.getItem(STORAGE_KEY)).toBeNull();
    });
  });

  describe('minWidthPx', () => {
    it('exposes MIN_WIDTH_PX as 320', () => {
      const { result } = renderHook(() => useChatPanels());
      expect(result.current.minWidthPx).toBe(320);
    });
  });
});
