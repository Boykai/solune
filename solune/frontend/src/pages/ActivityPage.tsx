/**
 * ActivityPage — unified activity timeline with filter chips and infinite scroll.
 */

import { useCallback, useMemo, useState, type ComponentType } from 'react';
import {
  Activity,
  ArrowRightLeft,
  Bot,
  Boxes,
  ChevronDown,
  ChevronRight,
  Clock,
  GitBranch,
  Layers,
  ListChecks,
  Settings,
  Sparkles,
  Trash2,
  Webhook,
  Wrench,
} from '@/lib/icons';
import { InfiniteScrollContainer } from '@/components/common/InfiniteScrollContainer';
import { useAuth } from '@/hooks/useAuth';
import { useActivityFeed } from '@/hooks/useActivityFeed';
import { useActivityStats } from '@/hooks/useActivityStats';
import { cn } from '@/lib/utils';
import type { ActivityEvent } from '@/types';

interface EventCategory {
  label: string;
  types: string[];
  icon: ComponentType<{ className?: string }>;
}

interface ActivityGroup {
  label: 'Today' | 'Yesterday' | 'This Week' | 'Earlier';
  items: ActivityEvent[];
}

const DAY_IN_MS = 86_400_000;
const BUCKET_ORDER: ActivityGroup['label'][] = ['Today', 'Yesterday', 'This Week', 'Earlier'];

export const EVENT_CATEGORIES: EventCategory[] = [
  { label: 'Pipeline', types: ['pipeline_run', 'pipeline_stage'], icon: GitBranch },
  { label: 'Chore', types: ['chore_trigger', 'chore_crud'], icon: ListChecks },
  { label: 'Agent', types: ['agent_crud', 'agent_execution'], icon: Bot },
  { label: 'Execution', types: ['agent_execution'], icon: Sparkles },
  { label: 'Project', types: ['project', 'settings'], icon: Layers },
  { label: 'App', types: ['app_crud'], icon: Boxes },
  { label: 'Tool', types: ['tool_crud'], icon: Wrench },
  { label: 'Webhook', types: ['webhook'], icon: Webhook },
  { label: 'Cleanup', types: ['cleanup'], icon: Trash2 },
  { label: 'Status', types: ['status_change'], icon: ArrowRightLeft },
];

const EVENT_TYPE_ICON_MAP: Record<string, ComponentType<{ className?: string }>> = {
  pipeline_run: GitBranch,
  pipeline_stage: GitBranch,
  chore_trigger: ListChecks,
  chore_crud: ListChecks,
  agent_crud: Bot,
  agent_execution: Sparkles,
  project: Layers,
  settings: Settings,
  cleanup: Trash2,
  app_crud: Boxes,
  tool_crud: Wrench,
  status_change: ArrowRightLeft,
  webhook: Webhook,
};

function toEventDate(isoDate: string): Date {
  return new Date(isoDate.endsWith('Z') ? isoDate : `${isoDate}Z`);
}

function getUtcDayStart(date: Date): number {
  return Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate());
}

function humanizeToken(value: string): string {
  return value
    .split(/[_\-.]/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

function formatRelativeTime(isoDate: string): string {
  const now = Date.now();
  const then = toEventDate(isoDate).getTime();
  const diff = now - then;

  if (diff < 60_000) return 'just now';
  if (diff < 3_600_000) {
    const mins = Math.floor(diff / 60_000);
    return `${mins}m ago`;
  }
  if (diff < DAY_IN_MS) {
    const hrs = Math.floor(diff / 3_600_000);
    return `${hrs}h ago`;
  }
  const days = Math.floor(diff / DAY_IN_MS);
  if (days < 30) return `${days}d ago`;
  return toEventDate(isoDate).toLocaleDateString();
}

function getBucketLabel(isoDate: string, now: Date): ActivityGroup['label'] {
  const dayDiff = Math.floor((getUtcDayStart(now) - getUtcDayStart(toEventDate(isoDate))) / DAY_IN_MS);

  if (dayDiff <= 0) return 'Today';
  if (dayDiff === 1) return 'Yesterday';
  if (dayDiff < 7) return 'This Week';
  return 'Earlier';
}

export function bucketActivityEvents(events: ActivityEvent[], now = new Date(Date.now())): ActivityGroup[] {
  const grouped = new Map<ActivityGroup['label'], ActivityEvent[]>();

  for (const event of events) {
    const label = getBucketLabel(event.created_at, now);
    const items = grouped.get(label) ?? [];
    items.push(event);
    grouped.set(label, items);
  }

  return BUCKET_ORDER.filter((label) => grouped.has(label)).map((label) => ({
    label,
    items: grouped.get(label) ?? [],
  }));
}

function getActionBadgeClasses(action: string): string {
  switch (action) {
    case 'created':
      return 'border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300';
    case 'deleted':
      return 'border-rose-500/30 bg-rose-500/10 text-rose-700 dark:text-rose-300';
    case 'updated':
      return 'border-sky-500/30 bg-sky-500/10 text-sky-700 dark:text-sky-300';
    case 'started':
    case 'launched':
    case 'triggered':
    case 'completed':
      return 'border-violet-500/30 bg-violet-500/10 text-violet-700 dark:text-violet-300';
    default:
      return 'border-border/60 bg-muted/60 text-muted-foreground';
  }
}

function formatMostCommonEvent(byType: Record<string, number>): string {
  const [eventType, count] =
    Object.entries(byType).sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0]))[0] ??
    [];

  if (!eventType || typeof count !== 'number') {
    return 'No activity yet';
  }

  return `${humanizeToken(eventType)} (${count})`;
}

