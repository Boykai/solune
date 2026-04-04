/**
 * AgentNode — represents an agent assigned to a pipeline stage.
 * Shows agent name, model selection, tool count badge, and remove button.
 * For human agents, also shows a delay-until-auto-merge toggle with a duration badge.
 */

import { useState, useRef } from 'react';
import { X, Wrench, Copy, CheckCircle2, XCircle, Loader2, Clock } from '@/lib/icons';

export type AgentRunStatus = 'pending' | 'running' | 'completed' | 'failed';

import { ModelSelector } from './ModelSelector';
import { ThemedAgentIcon } from '@/components/common/ThemedAgentIcon';
import { Tooltip } from '@/components/ui/tooltip';
import { HoverCard, HoverCardTrigger, HoverCardContent } from '@/components/ui/hover-card';
import type { PipelineAgentNode } from '@/types';
import { formatAgentName } from '@/utils/formatAgentName';
import type { SyntheticListenerMap } from '@dnd-kit/core/dist/hooks/utilities';
import type { DraggableAttributes } from '@dnd-kit/core';
import { cn } from '@/lib/utils';

/**
 * Format seconds into a human-readable duration string.
 * Examples: 30 → "30s", 300 → "5m", 3600 → "1h", 90 → "1m 30s", 86400 → "24h".
 */
function formatDelayDuration(seconds: number): string {
  if (seconds <= 0) return '0s';
  const hours = Math.floor(seconds / 3600);
  const remainder = seconds % 3600;
  const minutes = Math.floor(remainder / 60);
  const secs = remainder % 60;
  const parts: string[] = [];
  if (hours) parts.push(`${hours}h`);
  if (minutes) parts.push(`${minutes}m`);
  if (secs || parts.length === 0) parts.push(`${secs}s`);
  return parts.join(' ');
}

interface AgentNodeProps {
  agentNode: PipelineAgentNode;
  onModelSelect: (modelId: string, modelName: string, reasoningEffort?: string) => void;
  onRemove: () => void;
  onToolsClick?: () => void;
  onClone?: () => void;
  onConfigChange?: (config: Record<string, unknown>) => void;
  isParallel?: boolean;
  /** Runtime status for live pipeline monitoring. */
  agentStatus?: AgentRunStatus;
  // Drag-and-drop sortable props (optional — only provided when used inside a SortableContext)
  dragHandleListeners?: SyntheticListenerMap;
  dragHandleAttributes?: DraggableAttributes;
  setNodeRef?: (node: HTMLElement | null) => void;
  dragStyle?: { transform?: string; transition?: string };
  isDragging?: boolean;
}

