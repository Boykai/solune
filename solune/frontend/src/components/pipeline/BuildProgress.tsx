/**
 * BuildProgress — stepper/timeline panel for monitoring app build progress.
 * Shows phases as steps, highlights current phase, displays agent and detail.
 */

import { cn } from '@/lib/utils';
import type { BuildPhase, BuildProgressPayload } from '@/types/app-template';

const PHASES: BuildPhase[] = [
  'scaffolding',
  'configuring',
  'issuing',
  'building',
  'deploying_prep',
  'complete',
];

const PHASE_LABELS: Record<BuildPhase, string> = {
  scaffolding: 'Scaffolding',
  configuring: 'Configuring Pipeline',
  issuing: 'Creating Issue',
  building: 'Building',
  deploying_prep: 'Deploy Preparation',
  complete: 'Complete',
  failed: 'Failed',
};

const PHASE_ICONS: Record<BuildPhase, string> = {
  scaffolding: '📁',
  configuring: '⚙️',
  issuing: '📋',
  building: '🔨',
  deploying_prep: '🚀',
  complete: '✅',
  failed: '❌',
};

interface BuildProgressProps {
  progress: BuildProgressPayload | null;
  className?: string;
}

export function BuildProgress({ progress, className }: BuildProgressProps) {
  if (!progress) {
    return null;
  }

  const isFailed = progress.phase === 'failed';

  // When phase is 'failed', use pct_complete to determine which phase was active.
  // 'failed' is not in PHASES so indexOf returns -1; approximate from progress %.
  const currentPhaseIndex = isFailed
    ? Math.min(Math.floor((progress.pct_complete / 100) * PHASES.length), PHASES.length - 1)
    : PHASES.indexOf(progress.phase);

  return (
    <div className={cn('rounded-xl border border-border/80 bg-card/88 p-5', className)}>
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-sm font-semibold">Build Progress — {progress.app_name}</h3>
        <span className="text-xs text-muted-foreground">{progress.pct_complete}%</span>
      </div>

      {/* Stepper */}
      <div className="space-y-3">
        {PHASES.map((phase, idx) => {
          const isCompleted = idx < currentPhaseIndex;
          const isCurrent = isFailed ? idx === currentPhaseIndex : phase === progress.phase;
          const isPending = idx > currentPhaseIndex;

          return (
            <div key={phase} className="flex items-start gap-3">
              {/* Step indicator */}
              <div className="flex flex-col items-center">
                <div
                  className={cn(
                    'flex h-7 w-7 items-center justify-center rounded-full text-xs',
                    isCompleted && 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/50 dark:text-emerald-300',
                    isCurrent && !isFailed && 'bg-primary/20 text-primary ring-2 ring-primary/40',
                    isCurrent && isFailed && 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300',
                    isPending && 'bg-muted/50 text-muted-foreground',
                  )}
                >
                  {isCompleted ? '✓' : PHASE_ICONS[phase]}
                </div>
                {idx < PHASES.length - 1 && (
                  <div
                    className={cn(
                      'mt-1 h-4 w-0.5',
                      isCompleted ? 'bg-emerald-300 dark:bg-emerald-700' : 'bg-muted/40',
                    )}
                  />
                )}
              </div>

              {/* Step content */}
              <div className="flex-1 pb-1">
                <p
                  className={cn(
                    'text-sm font-medium',
                    isCurrent && 'text-foreground',
                    isPending && 'text-muted-foreground',
                    isCompleted && 'text-muted-foreground',
                  )}
                >
                  {PHASE_LABELS[phase]}
                </p>
                {isCurrent && progress.detail && (
                  <p className="mt-0.5 text-xs text-muted-foreground">{progress.detail}</p>
                )}
                {isCurrent && progress.agent_name && (
                  <span className="mt-1 inline-block rounded bg-muted/60 px-1.5 py-0.5 text-xs text-muted-foreground">
                    Agent: {progress.agent_name}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Progress bar */}
      <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-muted/40">
        <div
          className={cn(
            'h-full rounded-full transition-all duration-500',
            isFailed ? 'bg-red-500' : 'bg-primary',
          )}
          style={{ width: `${progress.pct_complete}%` }}
        />
      </div>
    </div>
  );
}
