import { describe, expect, it, vi, beforeEach } from 'vitest';
import { act, renderHook } from '@testing-library/react';
import { useContext, type ReactNode } from 'react';
import { UndoRedoContext, UndoRedoProvider, type ActionHistoryEntry } from './UndoRedoContext';

function wrapper({ children }: { children: ReactNode }) {
  return <UndoRedoProvider undoWindowMs={30_000}>{children}</UndoRedoProvider>;
}

function useUndoRedo() {
  return useContext(UndoRedoContext);
}

const sampleAction: Omit<ActionHistoryEntry, 'id' | 'timestamp' | 'expiresAt'> = {
  actionType: 'archive',
  entityType: 'board_item',
  entityId: 'item-1',
  previousState: { status: 'active' },
  newState: { status: 'archived' },
  description: 'Archive item',
};

describe('UndoRedoContext', () => {
  beforeEach(() => {
    vi.useRealTimers();
  });

  it('starts with empty stacks', () => {
    const { result } = renderHook(() => useUndoRedo(), { wrapper });
    expect(result.current.canUndo).toBe(false);
    expect(result.current.canRedo).toBe(false);
    expect(result.current.nextUndoDescription).toBeNull();
    expect(result.current.nextRedoDescription).toBeNull();
  });

  it('pushAction enables undo', () => {
    const { result } = renderHook(() => useUndoRedo(), { wrapper });

    act(() => {
      result.current.pushAction(sampleAction);
    });

    expect(result.current.canUndo).toBe(true);
    expect(result.current.nextUndoDescription).toBe('Archive item');
  });

  it('undo pops the last action', () => {
    const { result } = renderHook(() => useUndoRedo(), { wrapper });

    act(() => {
      result.current.pushAction(sampleAction);
    });

    let undone: ActionHistoryEntry | null = null;
    act(() => {
      undone = result.current.undo();
    });

    expect(undone).not.toBeNull();
    expect(undone!.description).toBe('Archive item');
    expect(result.current.canUndo).toBe(false);
    expect(result.current.canRedo).toBe(true);
  });

  it('redo restores the undone action', () => {
    const { result } = renderHook(() => useUndoRedo(), { wrapper });

    act(() => {
      result.current.pushAction(sampleAction);
    });
    act(() => {
      result.current.undo();
    });

    let redone: ActionHistoryEntry | null = null;
    act(() => {
      redone = result.current.redo();
    });

    expect(redone).not.toBeNull();
    expect(redone!.description).toBe('Archive item');
    expect(result.current.canUndo).toBe(true);
    expect(result.current.canRedo).toBe(false);
  });

  it('new action clears redo stack', () => {
    const { result } = renderHook(() => useUndoRedo(), { wrapper });

    act(() => {
      result.current.pushAction(sampleAction);
    });
    act(() => {
      result.current.undo();
    });
    expect(result.current.canRedo).toBe(true);

    act(() => {
      result.current.pushAction({ ...sampleAction, description: 'Another action' });
    });
    expect(result.current.canRedo).toBe(false);
  });

  it('undo on empty stack returns null', () => {
    const { result } = renderHook(() => useUndoRedo(), { wrapper });
    let undone: ActionHistoryEntry | null = null;
    act(() => {
      undone = result.current.undo();
    });
    expect(undone).toBeNull();
  });

  it('redo on empty stack returns null', () => {
    const { result } = renderHook(() => useUndoRedo(), { wrapper });
    let redone: ActionHistoryEntry | null = null;
    act(() => {
      redone = result.current.redo();
    });
    expect(redone).toBeNull();
  });

  it('expired entries are removed', () => {
    vi.useFakeTimers();
    const { result } = renderHook(() => useUndoRedo(), {
      wrapper: ({ children }: { children: ReactNode }) => (
        <UndoRedoProvider undoWindowMs={1_000}>{children}</UndoRedoProvider>
      ),
    });

    act(() => {
      result.current.pushAction(sampleAction);
    });
    expect(result.current.canUndo).toBe(true);

    // Advance past the undo window + expiry check interval
    act(() => {
      vi.advanceTimersByTime(6_000);
    });

    expect(result.current.canUndo).toBe(false);
    vi.useRealTimers();
  });

  it('LIFO order is respected with multiple entries', () => {
    const { result } = renderHook(() => useUndoRedo(), { wrapper });

    act(() => {
      result.current.pushAction({ ...sampleAction, description: 'First' });
    });
    act(() => {
      result.current.pushAction({ ...sampleAction, description: 'Second' });
    });

    expect(result.current.nextUndoDescription).toBe('Second');

    let undone: ActionHistoryEntry | null = null;
    act(() => {
      undone = result.current.undo();
    });
    expect(undone!.description).toBe('Second');
    expect(result.current.nextUndoDescription).toBe('First');
  });
});
