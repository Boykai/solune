/**
 * SavedWorkflowsList — displays saved pipeline configurations as enriched cards.
 * Shows pipeline name, flow graph, stage details, tool counts, and preset badges.
 */

import { Clock, Layers, Bot, Workflow, Wrench, CheckCircle2, Copy } from '@/lib/icons';
import { PipelineFlowGraph } from './PipelineFlowGraph';
import { PresetBadge } from './PresetBadge';
import type { PipelineConfigSummary } from '@/types';
import { cn } from '@/lib/utils';
import { Tooltip } from '@/components/ui/tooltip';

interface SavedWorkflowsListProps {
  pipelines: PipelineConfigSummary[];
  activePipelineId: string | null;
  assignedPipelineId?: string;
  isLoading: boolean;
  onSelect: (pipelineId: string) => void;
  onCopy?: (pipelineId: string) => void;
  onAssign?: (pipelineId: string) => void;
}

function formatRelativeDate(dateStr: string): string {
  try {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60_000);
    const diffHours = Math.floor(diffMs / 3_600_000);
    const diffDays = Math.floor(diffMs / 86_400_000);

    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  } catch {
    return dateStr;
  }
}

export function SavedWorkflowsList({
  pipelines,
  activePipelineId,
  assignedPipelineId = '',
  isLoading,
  onSelect,
  onCopy,
  onAssign,
}: SavedWorkflowsListProps) {
  return (
    <section
      id="saved-pipelines"
      className="celestial-panel celestial-fade-in scroll-mt-6 rounded-[1.35rem] border border-border/75 p-4 sm:rounded-[1.5rem] sm:p-5"
      aria-labelledby="saved-pipelines-title"
    >
      <div className="mb-4">
        <p className="text-[11px] uppercase tracking-[0.24em] text-primary/80">Saved rituals</p>
        <h3 id="saved-pipelines-title" className="mt-2 flex items-center gap-2 text-xl font-display font-medium">
          <Workflow className="h-5 w-5 text-primary/70" />
          Saved Pipelines
        </h3>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          Reusable workflow presets and project-specific pipelines, presented with the same light card rhythm used across the catalog pages.
        </p>
      </div>

      {/* Loading skeleton */}
      {isLoading && (
        <div className="grid gap-3 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="moonwell flex animate-pulse flex-col gap-3 rounded-[1.3rem] border border-border/60 p-4"
            >
              <div className="h-4 w-2/3 rounded bg-muted/40" />
              <div className="h-3 w-full rounded bg-muted/30" />
              <div className="h-3 w-4/5 rounded bg-muted/30" />
              <div className="mt-auto flex gap-3">
                <div className="h-3 w-12 rounded bg-muted/20" />
                <div className="h-3 w-12 rounded bg-muted/20" />
                <div className="h-3 w-16 rounded bg-muted/20" />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Empty state */}
      {!isLoading && pipelines.length === 0 && (
        <div className="moonwell flex flex-col items-center gap-2 rounded-[1.2rem] border border-dashed border-border/70 p-6 text-center shadow-none">
          <Workflow className="h-6 w-6 text-muted-foreground/40" />
          <p className="text-sm text-muted-foreground">
            No saved pipelines yet. Create your first pipeline above!
          </p>
        </div>
      )}

      {/* Pipeline cards */}
      {!isLoading && pipelines.length > 0 && (
        <div className="grid gap-3 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
          {pipelines.map((pipeline) => {
            const isActive = pipeline.id === activePipelineId;
            const isAssigned = pipeline.id === assignedPipelineId;
            return (
              <div
                key={pipeline.id}
                role="button"
                tabIndex={0}
                onClick={() => onSelect(pipeline.id)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault();
                    onSelect(pipeline.id);
                  }
                }}
                className={cn(
                  'celestial-panel flex flex-col gap-2 rounded-[1.35rem] border p-4 text-left transition-all hover:-translate-y-0.5 hover:shadow-md',
                  isActive
                    ? 'border-primary/50 bg-primary/8 ring-1 ring-primary/20 shadow-sm'
                    : pipeline.is_preset
                      ? 'border-border/70 bg-card/90 hover:border-primary/30'
                      : 'border-border/70 bg-card/88 hover:border-primary/30'
                )}
              >
                {/* Header: name + badges */}
                <div className="flex items-start justify-between gap-2">
                  <Tooltip content={pipeline.name}>
                    <h4 className="truncate text-sm font-semibold text-foreground">
                      {pipeline.name}
                    </h4>
                  </Tooltip>
                  <div className="flex items-center gap-1 shrink-0">
                    {isAssigned && (
                      <span className="solar-chip-success inline-flex items-center gap-0.5 rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.12em]">
                        <CheckCircle2 className="h-2.5 w-2.5" />
                        Assigned
                      </span>
                    )}
                    {isActive && (
                      <span className="solar-chip rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.12em]">
                        Active
                      </span>
                    )}
                    {pipeline.is_preset && <PresetBadge presetId={pipeline.preset_id} />}
                  </div>
                </div>

                {pipeline.description && (
                  <p className="text-xs text-muted-foreground line-clamp-1">
                    {pipeline.description}
                  </p>
                )}

                {/* Flow graph */}
                {pipeline.stages && pipeline.stages.length > 0 && (
                  <div className="w-full py-1">
                    <PipelineFlowGraph
                      stages={pipeline.stages}
                      width={420}
                      height={96}
                      responsive={true}
                      className="w-full"
                    />
                  </div>
                )}

                {/* Stage details */}
                {pipeline.stages && pipeline.stages.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {pipeline.stages.map((stage) => (
                      <span
                        key={stage.id}
                        className="solar-chip-soft inline-flex items-center gap-1 rounded-[0.7rem] px-2 py-1 text-[10px] font-medium"
                      >
                        {stage.name}
                        <span className="font-medium text-foreground/70">
                          ({((stage.groups ?? []).flatMap((g) => g.agents).length) || stage.agents.length})
                        </span>
                      </span>
                    ))}
                  </div>
                )}

                {/* Stats */}
                <div className="flex items-center gap-3 mt-auto text-[11px] text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <Layers className="h-3 w-3" />
                    {pipeline.stage_count} stage{pipeline.stage_count !== 1 ? 's' : ''}
                  </span>
                  <span className="flex items-center gap-1">
                    <Bot className="h-3 w-3" />
                    {pipeline.agent_count} agent{pipeline.agent_count !== 1 ? 's' : ''}
                  </span>
                  {(pipeline.total_tool_count ?? 0) > 0 && (
                    <span className="flex items-center gap-1">
                      <Wrench className="h-3 w-3" />
                      {pipeline.total_tool_count} tool{pipeline.total_tool_count !== 1 ? 's' : ''}
                    </span>
                  )}
                  <span className="flex items-center gap-1 ml-auto">
                    <Clock className="h-3 w-3" />
                    {formatRelativeDate(pipeline.updated_at)}
                  </span>
                </div>

                {(onCopy || (onAssign && !isAssigned)) && (
                  <div className="mt-1 flex items-center gap-3">
                    {onCopy && (
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          onCopy(pipeline.id);
                        }}
                        className="inline-flex items-center gap-1 text-[10px] font-semibold uppercase tracking-[0.12em] text-primary/80 transition-colors hover:text-primary"
                      >
                        <Copy className="h-3 w-3" />
                        Copy
                      </button>
                    )}
                    {onAssign && !isAssigned && (
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          onAssign(pipeline.id);
                        }}
                        className="text-[10px] font-semibold uppercase tracking-[0.12em] text-primary/80 transition-colors hover:text-primary"
                      >
                        Assign to Project
                      </button>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
