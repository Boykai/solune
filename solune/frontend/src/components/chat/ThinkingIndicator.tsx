/**
 * ThinkingIndicator — Phase-aware loading indicator for plan mode.
 *
 * Replaces the generic 3-dot bounce with phase-specific labels and icons.
 */

import type { ThinkingPhase } from '@/types';
import { Search, ListChecks, Pencil } from '@/lib/icons';

interface ThinkingIndicatorProps {
  phase: ThinkingPhase;
  detail?: string;
}

const PHASE_CONFIG: Record<ThinkingPhase, { icon: typeof Search; label: string }> = {
  researching: { icon: Search, label: 'Researching project context\u2026' },
  planning: { icon: ListChecks, label: 'Drafting implementation plan\u2026' },
  refining: { icon: Pencil, label: 'Incorporating your feedback\u2026' },
};

export function ThinkingIndicator({ phase, detail }: ThinkingIndicatorProps) {
  const config = PHASE_CONFIG[phase];
  const Icon = config.icon;

  return (
    <div className="self-start ml-11">
      <div className="flex items-center gap-2.5 rounded-2xl border border-border bg-background/56 px-4 py-3 animate-pulse">
        <Icon className="h-4 w-4 text-muted-foreground shrink-0" />
        <div className="flex flex-col gap-0.5">
          <span className="text-sm text-muted-foreground font-medium">
            {config.label}
          </span>
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