function isUrl(value: unknown): value is string {
  if (typeof value !== 'string') return false;
  return value.startsWith('https://') || value.startsWith('http://');
}

function isGitHubNumber(key: string, value: unknown): boolean {
  return (
    typeof value === 'number' &&
    (key === 'issue_number' || key === 'pr_number' || key === 'tracking_issue_number')
  );
}

function DetailValue({ detailKey, value, urlHint }: { detailKey: string; value: unknown; urlHint?: string }) {
  if (isUrl(value)) {
    return (
      <a
        href={value}
        target="_blank"
        rel="noopener noreferrer"
        className="text-primary hover:underline"
      >
        {value}
      </a>
    );
  }
  if (isGitHubNumber(detailKey, value) && urlHint) {
    return (
      <a
        href={urlHint}
        target="_blank"
        rel="noopener noreferrer"
        className="text-primary hover:underline"
      >
        #{String(value)}
      </a>
    );
  }
  if (isGitHubNumber(detailKey, value)) {
    return <span className="text-primary font-medium">#{String(value)}</span>;
  }
  return <span>{typeof value === 'object' ? JSON.stringify(value) : String(value)}</span>;
}

function DetailView({ detail }: { detail: Record<string, unknown> }) {
  // Build URL hints: if detail has both issue_number and issue_url, link the number
  const urlHints: Record<string, string> = {};
  if (isUrl(detail.issue_url) && detail.issue_number != null) {
    urlHints.issue_number = detail.issue_url as string;
  }
  if (isUrl(detail.pr_url) && detail.pr_number != null) {
    urlHints.pr_number = detail.pr_url as string;
  }
  // For standalone numbers without a paired URL, try to construct from issue_url pattern
  if (!urlHints.pr_number && detail.pr_number != null && isUrl(detail.issue_url)) {
    const base = (detail.issue_url as string).replace(/\/issues\/\d+$/, '');
    urlHints.pr_number = `${base}/pull/${detail.pr_number}`;
  }
  if (!urlHints.issue_number && detail.issue_number != null && isUrl(detail.pr_url)) {
    const base = (detail.pr_url as string).replace(/\/pull\/\d+$/, '');
    urlHints.issue_number = `${base}/issues/${detail.issue_number}`;
  }

  return (
    <div className="mt-2 rounded-lg bg-muted/40 px-3 py-2 text-xs">
      {Object.entries(detail).map(([key, value]) => (
        <div key={key} className="flex gap-2 py-0.5">
          <span className="font-medium text-muted-foreground">{key}:</span>
          <span className="text-foreground">
            <DetailValue detailKey={key} value={value} urlHint={urlHints[key]} />
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
    return EVENT_CATEGORIES.filter((category) => selectedCategories.includes(category.label)).flatMap(
      (category) => category.types,
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
  const { data: stats, isLoading: statsLoading } = useActivityStats(projectId);

  const groupedEvents = useMemo(() => bucketActivityEvents(events), [events]);
  const statCards = useMemo(
    () => [
      { label: 'Total Events', value: String(stats?.total_count ?? 0) },
      { label: 'Today', value: String(stats?.today_count ?? 0) },
      { label: 'Most Common', value: formatMostCommonEvent(stats?.by_type ?? {}) },
      {
        label: 'Last Activity',
        value: stats?.last_event_at ? formatRelativeTime(stats.last_event_at) : 'No activity yet',
      },
    ],
    [stats],
  );

  const toggleCategory = useCallback((label: string) => {
    setSelectedCategories((previous) =>
      previous.includes(label) ? previous.filter((category) => category !== label) : [...previous, label],
    );
  }, []);

  const clearFilters = useCallback(() => setSelectedCategories([]), []);

  const toggleExpanded = useCallback((id: string) => {
    setExpandedIds((previous) => {
      const next = new Set(previous);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  return (
    <div className="mx-auto max-w-5xl px-4 py-6 sm:px-6 lg:px-8">
      <div className="mb-6 flex items-center gap-3">
        <Activity className="h-6 w-6 text-primary" />
        <h1 className="text-2xl font-display font-semibold tracking-tight">Activity</h1>
      </div>

      <div className="mb-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {statCards.map((stat) => (
          <div
            key={stat.label}
            className="moonwell inline-flex min-h-[6.5rem] flex-col rounded-[1.2rem] px-4 py-3 sm:rounded-[1.3rem]"
          >
            <p className="text-[10px] uppercase tracking-[0.22em] text-muted-foreground/80">
              {stat.label}
            </p>
            {statsLoading ? (
              <div className="mt-2 h-7 w-16 animate-pulse rounded bg-muted/60" />
            ) : (
              <p className="mt-2 break-words text-xl font-semibold leading-tight text-foreground">
                {stat.value}
              </p>
            )}
          </div>
        ))}
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-2">
        {EVENT_CATEGORIES.map((category) => {
          const Icon = category.icon;
          const active = selectedCategories.includes(category.label);
          return (
            <button
              key={category.label}
              type="button"
              onClick={() => toggleCategory(category.label)}
              className={cn(
                'inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition-colors',
                active
                  ? 'border-primary bg-primary/10 text-primary'
                  : 'border-border bg-background text-muted-foreground hover:border-primary/50 hover:text-foreground',
              )}
            >
              <Icon className="h-3.5 w-3.5" />
              {category.label}
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

      {isLoading && (
        <div className="flex items-center justify-center py-20">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary/30 border-t-primary" />
          <span className="ml-3 text-sm text-muted-foreground">Loading activity…</span>
        </div>
      )}

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

      {!isLoading && events.length > 0 && (
        <InfiniteScrollContainer
          hasNextPage={hasNextPage}
          isFetchingNextPage={isFetchingNextPage}
          fetchNextPage={fetchNextPage}
          isError={isError}
        >
          <div className="space-y-6">
            {groupedEvents.map((group) => (
              <section key={group.label} aria-label={group.label}>
                <div className="sticky top-0 z-10 mb-2 bg-background/95 py-2 backdrop-blur">
                  <p className="text-xs font-semibold uppercase tracking-[0.24em] text-muted-foreground">
                    {group.label}
                  </p>
                </div>

                <div className="space-y-1">
                  {group.items.map((event) => {
                    const Icon = EVENT_TYPE_ICON_MAP[event.event_type] ?? Clock;
                    const expanded = expandedIds.has(event.id);
                    const hasDetail = !!event.detail && Object.keys(event.detail).length > 0;

                    return (
                      <div key={event.id} className="group">
                        <button
                          type="button"
                          onClick={() => hasDetail && toggleExpanded(event.id)}
                          className={cn(
                            'flex w-full items-start gap-3 rounded-lg px-3 py-2.5 text-left transition-colors',
                            hasDetail ? 'cursor-pointer hover:bg-muted/50' : 'cursor-default',
                          )}
                        >
                          <Icon className="mt-0.5 h-4 w-4 shrink-0 text-primary/70" />
                          <div className="min-w-0 flex-1">
                            <div className="flex flex-wrap items-center gap-2">
                              <p className="text-sm text-foreground">{event.summary}</p>
                              <span
                                className={cn(
                                  'rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.18em]',
                                  getActionBadgeClasses(event.action),
                                )}
                              >
                                {humanizeToken(event.action)}
                              </span>
                              <span className="rounded-full border border-border/60 bg-muted/40 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                                {humanizeToken(event.entity_type)}
                              </span>
                            </div>
                            <div className="mt-0.5 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
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
