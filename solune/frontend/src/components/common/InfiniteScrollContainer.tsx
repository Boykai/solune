/**
 * InfiniteScrollContainer — reusable scroll sentinel component.
 *
 * Uses IntersectionObserver to detect when the user has scrolled near the
 * bottom of a list and automatically triggers the next page fetch.
 */

import { useEffect, useRef, type ReactNode } from 'react';
import { Skeleton } from '@/components/ui/skeleton';

interface InfiniteScrollContainerProps {
  children: ReactNode;
  hasNextPage: boolean;
  isFetchingNextPage: boolean;
  fetchNextPage: () => void;
  isError?: boolean;
  onRetry?: () => void;
  className?: string;
  /** Number of skeleton placeholder rows to show while loading the next page. */
  skeletonCount?: number;
}

export function InfiniteScrollContainer({
  children,
  hasNextPage,
  isFetchingNextPage,
  fetchNextPage,
  isError = false,
  onRetry,
  className,
  skeletonCount = 3,
}: InfiniteScrollContainerProps) {
  const sentinelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const sentinel = sentinelRef.current;
    if (!sentinel || !hasNextPage || isFetchingNextPage || isError) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const entry = entries[0];
        if (entry?.isIntersecting && hasNextPage && !isFetchingNextPage && !isError) {
          fetchNextPage();
        }
      },
      { rootMargin: '200px' },
    );

    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [hasNextPage, isFetchingNextPage, isError, fetchNextPage]);

  return (
    <div className={className}>
      {children}

      {/* Sentinel element for IntersectionObserver */}
      {hasNextPage && !isError && (
        <div ref={sentinelRef} aria-hidden="true" className="h-1" />
      )}

      {/* Loading indicator with skeleton placeholders */}
      {isFetchingNextPage && (
        <div className="space-y-3 py-4" aria-live="polite" aria-busy="true">
          {Array.from({ length: skeletonCount }).map((_, i) => (
            <div key={i} className="rounded-xl border border-border/60 p-4">
              <Skeleton variant="shimmer" className="mb-2 h-4 w-3/5" />
              <Skeleton variant="shimmer" className="h-3 w-2/5" />
            </div>
          ))}
          <div className="flex items-center justify-center">
            <div className="h-5 w-5 animate-spin rounded-full border-2 border-primary/30 border-t-primary" />
            <span className="ml-2 text-sm text-muted-foreground">Loading more…</span>
          </div>
        </div>
      )}

      {/* Error state with retry */}
      {isError && !isFetchingNextPage && (
        <div className="flex items-center justify-center gap-2 py-4" aria-live="polite">
          <span className="text-sm text-destructive">Failed to load more items.</span>
          {onRetry && (
            <button
              type="button"
              onClick={onRetry}
              className="text-sm font-medium text-primary hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
            >
              Retry
            </button>
          )}
        </div>
      )}
    </div>
  );
}
