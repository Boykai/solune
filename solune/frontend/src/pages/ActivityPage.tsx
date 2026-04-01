/**
 * ActivityPage — unified activity timeline with filter chips and infinite scroll.
 */

import { useState, useMemo, useCallback } from 'react';
import {
  GitBranch,
  ListChecks,
  Bot,
  Boxes,
  Wrench,
  Webhook,
  Trash2,
  ArrowRightLeft,
  Clock,
  ChevronDown,
  ChevronRight,
  Activity,
  Settings as SettingsIcon,
  Sparkles,
} from '@/lib/icons';
import { useActivityFeed } from '@/hooks/useActivityFeed';
import { useActivityStats } from '@/hooks/useActivityStats';
import { InfiniteScrollContainer } from '@/components/common/InfiniteScrollContainer';
import { useAuth } from '@/hooks/useAuth';
import { cn } from '@/lib/utils';
import type { ActivityEvent, ActivityStats } from '@/types';

// ── Event type → category mapping ──

export const EVENT_CATEGORIES = [
  { label: 'Pipeline', types: ['pipeline_run', 'pipeline_stage'], icon: GitBranch },
  { label: 'Execution', types: ['agent_execution'], icon: Sparkles },
  { label: 'Project', types: ['project', 'settings'], icon: SettingsIcon },
  { label: 'Chore', types: ['chore_trigger', 'chore_crud'], icon: ListChecks },
  { label: 'Agent', types: ['agent_crud'], icon: Bot },
  { label: 'App', types: ['app_crud'], icon: Boxes },
  { label: 'Tool', types: ['tool_crud'], icon: Wrench },
  { label: 'Webhook', types: ['webhook'], icon: Webhook },
  { label: 'Cleanup', types: ['cleanup'], icon: Trash2 },
  { label: 'Status', types: ['status_change'], icon: ArrowRightLeft },
] as const;

const EVENT_TYPE_ICON_MAP: Record<string, React.ComponentType<{ className?: string }>> = {
  pipeline_run: GitBranch,
  pipeline_stage: GitBranch,
  chore_trigger: ListChecks,
  chore_crud: ListChecks,
  agent_crud: Bot,
  agent_execution: Sparkles,
  cleanup: Trash2,
  app_crud: Boxes,
  tool_crud: Wrench,
  status_change: ArrowRightLeft,
  webhook: Webhook,
  project: SettingsIcon,
  settings: SettingsIcon,
};

type ActivityTimeBucket = 'Today' | 'Yesterday' | 'This Week' | 'Earlier';

const TIME_BUCKET_ORDER: ActivityTimeBucket[] = ['Today', 'Yesterday', 'This Week', 'Earlier'];

const ACTION_BADGE_STYLES: Record<string, string> = {
  created: 'border-emerald-500/20 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300',
  deleted: 'border-red-500/20 bg-red-500/10 text-red-700 dark:text-red-300',
  updated: 'border-blue-500/20 bg-blue-500/10 text-blue-700 dark:text-blue-300',
  launched: 'border-fuchsia-500/20 bg-fuchsia-500/10 text-fuchsia-700 dark:text-fuchsia-300',
  triggered: 'border-fuchsia-500/20 bg-fuchsia-500/10 text-fuchsia-700 dark:text-fuchsia-300',
  completed: 'border-fuchsia-500/20 bg-fuchsia-500/10 text-fuchsia-700 dark:text-fuchsia-300',
};

function parseActivityDate(isoDate: string): Date {
  return new Date(isoDate.endsWith('Z') ? isoDate : `${isoDate}Z`);
}

