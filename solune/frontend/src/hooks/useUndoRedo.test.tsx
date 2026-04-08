/**
 * Unit tests for useUndoRedo hook — convenience wrapper around UndoRedoContext.
 */
import { describe, it, expect } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import type { ReactNode } from 'react';
import { UndoRedoProvider } from '@/context/UndoRedoContext';
import { useUndoRedo } from './useUndoRedo';

function wrapper({ children }: { children: ReactNode }) {
  return <UndoRedoProvider>{children}</UndoRedoProvider>;
}

const sampleAction = {
  actionType: 'delete' as const,
  entityType: 'board_item' as const,
  entityId: 'item-1',
  previousState: { title: 'Old' },
  newState: {},
  description: 'Deleted item-1',
};

describe('useUndoRedo', () => {
  it('returns default state without actions', () => {
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
    expect(result.current.canRedo).toBe(false);
    expect(result.current.nextUndoDescription).toBe('Deleted item-1');
  });

  it('undo returns the undone entry and enables redo', () => {
    const { result } = renderHook(() => useUndoRedo(), { wrapper });

    act(() => {
      result.current.pushAction(sampleAction);
    });

    let undone: ReturnType<typeof result.current.undo>;
    act(() => {
      undone = result.current.undo();
    });

    expect(undone!).not.toBeNull();
    expect(undone!.entityId).toBe('item-1');
    expect(result.current.canUndo).toBe(false);
    expect(result.current.canRedo).toBe(true);
    expect(result.current.nextRedoDescription).toBe('Deleted item-1');
  });

  it('redo returns the redone entry', () => {
    const { result } = renderHook(() => useUndoRedo(), { wrapper });

    act(() => {
      result.current.pushAction(sampleAction);
    });
    act(() => {
      result.current.undo();
    });

    let redone: ReturnType<typeof result.current.redo>;
    act(() => {
      redone = result.current.redo();
    });

    expect(redone!).not.toBeNull();
    expect(redone!.entityId).toBe('item-1');
    expect(result.current.canUndo).toBe(true);
    expect(result.current.canRedo).toBe(false);
  });

  it('new action clears the redo stack', () => {
    const { result } = renderHook(() => useUndoRedo(), { wrapper });

    act(() => {
      result.current.pushAction(sampleAction);
    });
    act(() => {
      result.current.undo();
    });

    expect(result.current.canRedo).toBe(true);

    act(() => {
      result.current.pushAction({ ...sampleAction, entityId: 'item-2', description: 'Deleted item-2' });
    });

    expect(result.current.canRedo).toBe(false);
    expect(result.current.nextUndoDescription).toBe('Deleted item-2');
  });

  it('undo returns null when stack is empty', () => {
    const { result } = renderHook(() => useUndoRedo(), { wrapper });

    let undone: ReturnType<typeof result.current.undo>;
    act(() => {
      undone = result.current.undo();
    });

    expect(undone!).toBeNull();
  });

  it('redo returns null when stack is empty', () => {
    const { result } = renderHook(() => useUndoRedo(), { wrapper });

    let redone: ReturnType<typeof result.current.redo>;
    act(() => {
      redone = result.current.redo();
    });

    expect(redone!).toBeNull();
  });
});