export function AgentNode({
  agentNode,
  onModelSelect,
  onRemove,
  onToolsClick,
  onClone,
  onConfigChange,
  isParallel,
  agentStatus,
  dragHandleListeners,
  dragHandleAttributes,
  setNodeRef,
  dragStyle,
  isDragging,
}: AgentNodeProps) {
  const toolCount = agentNode.tool_count ?? agentNode.tool_ids?.length ?? 0;
  const displayName = formatAgentName(agentNode.agent_slug, agentNode.agent_display_name);
  const stopDragPointerPropagation = (event: React.PointerEvent<HTMLElement>) => {
    event.stopPropagation();
  };

  const isHuman = agentNode.agent_slug === 'human';
  const currentDelay = agentNode.config?.delay_seconds;
  const hasDelay = typeof currentDelay === 'number' && currentDelay > 0;

  // Track the previous external delay value to detect prop changes
  const prevDelayRef = useRef(currentDelay);
  const [delayInputValue, setDelayInputValue] = useState<string>(
    hasDelay ? String(currentDelay) : '300',
  );

  // Sync local input value when delay_seconds changes externally (not via effect)
  if (currentDelay !== prevDelayRef.current) {
    prevDelayRef.current = currentDelay;
    if (hasDelay) {
      setDelayInputValue(String(currentDelay));
    }
  }

  const handleDelayToggle = () => {
    if (!onConfigChange) return;
    if (hasDelay) {
      // Turn off delay
      const { delay_seconds: _, ...rest } = agentNode.config ?? {};
      onConfigChange(rest);
    } else {
      // Turn on delay with current input value
      const seconds = Math.max(1, Math.min(86400, Number(delayInputValue) || 300));
      onConfigChange({ ...agentNode.config, delay_seconds: seconds });
      setDelayInputValue(String(seconds));
    }
  };

  const handleDelayChange = (value: string) => {
    setDelayInputValue(value);
    if (!onConfigChange) return;
    const parsed = Number(value);
    if (Number.isInteger(parsed) && parsed >= 1 && parsed <= 86400) {
      onConfigChange({ ...agentNode.config, delay_seconds: parsed });
    }
  };

  return (
    <Tooltip
      contentKey={
        isParallel ? 'pipeline.agent.parallelHint' : 'pipeline.agent.sequentialHint'
      }
    >
      <div
        ref={setNodeRef}
        style={dragStyle}
        {...(dragHandleAttributes ?? {})}
        {...(dragHandleListeners ?? {})}
        className={cn('pipeline-agent-node pipeline-builder-node flex items-center gap-2 rounded-lg border px-2.5 py-2 transition-[color,background-color,border-color,box-shadow] hover:border-primary/30 hover:shadow-[0_0_12px_hsl(var(--glow)/0.18)] dark:hover:border-primary/50 dark:hover:shadow-[0_0_18px_hsl(var(--glow)/0.28)]', agentStatus === 'failed' ? 'border-destructive/50 bg-destructive/5 dark:bg-destructive/12' : agentStatus === 'completed' ? 'border-green-500/30 dark:border-green-400/50' : 'border-border/50 dark:border-border/80', dragHandleListeners ? ' cursor-grab active:cursor-grabbing touch-none' : '', isDragging ? ' opacity-50 scale-[0.98]' : '')}
    >
      {/* Drag handle removed — entire card is the drag target */}

      <HoverCard openDelay={300} closeDelay={150}>
        <HoverCardTrigger asChild>
          <span className="shrink-0">
            <ThemedAgentIcon slug={agentNode.agent_slug} name={displayName} size="md" />
          </span>
        </HoverCardTrigger>
        <HoverCardContent side="right" align="start" className="w-64">
          <div className="space-y-2">
            <h4 className="text-sm font-semibold">{displayName}</h4>
            {agentNode.agent_slug && (
              <p className="text-xs text-muted-foreground">{agentNode.agent_slug}</p>
            )}
            <div className="flex items-center gap-2">
              {agentNode.model_name && (
                <span className="inline-flex items-center rounded-full border border-border/60 px-2 py-0.5 text-[10px] font-medium">
                  {agentNode.model_name}
                </span>
              )}
              <span className="text-[10px] text-muted-foreground">
                {toolCount} tool{toolCount !== 1 ? 's' : ''}
              </span>
            </div>
            {agentStatus && agentStatus !== 'pending' && (
              <span className={cn('inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium',
                agentStatus === 'running' ? 'bg-primary/10 text-primary' :
                agentStatus === 'completed' ? 'bg-green-500/10 text-green-600' :
                'bg-destructive/10 text-destructive'
              )}>
                {agentStatus === 'running' ? '● Running' : agentStatus === 'completed' ? '✓ Completed' : '✗ Failed'}
              </span>
            )}
          </div>
        </HoverCardContent>
      </HoverCard>

      {/* Runtime status indicator */}
      {agentStatus === 'running' && (
        <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin text-primary" />
      )}
      {agentStatus === 'completed' && (
        <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-green-500" />
      )}
      {agentStatus === 'failed' && (
        <XCircle className="h-3.5 w-3.5 shrink-0 text-destructive" />
      )}

      {/* Agent info */}
      <div className="flex-1 min-w-0">
        <div className="text-xs font-medium text-foreground truncate">{displayName}</div>
        <div className="mt-1 flex flex-wrap items-center gap-2">
          <div
            className="flex min-w-[10rem] flex-1 items-center gap-1.5"
            onPointerDown={stopDragPointerPropagation}
          >
            <span className="text-[10px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
              Model
            </span>
            <ModelSelector
              selectedModelId={agentNode.model_id || null}
              selectedModelName={agentNode.model_name || null}
              onSelect={onModelSelect}
              allowAuto={true}
              autoLabel="Auto"
              triggerClassName="min-w-0 flex-1 justify-between"
            />
          </div>
          <button
            type="button"
            onClick={onToolsClick}
            onPointerDown={stopDragPointerPropagation}
            className="pipeline-builder-node-action celestial-focus inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[10px] transition-colors hover:bg-primary/10 focus-visible:outline-none dark:bg-background/42 dark:hover:bg-primary/14"
            aria-label="Select tools"
          >
            <Wrench className="h-3 w-3 text-muted-foreground" />
            {toolCount > 0 ? (
              <span className="font-medium text-primary">
                {toolCount} tool{toolCount !== 1 ? 's' : ''}
              </span>
            ) : (
              <span className="text-muted-foreground">+ Tools</span>
            )}
          </button>
        </div>

        {/* Human agent: Delay toggle + badge */}
        {isHuman && onConfigChange && (
          <div className="mt-1.5 flex flex-wrap items-center gap-2" onPointerDown={stopDragPointerPropagation}>
            <label className="inline-flex cursor-pointer items-center gap-1.5">
              <input
                type="checkbox"
                checked={hasDelay}
                onChange={handleDelayToggle}
                className="h-3 w-3 rounded border-border accent-primary"
                aria-label="Delay until auto-merge"
              />
              <span className="text-[10px] text-muted-foreground">Delay until auto-merge</span>
            </label>
            {hasDelay && (
              <input
                type="number"
                min={1}
                max={86400}
                value={delayInputValue}
                onChange={(e) => handleDelayChange(e.target.value)}
                className="h-5 w-16 rounded border border-border/60 bg-background px-1 text-[10px] text-foreground"
                aria-label="Delay seconds"
              />
            )}
            <span className={cn(
              'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium',
              hasDelay
                ? 'bg-primary/10 text-primary'
                : 'bg-muted text-muted-foreground',
            )}>
              <Clock className="h-3 w-3" />
              {hasDelay ? `⏱️ Auto-merge: ${formatDelayDuration(currentDelay as number)}` : 'Manual review'}
            </span>
          </div>
        )}

        {/* Human agent: Badge only (read-only, no onConfigChange) */}
        {isHuman && !onConfigChange && (
          <div className="mt-1.5">
            <span className={cn(
              'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium',
              hasDelay
                ? 'bg-primary/10 text-primary'
                : 'bg-muted text-muted-foreground',
            )}>
              <Clock className="h-3 w-3" />
              {hasDelay ? `⏱️ Auto-merge: ${formatDelayDuration(currentDelay as number)}` : 'Manual review'}
            </span>
          </div>
        )}
      </div>

      {/* Clone button */}
      {onClone && (
        <Tooltip contentKey="pipeline.agent.clone">
          <button
            type="button"
            onClick={onClone}
            onPointerDown={stopDragPointerPropagation}
            className="pipeline-builder-node-action celestial-focus shrink-0 rounded-md p-1 text-muted-foreground/60 transition-colors hover:bg-primary/10 hover:text-primary focus-visible:outline-none dark:bg-background/42 dark:hover:bg-primary/14"
            aria-label="Clone agent"
          >
            <Copy className="h-3.5 w-3.5" />
          </button>
        </Tooltip>
      )}

      {/* Remove button */}
      <Tooltip contentKey="pipeline.agent.remove">
        <button
          type="button"
          onClick={onRemove}
          onPointerDown={stopDragPointerPropagation}
          className="pipeline-builder-node-action celestial-focus shrink-0 rounded-md p-1 text-muted-foreground/60 transition-colors hover:bg-destructive/10 hover:text-destructive focus-visible:outline-none dark:bg-background/42 dark:hover:bg-destructive/14"
          aria-label="Remove agent"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </Tooltip>
    </div>
    </Tooltip>
  );
}
