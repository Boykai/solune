/**
 * Tests for useBoardProjection hook.
 *
 * Covers initial projection computation, buffer-based rendering, column
 * expansion, dataset totals, and reset on new board data.
 */

import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useBoardProjection } from './useBoardProjection';
import type { BoardDataResponse, BoardColumn, BoardItem, BoardStatusOption } from '@/types';

// ── Helpers ────────────────────────────────────────────────────────────

function makeStatus(name: string): BoardStatusOption {
  return { option_id: `opt-${name}`, name, color: 'GRAY' };
}

function makeItem(id: string): BoardItem {
  return {
    item_id: id,
    content_type: 'issue',
    title: `Item ${id}`,
    status: 'Todo',
    status_option_id: 'opt-todo',
    assignees: [],
    linked_prs: [],
    sub_issues: [],
    labels: [],
  };
}

function makeColumn(name: string, itemCount: number): BoardColumn {
  return {
    status: makeStatus(name),
    items: Array.from({ length: itemCount }, (_, i) => makeItem(`${name}-${i}`)),
    item_count: itemCount,
    estimate_total: 0,
  };
}

function makeBoardData(columns: BoardColumn[]): BoardDataResponse {
  return {
    project: {
      project_id: 'proj-1',
      name: 'Test Project',
      url: 'https://example.com',
      owner_login: 'testowner',
      status_field: {
        field_id: 'sf-1',
        options: columns.map((c) => c.status),
      },
    },
    columns,
  };
}

// ── Tests ──────────────────────────────────────────────────────────────