function toTitleCase(value: string): string {
  return value
    .split(/[_\s]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

function formatRelativeTime(isoDate: string): string {
  const now = Date.now();
  const then = parseActivityDate(isoDate).getTime();
  const diff = now - then;

  if (diff < 60_000) return 'just now';
  if (diff < 3_600_000) {
    const mins = Math.floor(diff / 60_000);
    return `${mins}m ago`;
  }
  if (diff < 86_400_000) {
    const hrs = Math.floor(diff / 3_600_000);
    return `${hrs}h ago`;
  }
  const days = Math.floor(diff / 86_400_000);
  if (days < 30) return `${days}d ago`;
  return new Date(then).toLocaleDateString();
}

export function getTimeBucketLabel(
  isoDate: string,
  now: Date = new Date()
): ActivityTimeBucket {
  const eventDate = parseActivityDate(isoDate);
  const startOfToday = new Date(now);
  startOfToday.setHours(0, 0, 0, 0);

  const startOfYesterday = new Date(startOfToday);
  startOfYesterday.setDate(startOfYesterday.getDate() - 1);

  const startOfThisWeekWindow = new Date(startOfToday);
  startOfThisWeekWindow.setDate(startOfThisWeekWindow.getDate() - 7);

  if (eventDate >= startOfToday) return 'Today';
  if (eventDate >= startOfYesterday) return 'Yesterday';
  if (eventDate >= startOfThisWeekWindow) return 'This Week';
  return 'Earlier';
}

export function groupEventsByTimeBucket(
  events: ActivityEvent[],
  now: Date = new Date()
): Array<{ label: ActivityTimeBucket; events: ActivityEvent[] }> {
  const groups = new Map<ActivityTimeBucket, ActivityEvent[]>(
    TIME_BUCKET_ORDER.map((label) => [label, [] as ActivityEvent[]])
  );

  events.forEach((event) => {
    const label = getTimeBucketLabel(event.created_at, now);
    groups.get(label)?.push(event);
  });

  return TIME_BUCKET_ORDER.map((label) => ({ label, events: groups.get(label) ?? [] })).filter(
    (group) => group.events.length > 0
  );
}

function getActionBadgeClass(action: string): string {
  return (
    ACTION_BADGE_STYLES[action] ??
    'border-border/70 bg-muted/60 text-muted-foreground'
  );
}

function formatMostCommon(stats: ActivityStats | null): string {
  if (!stats || Object.keys(stats.by_type).length === 0) return 'No activity';
  const [eventType] =
    Object.entries(stats.by_type).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))[0] ?? [];
  return eventType ? toTitleCase(eventType) : 'No activity';
}

function formatLastActivity(lastEventAt: string | null, isLoading: boolean): string {
  if (isLoading) return 'Loading…';
  if (!lastEventAt) return 'No activity';
  return formatRelativeTime(lastEventAt);
}

function DetailView({ detail }: { detail: Record<string, unknown> }) {
  return (
    <div className="mt-2 rounded-lg bg-muted/40 px-3 py-2 text-xs">
      {Object.entries(detail).map(([key, value]) => (
        <div key={key} className="flex gap-2 py-0.5">
          <span className="font-medium text-muted-foreground">{key}:</span>
          <span className="text-foreground">
            {typeof value === 'object' ? JSON.stringify(value) : String(value)}
          </span>
        </div>
      ))}
    </div>
  );
}

