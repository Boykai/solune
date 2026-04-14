/**
 * ChoresPanel — container for the Chores feature on the project board.
 *
 * Composes ChoresToolbar, ChoresGrid, and ChoresSaveAllBar.
 * Handles inline editing with dirty tracking, filtering,
 * sorting, and loading/error/empty states.
 */

import { useCallback, useDeferredValue, useEffect, useMemo, useState } from 'react';
import { ScrollText } from '@/lib/icons';
import { useChoresListPaginated, useInlineUpdateChore } from '@/hooks/useChores';
import type { ChoresFilterParams } from '@/hooks/useChores';
import { ChoresToolbar } from './ChoresToolbar';
import { ChoresGrid } from './ChoresGrid';
import { ChoresSaveAllBar } from './ChoresSaveAllBar';
import { CelestialLoader } from '@/components/common/CelestialLoader';
import { isRateLimitApiError } from '@/utils/rateLimit';
import type { Chore, ChoreEditState, ChoreInlineUpdate } from '@/types';
import type { ChoreStatusFilter, ScheduleFilter, ChoreSortMode } from './ChoresToolbar';
import { Button } from '@/components/ui/button';

interface ChoresPanelProps {
  projectId: string;
  parentIssueCount?: number;
  onDirtyChange?: (isDirty: boolean) => void;
}

