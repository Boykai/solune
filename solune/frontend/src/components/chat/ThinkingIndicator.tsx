/**
 * ThinkingIndicator — Phase-aware loading indicator for plan mode.
 *
 * Supports both classic thinking phases (researching, planning, refining)
 * and v2 SDK event types (reasoning, tool_start, stage progress).
 */

import type { ThinkingPhase } from '@/types';
import { Search, ListChecks, Pencil, Brain, Wrench } from '@/lib/icons';

interface ThinkingIndicatorProps {
  phase: ThinkingPhase;
  detail?: string;
  /** Optional stage name for pipeline progress display. */
  stageName?: string;
}

const PHASE_CONFIG: Record<string, { icon: typeof Search; label: string }> = {
  researching: { icon: Search, label: 'Researching project context\u2026' },
  planning: { icon: ListChecks, label: 'Drafting implementation plan\u2026' },
  refining: { icon: Pencil, label: 'Incorporating your feedback\u2026' },
  reasoning: { icon: Brain, label: 'Reasoning through approach\u2026' },
  tool_start: { icon: Wrench, label: 'Running tool\u2026' },
};

export function ThinkingIndicator({ phase, detail, stageName }: ThinkingIndicatorProps) {
  const config = PHASE_CONFIG[phase] ?? PHASE_CONFIG.planning;
  const Icon = config.icon;

  return (
    <div className="self-start ml-11">
      <div className="flex items-center gap-2.5 rounded-2xl border border-border bg-background/56 px-4 py-3 animate-pulse">
        <Icon className="h-4 w-4 text-muted-foreground shrink-0" />
        <div className="flex flex-col gap-0.5">
          <span className="text-sm text-muted-foreground font-medium">
            {config.label}
          </span>
          {stageName && (
            <span className="text-xs text-primary/80 font-medium">
              Stage: {stageName}
            </span>
          )}
          {detail && (
            <span className="text-xs text-muted-foreground/70">
              {detail}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
