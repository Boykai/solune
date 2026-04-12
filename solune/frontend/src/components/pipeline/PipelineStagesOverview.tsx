/**
 * PipelineStagesOverview — Visualizes pipeline stages with agent assignments.
 * Extracted from AgentsPipelinePage to keep the page file ≤250 lines.
 */

import { useMemo, type CSSProperties } from 'react';
import { statusColorToCSS } from '@/components/board/colorUtils';
import { formatAgentName } from '@/utils/formatAgentName';
import type { StatusColor } from '@/types';

interface AgentMapping {
  id: string;
  slug: string;
  display_name?: string | null;
}

interface BoardColumn {
  status: { option_id: string; name: string; color: StatusColor };
  item_count: number;
}

interface PipelineStagesOverviewProps {
  columns: BoardColumn[];
  localMappings: Record<string, AgentMapping[]>;
  alignedColumnCount: number;
}

export function PipelineStagesOverview({
  columns,
  localMappings,
  alignedColumnCount,
}: PipelineStagesOverviewProps) {
  const alignedGridStyle = useMemo<CSSProperties>(
    () => ({
      gridTemplateColumns: `repeat(${alignedColumnCount}, minmax(14rem, 1fr))`,
    }),
    [alignedColumnCount],
  );

  return (
    <section
      className="celestial-panel rounded-[1.35rem] border border-border/75 p-4 sm:rounded-[1.5rem] sm:p-5"
      aria-labelledby="pipeline-stages-title"
    >
      <div className="mb-4">
        <p className="text-[11px] uppercase tracking-[0.24em] text-primary/80">Orbital map</p>
        <h3 id="pipeline-stages-title" className="mt-2 text-xl font-display font-medium">
          Pipeline stages
        </h3>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          Keep column coverage readable so each stage shows both workload and attached agents at a glance.
        </p>
      </div>
      <div className="overflow-x-auto pb-2">
        <div
          className="grid min-w-full items-stretch gap-3"
          style={alignedGridStyle}
          data-testid="pipeline-stages-grid"
        >
          {columns.map((col) => {
            const assigned = localMappings[col.status.name] ?? [];
            const dotColor = statusColorToCSS(col.status.color);
            return (
              <div
                key={col.status.option_id}
                className="moonwell flex h-full min-w-0 flex-col items-center gap-2 rounded-[1.2rem] border border-border/60 p-4 text-center shadow-none"
              >
                <span
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: dotColor }}
                />
                <span className="text-sm font-medium">{col.status.name}</span>
                <span className="text-xs text-muted-foreground">{col.item_count} items</span>
                {assigned.length > 0 ? (
                  <div className="flex flex-wrap gap-1 justify-center mt-1">
                    {assigned.map((a) => (
                      <span
                        key={a.id}
                        className="solar-chip rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.12em]"
                      >
                        {formatAgentName(a.slug, a.display_name)}
                      </span>
                    ))}
                  </div>
                ) : (
                  <span className="text-[10px] text-muted-foreground/60 mt-1">No agents</span>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
