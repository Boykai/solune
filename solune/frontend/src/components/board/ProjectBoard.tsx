/**
 * ProjectBoard component - horizontal columns container for the Kanban board.
 * Uses CSS grid matching AgentConfigRow for aligned columns.
 * Supports optional grouping within columns via getGroups callback.
 * Wraps columns with DndContext + DragOverlay for card drag-and-drop.
 * Phase 8: Supports board projection for lazy-loading large boards.
 */

import { useMemo, useState, useRef, useEffect, useCallback } from 'react';
import {
  DndContext,
  DragOverlay,
  closestCorners,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import type { BoardDataResponse, BoardItem, AvailableAgent } from '@/types';
import type { BoardGroup } from '@/hooks/useBoardControls';
import { useBoardDragDrop } from '@/hooks/useBoardDragDrop';
import { useBoardProjection, type BoardProjectionConfig } from '@/hooks/useBoardProjection';
import { useMediaQuery } from '@/hooks/useMediaQuery';
import { BoardColumn } from './BoardColumn';
import { BoardDragOverlay } from './BoardDragOverlay';

interface ProjectBoardProps {
  boardData: BoardDataResponse;
  onCardClick: (item: BoardItem) => void;
  availableAgents?: AvailableAgent[];
  getGroups?: (items: BoardItem[]) => BoardGroup[] | null;
  onStatusUpdate?: (itemId: string, newStatus: string) => void | Promise<void>;
  /** Optional board projection config for lazy loading. */
  projectionConfig?: BoardProjectionConfig;
}

export function ProjectBoard({
  boardData,
  onCardClick,
  availableAgents,
  getGroups,
  onStatusUpdate,
  projectionConfig,
}: ProjectBoardProps) {
  const columnCount = Math.max(boardData.columns.length, 1);
  const isMobile = useMediaQuery('(max-width: 767px)');
  const colMinWidth = isMobile ? '14rem' : '16rem';
  const gridStyle = useMemo(
    () => ({ gridTemplateColumns: `repeat(${columnCount}, minmax(min(${colMinWidth}, 85vw), 1fr))` }),
    [columnCount, colMinWidth]
  );

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
  );

  const { activeCard, handlers } = useBoardDragDrop(boardData, onStatusUpdate);

  // T027: Scroll affordance — gradient fade on the trailing edge
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [showScrollFade, setShowScrollFade] = useState(false);

  const checkScrollFade = useCallback(() => {
    const el = scrollContainerRef.current;
    if (!el) return;
    const hasOverflow = el.scrollWidth > el.clientWidth;
    const atEnd = el.scrollLeft + el.clientWidth >= el.scrollWidth - 2;
    setShowScrollFade(hasOverflow && !atEnd);
  }, []);

  useEffect(() => {
    const el = scrollContainerRef.current;
    if (!el) return;
    // Defer initial check to avoid synchronous setState in effect body
    const rafId = requestAnimationFrame(checkScrollFade);
    el.addEventListener('scroll', checkScrollFade, { passive: true });
    window.addEventListener('resize', checkScrollFade);
    return () => {
      cancelAnimationFrame(rafId);
      el.removeEventListener('scroll', checkScrollFade);
      window.removeEventListener('resize', checkScrollFade);
    };
  }, [checkScrollFade]);

  // Board projection for lazy loading large boards
  const {
    columnProjections,
    observerRef,
  } = useBoardProjection(boardData, projectionConfig);

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCorners}
      onDragStart={handlers.onDragStart}
      onDragOver={handlers.onDragOver}
      onDragEnd={handlers.onDragEnd}
      onDragCancel={handlers.onDragCancel}
    >
      <div className="relative flex h-full w-full flex-1">
        <div ref={scrollContainerRef} className="celestial-fade-in flex h-full w-full flex-1 snap-x snap-mandatory overflow-x-auto overflow-y-visible pb-6 md:snap-none" role="region" aria-label="Project board">
          <div
            className="grid min-h-full min-w-full items-stretch gap-5 pb-2"
            style={gridStyle}
          >
          {boardData.columns.map((column) => {
            const projection = columnProjections.get(column.status.name);
            const projectedColumn = projection
              ? {
                  ...column,
                  items: column.items.slice(
                    projection.renderedRange.start,
                    projection.renderedRange.end,
                  ),
                }
              : column;

            return (
              <BoardColumn
                key={column.status.option_id}
                column={projectedColumn}
                onCardClick={onCardClick}
                availableAgents={availableAgents}
                getGroups={getGroups}
                hasMore={projection?.hasMore}
                scrollSentinelRef={observerRef(column.status.name)}
              />
            );
          })}
          </div>
        </div>
        {showScrollFade && (
          <div
            className="pointer-events-none absolute right-0 top-0 h-full w-8 bg-gradient-to-l from-background/80 to-transparent"
            aria-hidden="true"
          />
        )}
      </div>
      <DragOverlay>
        {activeCard ? <BoardDragOverlay item={activeCard} /> : null}
      </DragOverlay>
    </DndContext>
  );
}
