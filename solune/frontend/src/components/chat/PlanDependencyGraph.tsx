/**
 * PlanDependencyGraph — Visual DAG representation of plan step dependencies.
 *
 * Renders step nodes with dependency edges and approval status visual
 * distinction. Uses a simple vertical layout with connection lines.
 */

import type { PlanStep, DependencyGraphNode, DependencyGraphEdge } from '@/types';
import { CheckCircle, XCircle, Clock } from '@/lib/icons';
import { cn } from '@/lib/utils';

interface PlanDependencyGraphProps {
  steps: PlanStep[];
  /** Callback when a node is clicked. */
  onNodeClick?: (stepId: string) => void;
}

const APPROVAL_STYLES: Record<string, { borderColor: string; bgColor: string; icon: typeof Clock }> = {
  pending: { borderColor: 'border-muted-foreground/30', bgColor: 'bg-muted/50', icon: Clock },
  approved: { borderColor: 'border-green-500/50', bgColor: 'bg-green-500/10', icon: CheckCircle },
  rejected: { borderColor: 'border-red-500/50', bgColor: 'bg-red-500/10', icon: XCircle },
};

function buildGraph(steps: PlanStep[]): { nodes: DependencyGraphNode[]; edges: DependencyGraphEdge[] } {
  const nodes: DependencyGraphNode[] = steps.map((s) => ({
    step_id: s.step_id,
    title: s.title,
    position: s.position,
    approval_status: s.approval_status,
    dependencies: s.dependencies,
  }));

  const edges: DependencyGraphEdge[] = [];
  for (const step of steps) {
    for (const depId of step.dependencies) {
      edges.push({ from: depId, to: step.step_id });
    }
  }

  return { nodes, edges };
}

export function PlanDependencyGraph({ steps, onNodeClick }: PlanDependencyGraphProps) {
  const { nodes, edges } = buildGraph(steps);

  if (nodes.length === 0) {
    return (
      <div className="text-sm text-muted-foreground text-center py-4">
        No steps to display.
      </div>
    );
  }

  // Build lookup for quick access
  const nodeMap = new Map(nodes.map((n) => [n.step_id, n]));

  return (
    <div className="space-y-3">
      <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
        Dependency Graph
      </h4>
      <div className="space-y-2">
        {nodes.map((node) => {
          const status = node.approval_status ?? 'pending';
          const style = APPROVAL_STYLES[status] ?? APPROVAL_STYLES.pending;
          const StatusIcon = style.icon;
          const deps = node.dependencies
            .map((d) => nodeMap.get(d))
            .filter((d): d is DependencyGraphNode => d !== undefined);

          return (
            <div key={node.step_id} className="flex items-start gap-2">
              {/* Dependency lines indicator */}
              <div className="flex flex-col items-center w-4 shrink-0 mt-1">
                {deps.length > 0 && (
                  <div className="w-px h-3 bg-muted-foreground/20" />
                )}
                <div className={cn(
                  'w-2 h-2 rounded-full shrink-0',
                  status === 'approved' ? 'bg-green-500' :
                  status === 'rejected' ? 'bg-red-500' :
                  'bg-muted-foreground/40'
                )} />
              </div>

              {/* Node card */}
              <button
                type="button"
                onClick={() => onNodeClick?.(node.step_id)}
                className={cn(
                  'flex-1 flex items-center gap-2 rounded-md border px-3 py-2 text-left transition-colors hover:bg-accent/50',
                  style.borderColor,
                  style.bgColor,
                )}
              >
                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-background text-[10px] font-medium text-muted-foreground border border-border">
                  {node.position + 1}
                </span>
                <span className="flex-1 text-sm font-medium text-foreground truncate">
                  {node.title}
                </span>
                <StatusIcon className={cn(
                  'h-3.5 w-3.5 shrink-0',
                  status === 'approved' ? 'text-green-600 dark:text-green-400' :
                  status === 'rejected' ? 'text-red-600 dark:text-red-400' :
                  'text-muted-foreground'
                )} />
              </button>
            </div>
          );
        })}
      </div>

      {/* Edge summary */}
      {edges.length > 0 && (
        <div className="text-[10px] text-muted-foreground/60 pt-1">
          {edges.length} {edges.length === 1 ? 'dependency' : 'dependencies'} between {nodes.length} steps
        </div>
      )}
    </div>
  );
}
