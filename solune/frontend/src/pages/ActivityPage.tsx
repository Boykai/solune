/**
 * ActivityPage — unified activity timeline with stats header, filter chips,
 * time-bucketed grouping, status badges, entity pills, and infinite scroll.
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
  Kanban,
  Settings,
  Zap,
  BarChart3,
  TrendingUp,
} from '@/lib/icons';
import { useActivityFeed } from '@/hooks/useActivityFeed';
import { useActivityStats } from '@/hooks/useActivityStats';
import { InfiniteScrollContainer } from '@/components/common/InfiniteScrollContainer';
import { useAuth } from '@/hooks/useAuth';
import { cn } from '@/lib/utils';
import type { ActivityEvent } from '@/types';

// ── Event type → category mapping ──

const EVENT_CATEGORIES = [
  { label: 'Pipeline', types: ['pipeline_run', 'pipeline_stage'], icon: GitBranch },
  { label: 'Chore', types: ['chore_trigger', 'chore_crud'], icon: ListChecks },
  { label: 'Agent', types: ['agent_crud', 'agent_execution'], icon: Bot },
  { label: 'App', types: ['app_crud'], icon: Boxes },
  { label: 'Tool', types: ['tool_crud'], icon: Wrench },
  { label: 'Webhook', types: ['webhook'], icon: Webhook },
  { label: 'Project', types: ['project', 'settings'], icon: Kanban },
  { label: 'Status', types: ['status_change'], icon: ArrowRightLeft },
  { label: 'Cleanup', types: ['cleanup'], icon: Trash2 },
] as const;

const EVENT_TYPE_ICON_MAP: Record<string, React.ComponentType<{ className?: string }>> = {
  pipeline_run: GitBranch,
  pipeline_stage: GitBranch,
  chore_trigger: ListChecks,
  chore_crud: ListChecks,
  agent_crud: Bot,
  agent_execution: Zap,
  cleanup: Trash2,
  app_crud: Boxes,
  tool_crud: Wrench,
  status_change: ArrowRightLeft,
  webhook: Webhook,
  project: Kanban,
  settings: Settings,
};

// ── Action → badge color mapping ──

const ACTION_BADGE_COLORS: Record<string, string> = {
  created: 'bg-emerald-500/10 text-emerald-600 border-emerald-500/20',
  deleted: 'bg-red-500/10 text-red-600 border-red-500/20',
  updated: 'bg-blue-500/10 text-blue-600 border-blue-500/20',
  started: 'bg-violet-500/10 text-violet-600 border-violet-500/20',
  launched: 'bg-violet-500/10 text-violet-600 border-violet-500/20',
  triggered: 'bg-violet-500/10 text-violet-600 border-violet-500/20',
  completed: 'bg-emerald-500/10 text-emerald-600 border-emerald-500/20',
  cancelled: 'bg-amber-500/10 text-amber-600 border-amber-500/20',
  failed: 'bg-red-500/10 text-red-600 border-red-500/20',
  pr_merged: 'bg-violet-500/10 text-violet-600 border-violet-500/20',
  copilot_pr_ready: 'bg-blue-500/10 text-blue-600 border-blue-500/20',
  selected: 'bg-blue-500/10 text-blue-600 border-blue-500/20',
  user_updated: 'bg-blue-500/10 text-blue-600 border-blue-500/20',
  global_updated: 'bg-amber-500/10 text-amber-600 border-amber-500/20',
  project_updated: 'bg-blue-500/10 text-blue-600 border-blue-500/20',
};

// ── Entity type → pill color mapping ──

const ENTITY_PILL_COLORS: Record<string, string> = {
  pipeline: 'bg-indigo-500/10 text-indigo-600',
  agent: 'bg-violet-500/10 text-violet-600',
  tool: 'bg-amber-500/10 text-amber-600',
  app: 'bg-cyan-500/10 text-cyan-600',
  chore: 'bg-teal-500/10 text-teal-600',
  issue: 'bg-gray-500/10 text-gray-600',
  project: 'bg-blue-500/10 text-blue-600',
  user: 'bg-pink-500/10 text-pink-600',
  global: 'bg-amber-500/10 text-amber-600',
};

// ── Time bucketing ──

function getTimeBucket(isoDate: string): string {
  const now = new Date();
  const then = new Date(isoDate + (isoDate.endsWith('Z') ? '' : 'Z'));

  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterdayStart = new Date(todayStart.getTime() - 86_400_000);
  const weekStart = new Date(todayStart.getTime() - 6 * 86_400_000);

  if (then >= todayStart) return 'Today';
  if (then >= yesterdayStart) return 'Yesterday';
  if (then >= weekStart) return 'This Week';
  return 'Earlier';
}

function formatRelativeTime(isoDate: string): string {
  const now = Date.now();
  const then = new Date(isoDate + (isoDate.endsWith('Z') ? '' : 'Z')).getTime();
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

// ── Sub-components ──

function ActionBadge({ action }: { action: string }) {
  const colors = ACTION_BADGE_COLORS[action] ?? 'bg-muted text-muted-foreground border-border';
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border px-1.5 py-0.5 text-[10px] font-medium leading-none',
        colors,
      )}
    >
      {action.replace(/_/g, ' ')}
    </span>
  );
}

function EntityPill({ entityType, entityId }: { entityType: string; entityId: string }) {
  if (!entityId) return null;
  const colors = ENTITY_PILL_COLORS[entityType] ?? 'bg-muted text-muted-foreground';
  return (
    <span className={cn('inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-medium leading-none', colors)}>
      {entityType}:{entityId.length > 20 ? entityId.slice(0, 20) + '…' : entityId}
    </span>
  );
}

function StatCard({
  label,
  value,
  icon: Icon,
  loading,
}: {
  label: string;
  value: string | number;
  icon: React.ComponentType<{ className?: string }>;
  loading?: boolean;
}) {
  return (
    <div className="flex items-center gap-3 rounded-lg border border-border/60 bg-card px-4 py-3">
      <Icon className="h-5 w-5 shrink-0 text-primary/60" />
      <div className="min-w-0">
        {loading ? (
          <div className="h-5 w-12 animate-pulse rounded bg-muted" />
        ) : (
          <p className="text-lg font-semibold tabular-nums text-foreground">{value}</p>
        )}
        <p className="text-[11px] text-muted-foreground">{label}</p>
      </div>
    </div>
  );
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

function TimeBucketHeader({ label }: { label: string }) {
  return (
    <div className="sticky top-0 z-10 flex items-center gap-2 bg-background/95 px-1 py-2 backdrop-blur-sm">
      <div className="h-px flex-1 bg-border/50" />
      <span className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground/70">
        {label}
      </span>
      <div className="h-px flex-1 bg-border/50" />
    </div>
  );
}

// ── Main component ──

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

  const { data: stats, isLoading: statsLoading } = useActivityStats(projectId);

  // Group events by time bucket
  const groupedEvents = useMemo(() => {
    const groups: { bucket: string; events: ActivityEvent[] }[] = [];
    let currentBucket = '';
    for (const event of events) {
      const bucket = getTimeBucket(event.created_at);
      if (bucket !== currentBucket) {
        currentBucket = bucket;
        groups.push({ bucket, events: [] });
      }
      groups[groups.length - 1].events.push(event);
    }
    return groups;
  }, [events]);

  const mostCommonType = useMemo(() => {
    if (!stats?.by_type) return '—';
    const entries = Object.entries(stats.by_type);
    if (entries.length === 0) return '—';
    entries.sort(([, a], [, b]) => b - a);
    return entries[0][0].replace(/_/g, ' ');
  }, [stats]);

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

      {/* Stats dashboard */}
      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCard
          label="Total Events"
          value={stats?.total ?? 0}
          icon={BarChart3}
          loading={statsLoading}
        />
        <StatCard
          label="Today"
          value={stats?.today ?? 0}
          icon={TrendingUp}
          loading={statsLoading}
        />
        <StatCard
          label="Most Common"
          value={mostCommonType}
          icon={Activity}
          loading={statsLoading}
        />
        <StatCard
          label="Last Activity"
          value={stats?.last_event_at ? formatRelativeTime(stats.last_event_at) : '—'}
          icon={Clock}
          loading={statsLoading}
        />
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

      {/* Event timeline with time-bucketed grouping */}
      {!isLoading && events.length > 0 && (
        <InfiniteScrollContainer
          hasNextPage={hasNextPage}
          isFetchingNextPage={isFetchingNextPage}
          fetchNextPage={fetchNextPage}
          isError={isError}
        >
          {groupedEvents.map((group) => (
            <div key={group.bucket}>
              <TimeBucketHeader label={group.bucket} />
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
                          hasDetail ? 'hover:bg-muted/50 cursor-pointer' : 'cursor-default',
                        )}
                      >
                        <Icon className="mt-0.5 h-4 w-4 shrink-0 text-primary/70" />
                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-center gap-1.5">
                            <p className="text-sm text-foreground">{event.summary}</p>
                            <ActionBadge action={event.action} />
                            <EntityPill entityType={event.entity_type} entityId={event.entity_id} />
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
                            <ChevronRight className="mt-1 h-3.5 w-3.5 shrink-0 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                          ))}
                      </button>
                      {expanded && event.detail && <DetailView detail={event.detail} />}
                    </div>
                  );
                })}
              </div>
            </div>
          ))}

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