export function ChoresPanel({
  projectId,
  parentIssueCount = 0,
  onDirtyChange,
}: ChoresPanelProps) {
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<ChoreStatusFilter>('all');
  const [scheduleFilter, setScheduleFilter] = useState<ScheduleFilter>('all');
  const [sortMode, setSortMode] = useState<ChoreSortMode>('attention');
  const deferredSearch = useDeferredValue(search);

  // ── Server-side filter params ──
  const sortMap: Record<ChoreSortMode, Pick<ChoresFilterParams, 'sort' | 'order'>> = {
    attention: { sort: 'attention', order: 'asc' },
    updated: { sort: 'updated_at', order: 'desc' },
    name: { sort: 'name', order: 'asc' },
  };
  const filterParams: ChoresFilterParams = {
    ...(statusFilter !== 'all' ? { status: statusFilter } : {}),
    ...(scheduleFilter !== 'all' ? { scheduleType: scheduleFilter } : {}),
    ...(deferredSearch.trim() ? { search: deferredSearch.trim() } : {}),
    ...sortMap[sortMode],
  };

  const {
    allItems: chores,
    isLoading,
    error,
    refetch,
    hasNextPage,
    isFetchingNextPage,
    fetchNextPage,
  } = useChoresListPaginated(projectId, filterParams);
  // ── Inline Edit State ──
  const [editState, setEditState] = useState<Record<string, ChoreEditState>>({});
  const inlineUpdateMutation = useInlineUpdateChore(projectId);

  const isAnyDirty = useMemo(() => Object.values(editState).some((s) => s.isDirty), [editState]);

  useEffect(() => {
    onDirtyChange?.(isAnyDirty);
  }, [isAnyDirty, onDirtyChange]);

  const handleEditChange = useCallback((choreId: string, updates: Partial<ChoreInlineUpdate>) => {
    setEditState((prev) => {
      const existing = prev[choreId];
      if (!existing) return prev;
      const newCurrent = { ...existing.current, ...updates };
      const isDirty = Object.keys(newCurrent).some((key) => {
        const k = key as keyof ChoreInlineUpdate;
        const original = existing.original[k as keyof Chore];
        return newCurrent[k] !== undefined && newCurrent[k] !== original;
      });
      return { ...prev, [choreId]: { ...existing, current: newCurrent, isDirty } };
    });
  }, []);

  const handleEditStart = useCallback((chore: Chore) => {
    setEditState((prev) => ({
      ...prev,
      [chore.id]: { original: chore, current: {}, isDirty: false, fileSha: null },
    }));
  }, []);

  const handleEditDiscard = useCallback((choreId: string) => {
    setEditState((prev) => {
      const next = { ...prev };
      delete next[choreId];
      return next;
    });
  }, []);

  const handleEditSave = useCallback(
    async (choreId: string) => {
      const state = editState[choreId];
      if (!state?.isDirty) return;
      try {
        await inlineUpdateMutation.mutateAsync({ choreId, data: state.current });
        setEditState((prev) => {
          const next = { ...prev };
          delete next[choreId];
          return next;
        });
      } catch {
        // Error handled by mutation state
      }
    },
    [editState, inlineUpdateMutation]
  );

  const handleSaveAll = useCallback(async () => {
    const dirtyIds = Object.keys(editState).filter((id) => editState[id]?.isDirty);
    for (const id of dirtyIds) {
      await handleEditSave(id);
    }
  }, [editState, handleEditSave]);

  const handleResetFilters = useCallback(() => {
    setSearch('');
    setStatusFilter('all');
    setScheduleFilter('all');
    setSortMode('attention');
  }, []);

  const isRateLimited = isRateLimitApiError(error);
  const hasActiveFilters =
    statusFilter !== 'all' || scheduleFilter !== 'all' || deferredSearch.trim() !== '';

  return (
    <div className="celestial-fade-in flex min-w-0 flex-col gap-6">
      <ChoresSaveAllBar
        isVisible={isAnyDirty}
        isSaving={inlineUpdateMutation.isPending}
        onDiscardAll={() => setEditState({})}
        onSaveAll={handleSaveAll}
      />

      {isLoading && (
        <div className="flex flex-col items-center justify-center gap-3 py-12">
          <CelestialLoader size="md" label="Loading chores…" />
        </div>
      )}

      {error && !isLoading && (
        <div className="flex flex-col items-center gap-3 rounded-[1.4rem] border border-destructive/30 bg-destructive/5 p-6 text-center">
          <span className="text-sm font-medium text-destructive">
            {isRateLimited ? 'Rate limit reached' : 'Could not load chores'}
          </span>
          <p className="text-xs text-muted-foreground">
            {isRateLimited
              ? 'Too many requests. Please wait a moment and try again.'
              : `${error.message}. Check your connection and retry.`}
          </p>
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            Retry
          </Button>
        </div>
      )}

      {!isLoading &&
        !error &&
        !hasActiveFilters &&
        chores.length === 0 && (
          <div className="celestial-panel flex flex-col items-center gap-3 rounded-[1.5rem] border-2 border-dashed border-border bg-background/28 p-8 text-center">
            <ScrollText className="h-8 w-8 text-primary/80" aria-hidden="true" />
            <p className="text-lg font-medium text-foreground">No chores yet</p>
            <p className="max-w-md text-sm text-muted-foreground">
              Create a chore to set up recurring maintenance routines for your project.
            </p>
          </div>
        )}

      {!isLoading && !error && (chores.length > 0 || hasActiveFilters) && (
        <section
          id="chores-catalog"
          className="ritual-stage scroll-mt-6 rounded-[1.55rem] p-4 sm:rounded-[1.85rem] sm:p-6"
        >
          <ChoresToolbar
            search={search}
            onSearchChange={setSearch}
            statusFilter={statusFilter}
            onStatusFilterChange={setStatusFilter}
            scheduleFilter={scheduleFilter}
            onScheduleFilterChange={setScheduleFilter}
            sortMode={sortMode}
            onSortModeChange={setSortMode}
          />
          <ChoresGrid
            chores={chores}
            projectId={projectId}
            parentIssueCount={parentIssueCount}
            editState={editState}
            onEditStart={handleEditStart}
            onEditChange={handleEditChange}
            onEditSave={handleEditSave}
            onEditDiscard={handleEditDiscard}
            isSaving={inlineUpdateMutation.isPending}
            onResetFilters={handleResetFilters}
            hasNextPage={hasNextPage}
            isFetchingNextPage={isFetchingNextPage}
            fetchNextPage={fetchNextPage}
          />
        </section>
      )}
    </div>
  );
}