describe('useBoardProjection', () => {
  // Mock IntersectionObserver
  let observerInstances: Map<Element, { callback: IntersectionObserverCallback; options?: IntersectionObserverInit }>;

  beforeEach(() => {
    observerInstances = new Map();

    const MockIntersectionObserver = vi.fn(
      function (this: unknown, callback: IntersectionObserverCallback, options?: IntersectionObserverInit) {
        const instance = {
          observe: vi.fn((element: Element) => {
            observerInstances.set(element, { callback, options });
          }),
          unobserve: vi.fn(),
          disconnect: vi.fn(),
        };
        return instance;
      },
    );

    vi.stubGlobal('IntersectionObserver', MockIntersectionObserver);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // ── Null board data ──

  describe('null board data', () => {
    it('returns empty projections for null board data', () => {
      const { result } = renderHook(() => useBoardProjection(null));
      expect(result.current.columnProjections.size).toBe(0);
      expect(result.current.totalRenderedItems).toBe(0);
      expect(result.current.totalDatasetItems).toBe(0);
    });

    it('isInitialRenderComplete is false for null data', () => {
      const { result } = renderHook(() => useBoardProjection(null));
      expect(result.current.isInitialRenderComplete).toBe(false);
    });
  });

  // ── Initial projection ──

  describe('initial projection', () => {
    it('creates projections for each column', () => {
      const data = makeBoardData([
        makeColumn('Todo', 5),
        makeColumn('In Progress', 3),
        makeColumn('Done', 8),
      ]);

      const { result } = renderHook(() => useBoardProjection(data));

      expect(result.current.columnProjections.size).toBe(3);
      expect(result.current.columnProjections.has('Todo')).toBe(true);
      expect(result.current.columnProjections.has('In Progress')).toBe(true);
      expect(result.current.columnProjections.has('Done')).toBe(true);
    });

    it('limits rendered range to buffer size', () => {
      const data = makeBoardData([makeColumn('Todo', 50)]);

      const { result } = renderHook(() =>
        useBoardProjection(data, { bufferSize: 10 }),
      );

      const proj = result.current.columnProjections.get('Todo')!;
      expect(proj.renderedRange.start).toBe(0);
      expect(proj.renderedRange.end).toBe(10);
      expect(proj.hasMore).toBe(true);
      expect(proj.totalItems).toBe(50);
    });

    it('renders all items when column has fewer than buffer size', () => {
      const data = makeBoardData([makeColumn('Todo', 3)]);

      const { result } = renderHook(() =>
        useBoardProjection(data, { bufferSize: 10 }),
      );

      const proj = result.current.columnProjections.get('Todo')!;
      expect(proj.renderedRange.end).toBe(3);
      expect(proj.hasMore).toBe(false);
    });

    it('uses default buffer of 10 when no config is provided', () => {
      const data = makeBoardData([makeColumn('Todo', 50)]);

      const { result } = renderHook(() => useBoardProjection(data));

      const proj = result.current.columnProjections.get('Todo')!;
      expect(proj.renderedRange.end).toBe(10);
    });
  });

  // ── Dataset totals ──

  describe('dataset totals', () => {
    it('totalDatasetItems counts all items across columns', () => {
      const data = makeBoardData([
        makeColumn('Todo', 10),
        makeColumn('In Progress', 5),
        makeColumn('Done', 20),
      ]);

      const { result } = renderHook(() => useBoardProjection(data));
      expect(result.current.totalDatasetItems).toBe(35);
    });

    it('totalRenderedItems reflects capped projections', () => {
      const data = makeBoardData([
        makeColumn('Todo', 50),
        makeColumn('Done', 3),
      ]);

      const { result } = renderHook(() =>
        useBoardProjection(data, { bufferSize: 10 }),
      );

      // Todo: 10 rendered, Done: 3 rendered
      expect(result.current.totalRenderedItems).toBe(13);
    });

    it('totalDatasetItems is 0 for null data', () => {
      const { result } = renderHook(() => useBoardProjection(null));
      expect(result.current.totalDatasetItems).toBe(0);
    });
  });

  // ── Board data reset ──

  describe('board data changes', () => {
    it('resets expansions when board data changes', () => {
      const data1 = makeBoardData([makeColumn('Todo', 50)]);
      const data2 = makeBoardData([makeColumn('Todo', 30)]);

      const { result, rerender } = renderHook(
        ({ data }) => useBoardProjection(data, { bufferSize: 5 }),
        { initialProps: { data: data1 } },
      );

      // Verify initial projection
      expect(result.current.columnProjections.get('Todo')!.renderedRange.end).toBe(5);

      // Switch to new data
      rerender({ data: data2 });

      // Should reset to buffer size for new data
      const proj = result.current.columnProjections.get('Todo')!;
      expect(proj.renderedRange.end).toBe(5);
      expect(proj.totalItems).toBe(30);
    });

    it('handles transition from null to real data', () => {
      const data = makeBoardData([makeColumn('Todo', 10)]);

      const { result, rerender } = renderHook(
        ({ data: d }) => useBoardProjection(d),
        { initialProps: { data: null as BoardDataResponse | null } },
      );

      expect(result.current.columnProjections.size).toBe(0);

      rerender({ data });
      expect(result.current.columnProjections.size).toBe(1);
      expect(result.current.totalDatasetItems).toBe(10);
    });
  });

  // ── Observer ref factory ──

  describe('observerRef', () => {
    it('returns a function for each column ID', () => {
      const data = makeBoardData([makeColumn('Todo', 50)]);
      const { result } = renderHook(() => useBoardProjection(data));

      const refFn = result.current.observerRef('Todo');
      expect(typeof refFn).toBe('function');
    });

    it('creates IntersectionObserver when node is attached', () => {
      const data = makeBoardData([makeColumn('Todo', 50)]);
      const { result } = renderHook(() => useBoardProjection(data));

      const node = document.createElement('div');
      act(() => {
        result.current.observerRef('Todo')(node);
      });

      expect(IntersectionObserver).toHaveBeenCalled();
    });

    it('cleans up observer when node is detached (null)', () => {
      const data = makeBoardData([makeColumn('Todo', 50)]);
      const { result } = renderHook(() => useBoardProjection(data));

      const node = document.createElement('div');

      act(() => {
        result.current.observerRef('Todo')(node);
      });

      // Detach
      act(() => {
        result.current.observerRef('Todo')(null);
      });

      // Observer should have been disconnected
      const mockObserverInstances = vi.mocked(IntersectionObserver).mock.results;
      const lastInstance = mockObserverInstances[mockObserverInstances.length - 1]?.value;
      if (lastInstance) {
        expect(lastInstance.disconnect).toHaveBeenCalled();
      }
    });
  });

  // ── Empty columns ──

  describe('edge cases', () => {
    it('handles board with empty columns', () => {
      const data = makeBoardData([
        makeColumn('Empty', 0),
        makeColumn('Full', 5),
      ]);

      const { result } = renderHook(() => useBoardProjection(data, { bufferSize: 10 }));

      const emptyProj = result.current.columnProjections.get('Empty')!;
      expect(emptyProj.renderedRange.end).toBe(0);
      expect(emptyProj.hasMore).toBe(false);
      expect(emptyProj.totalItems).toBe(0);

      const fullProj = result.current.columnProjections.get('Full')!;
      expect(fullProj.renderedRange.end).toBe(5);
      expect(fullProj.hasMore).toBe(false);
    });

    it('handles board with no columns', () => {
      const data: BoardDataResponse = {
        project: {
          project_id: 'proj-1',
          name: 'Empty',
          url: 'https://example.com',
          owner_login: 'testowner',
          status_field: { field_id: 'sf-1', options: [] },
        },
        columns: [],
      };

      const { result } = renderHook(() => useBoardProjection(data));
      expect(result.current.columnProjections.size).toBe(0);
      expect(result.current.totalDatasetItems).toBe(0);
      expect(result.current.totalRenderedItems).toBe(0);
    });

    it('bufferSize of 1 renders only 1 item per column', () => {
      const data = makeBoardData([makeColumn('Todo', 100)]);

      const { result } = renderHook(() =>
        useBoardProjection(data, { bufferSize: 1 }),
      );

      const proj = result.current.columnProjections.get('Todo')!;
      expect(proj.renderedRange.end).toBe(1);
      expect(proj.hasMore).toBe(true);
    });
  });
});