export function ActivityPage() {
  const { user } = useAuth();
  const projectId = user?.selected_project_id ?? '';

  const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  const eventTypes = useMemo(() => {
    if (selectedCategories.length === 0) return undefined;
    return EVENT_CATEGORIES.filter((c) => selectedCategories.includes(c.label)).flatMap(
      (c) => c.types,
    );
  }, [selectedCategories]);

  const {
    allItems: events,
    hasNextPage,
    isFetchingNextPage,
    fetchNextPage,
    isLoading,
    isError,
  } = useActivityFeed(projectId, eventTypes);
  const { stats, isLoading: isStatsLoading } = useActivityStats(projectId);

  const groupedEvents = useMemo(() => groupEventsByTimeBucket(events), [events]);
  const statsCards = useMemo(
    () => [
      { label: 'Total Events', value: String(stats?.total_count ?? 0) },
      { label: 'Today', value: String(stats?.today_count ?? 0) },
      { label: 'Most Common', value: formatMostCommon(stats) },
      {
        label: 'Last Activity',
        value: formatLastActivity(stats?.last_event_at ?? null, isStatsLoading),
      },
    ],
    [isStatsLoading, stats]
  );

  const toggleCategory = useCallback((label: string) => {
    setSelectedCategories((prev) =>
      prev.includes(label) ? prev.filter((c) => c !== label) : [...prev, label],
    );
  }, []);

  const clearFilters = useCallback(() => setSelectedCategories([]), []);

  const toggleExpanded = useCallback((id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  return (
    <div className="mx-auto max-w-4xl px-4 py-6 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="mb-6 flex items-center gap-3">
        <Activity className="h-6 w-6 text-primary" />
        <h1 className="text-2xl font-display font-semibold tracking-tight">Activity</h1>
      </div>

      <div className="mb-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {statsCards.map((stat) => (
          <section key={stat.label} className="moonwell rounded-[1.3rem] px-4 py-3">
            <p className="text-[10px] uppercase tracking-[0.22em] text-muted-foreground/80">
              {stat.label}
            </p>
            <p className="mt-2 break-words text-xl font-semibold leading-tight text-foreground">
              {stat.value}
            </p>
          </section>
        ))}
      </div>

      {/* Filter chips */}
      <div className="mb-4 flex flex-wrap items-center gap-2">
        {EVENT_CATEGORIES.map((cat) => {
          const Icon = cat.icon;
          const active = selectedCategories.includes(cat.label);
          return (
            <button
              key={cat.label}
              type="button"
              onClick={() => toggleCategory(cat.label)}
              className={cn(
                'inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition-colors',
                active
                  ? 'border-primary bg-primary/10 text-primary'
                  : 'border-border bg-background text-muted-foreground hover:border-primary/50 hover:text-foreground',
              )}
            >
              <Icon className="h-3.5 w-3.5" />
              {cat.label}
            </button>
          );
        })}
        {selectedCategories.length > 0 && (
          <button
            type="button"
            onClick={clearFilters}
            className="text-xs text-muted-foreground hover:text-foreground"
          >
            Clear all
          </button>
        )}
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="flex items-center justify-center py-20">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary/30 border-t-primary" />
          <span className="ml-3 text-sm text-muted-foreground">Loading activity…</span>
        </div>
      )}

      {/* Empty state */}
      {!isLoading && events.length === 0 && (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border/60 py-20">
          <Clock className="mb-3 h-10 w-10 text-muted-foreground/40" />
          <p className="text-sm font-medium text-muted-foreground">
            {selectedCategories.length > 0
              ? `No ${selectedCategories.join(', ').toLowerCase()} events found`
              : 'No activity recorded yet'}
          </p>
          <p className="mt-1 text-xs text-muted-foreground/70">
            Events will appear here as you use the system.
          </p>
        </div>
      )}

      {/* Event timeline */}
      {!isLoading && events.length > 0 && (
        <InfiniteScrollContainer
          hasNextPage={hasNextPage}
          isFetchingNextPage={isFetchingNextPage}
          fetchNextPage={fetchNextPage}
          isError={isError}
        >
          <div className="space-y-6">
            {groupedEvents.map((group) => (
              <section key={group.label}>
                <div className="sticky top-0 z-10 mb-2 bg-background/95 px-3 py-2 text-xs font-semibold uppercase tracking-[0.22em] text-muted-foreground backdrop-blur-sm">
                  {group.label}
                </div>
                <div className="space-y-1">
                  {group.events.map((event) => {
                    const Icon = EVENT_TYPE_ICON_MAP[event.event_type] ?? Clock;
                    const expanded = expandedIds.has(event.id);
                    const hasDetail = event.detail && Object.keys(event.detail).length > 0;

                    return (
                      <div key={event.id} className="group">
                        <button
                          type="button"
                          onClick={() => hasDetail && toggleExpanded(event.id)}
                          className={cn(
                            'flex w-full items-start gap-3 rounded-lg px-3 py-2.5 text-left transition-colors',
                            hasDetail ? 'cursor-pointer hover:bg-muted/50' : 'cursor-default'
                          )}
                        >
                          <Icon className="mt-0.5 h-4 w-4 shrink-0 text-primary/70" />
                          <div className="min-w-0 flex-1">
                            <div className="flex flex-wrap items-center gap-2">
                              <p className="text-sm text-foreground">{event.summary}</p>
                              <span
                                className={cn(
                                  'rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.14em]',
                                  getActionBadgeClass(event.action)
                                )}
                              >
                                {toTitleCase(event.action)}
                              </span>
                              <span className="rounded-full border border-border/70 bg-background px-2 py-0.5 text-[10px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
                                {toTitleCase(event.entity_type)}
                              </span>
                            </div>
                            <div className="mt-0.5 flex items-center gap-2 text-xs text-muted-foreground">
                              <span>{formatRelativeTime(event.created_at)}</span>
                              <span>·</span>
                              <span>{event.actor}</span>
                            </div>
                          </div>
                          {hasDetail &&
                            (expanded ? (
                              <ChevronDown className="mt-1 h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                            ) : (
                              <ChevronRight className="mt-1 h-3.5 w-3.5 shrink-0 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
                            ))}
                        </button>
                        {expanded && event.detail && <DetailView detail={event.detail} />}
                      </div>
                    );
                  })}
                </div>
              </section>
            ))}
          </div>

          {/* End of activity indicator */}
          {!hasNextPage && events.length > 0 && (
            <div className="flex items-center justify-center gap-2 py-6 text-xs text-muted-foreground">
              <div className="h-px flex-1 bg-border/50" />
              <span>End of activity log</span>
              <div className="h-px flex-1 bg-border/50" />
            </div>
          )}
        </InfiniteScrollContainer>
      )}
    </div>
  );
}
