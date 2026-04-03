/**
 * BoardColumnSkeleton — skeleton placeholder matching BoardColumn dimensions.
 */

import { Skeleton } from '@/components/ui/skeleton';
import { IssueCardSkeleton } from './IssueCardSkeleton';

export function BoardColumnSkeleton() {
  return (
    <div
      className="flex h-[44rem] max-h-[44rem] min-h-[28rem] min-w-0 shrink-0 flex-col overflow-hidden rounded-[1.4rem] border border-border/70 shadow-sm md:h-[72rem] md:max-h-[72rem] md:min-h-[44rem] xl:h-[95rem] xl:max-h-[95rem]"
      role="status"
      aria-busy="true"
    >
      <span className="sr-only">Loading column…</span>
      {/* Header */}
      <div className="flex items-center gap-2 border-b border-border/70 p-4">
        <Skeleton className="h-2.5 w-2.5 rounded-full" />
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-5 w-8 rounded-full" />
      </div>
      {/* Cards */}
      <div className="flex flex-col gap-3 p-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <IssueCardSkeleton key={i} />
        ))}
      </div>
    </div>
  );
}
